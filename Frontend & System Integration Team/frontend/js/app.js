const searchForm = document.getElementById("searchForm");
const searchInput = document.getElementById("searchInput");
const productGrid = document.getElementById("productGrid");
const resultsTitle = document.getElementById("resultsTitle");
const resultsCount = document.getElementById("resultsCount");
const emptyState = document.getElementById("emptyState");
const sortSelect = document.getElementById("sortSelect");

function getSearchQuery() {
    return new URLSearchParams(window.location.search).get("q") || "";
}

function displayProducts(items) {
    if (!productGrid) return;

    productGrid.replaceChildren();
    emptyState.hidden = items.length > 0;

    items.forEach(product => {
        productGrid.appendChild(createProductCard(product));
    });
}

function updateResults() {
    if (!productGrid) return;

    const query = getSearchQuery().toLowerCase();
    const category = new URLSearchParams(window.location.search).get("category");

    if (searchInput) searchInput.value = getSearchQuery();

    let filtered = products.filter(product => {
        const matchesQuery =
            product.name.toLowerCase().includes(query) ||
            product.brand.toLowerCase().includes(query) ||
            product.category.toLowerCase().includes(query);

        const matchesCategory = !category || product.category === category;

        return matchesQuery && matchesCategory;
    });

    if (sortSelect.value === "low") {
        filtered.sort((a, b) =>
            Math.min(...a.prices.map(p => p.price)) -
            Math.min(...b.prices.map(p => p.price))
        );
    }

    if (sortSelect.value === "high") {
        filtered.sort((a, b) =>
            Math.min(...b.prices.map(p => p.price)) -
            Math.min(...a.prices.map(p => p.price))
        );
    }

    resultsTitle.textContent = query
        ? `Results for "${getSearchQuery()}"`
        : category || "All Products";

    resultsCount.textContent = `${filtered.length} products found`;

    displayProducts(filtered);
}

if (searchForm) {
    searchForm.addEventListener("submit", event => {
        event.preventDefault();

        const query = searchInput.value.trim();
        if (!query) return;

        const destination = new URL(searchForm.action, window.location.href);
        destination.searchParams.set("q", query);
        window.location.href = destination.toString();
    });
}

if (sortSelect) {
    sortSelect.addEventListener("change", updateResults);
}

if (productGrid) {
    updateResults();
}
