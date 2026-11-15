const loadingState = document.getElementById("loadingState");
const errorState = document.getElementById("errorState");
const productContent = document.getElementById("productContent");
const offerList = document.getElementById("offerList");
const offerSort = document.getElementById("offerSort");
const noOffersState = document.getElementById("noOffersState");

function showError() {
    loadingState.hidden = true;
    productContent.hidden = true;
    errorState.hidden = false;
}

function displayOffers(product) {
    offerList.replaceChildren();

    const offers = Array.isArray(product.offers) ? [...product.offers] : [];
    offers.sort((a, b) => {
        const aPrice = Number(a.price);
        const bPrice = Number(b.price);
        return offerSort.value === "high" ? bPrice - aPrice : aPrice - bPrice;
    });

    noOffersState.hidden = offers.length > 0;
    document.getElementById("offerCount").textContent =
        (product.offer_count ?? offers.length) + " retailer offers found";

    offers.forEach(offer => {
        offerList.appendChild(createOfferCard(offer));
    });
}

function loadProduct() {
    loadingState.hidden = false;
    productContent.hidden = true;
    errorState.hidden = true;

    const productId = Number(
        new URLSearchParams(window.location.search).get("id")
    );
    const product = products.find(item => item.product_id === productId);

    if (!product) {
        showError();
        return;
    }

    const productImage = document.getElementById("productImage");
    populateProductImage(
        productImage,
        product.image_url,
        product.category?.name,
        product.name
    );
    document.getElementById("productCategory").textContent =
        product.category?.name || "Product";
    document.getElementById("productName").textContent =
        product.name || "Unnamed product";
    document.getElementById("productBrand").textContent =
        product.brand?.name ? "Brand: " + product.brand.name : "Brand not specified";

    const attributes = document.getElementById("productAttributes");
    attributes.replaceChildren();

    [
        ["Category", product.category?.name],
        ["Model", product.model],
        ["Variant", product.variant]
    ].filter(([, value]) => value).forEach(([label, value]) => {
        const attribute = document.createElement("span");
        attribute.textContent = label + ": " + value;
        attributes.appendChild(attribute);
    });

    displayOffers(product);

    loadingState.hidden = true;
    productContent.hidden = false;
}

if (offerSort) {
    offerSort.addEventListener("change", () => {
        const productId = Number(
            new URLSearchParams(window.location.search).get("id")
        );
        const product = products.find(item => item.product_id === productId);
        if (product) displayOffers(product);
    });
}

loadProduct();
