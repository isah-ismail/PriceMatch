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
    if (emptyState) emptyState.hidden = items.length > 0;

    items.forEach(product => {
        productGrid.appendChild(createProductCard(product));
    });
}

function priceValue(product) {
    if (product.lowest_price === null || product.lowest_price === undefined || product.lowest_price === "") {
        return null;
    }

    const price = Number(product.lowest_price);
    return Number.isFinite(price) ? price : null;
}

function compareByPrice(a, b, direction) {
    const aPrice = priceValue(a);
    const bPrice = priceValue(b);

    if (aPrice === null && bPrice === null) return 0;
    if (aPrice === null) return 1;
    if (bPrice === null) return -1;

    return direction === "low" ? aPrice - bPrice : bPrice - aPrice;
}

function updateResults() {
    if (!productGrid) return;

    const params = new URLSearchParams(window.location.search);
    const query = getSearchQuery().trim().toLocaleLowerCase("tr-TR");
    const category = (params.get("category") || "").toLocaleLowerCase("tr-TR");

    if (searchInput) searchInput.value = getSearchQuery();

    let filtered = products.filter(product => {
        const searchableFields = [
            product.name,
            product.brand?.name,
            product.category?.name,
            product.model,
            product.variant
        ];

        const matchesQuery = !query || searchableFields.some(value =>
            (value || "").toLocaleLowerCase("tr-TR").includes(query)
        );
        const matchesCategory = !category ||
            (product.category?.name || "").toLocaleLowerCase("tr-TR") === category;

        return matchesQuery && matchesCategory;
    });

    if (sortSelect?.value === "low") {
        filtered.sort((a, b) => compareByPrice(a, b, "low"));
    } else if (sortSelect?.value === "high") {
        filtered.sort((a, b) => compareByPrice(a, b, "high"));
    }

    if (resultsTitle) {
        resultsTitle.textContent = query
            ? 'Results for "' + getSearchQuery() + '"'
            : category ? params.get("category") : "All Products";
    }
    if (resultsCount) resultsCount.textContent = filtered.length + " products found";

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
