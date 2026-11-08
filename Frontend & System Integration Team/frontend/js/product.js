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
    offerList.innerHTML = "";

    const sortedOffers = [...product.prices];

    if (offerSort.value === "low") {
        sortedOffers.sort((a, b) => a.price - b.price);
    } else {
        sortedOffers.sort((a, b) => b.price - a.price);
    }

    noOffersState.hidden = sortedOffers.length > 0;

    if (sortedOffers.length === 0) return;

    const lowestPrice = Math.min(...sortedOffers.map(offer => offer.price));

    sortedOffers.forEach(offer => {
        const isCheapest = offer.price === lowestPrice;
        const card = createOfferCard(offer, isCheapest);
        offerList.appendChild(card);
    });
}

function loadProduct() {
    loadingState.hidden = false;
    productContent.hidden = true;
    errorState.hidden = true;

    const productId = Number(
        new URLSearchParams(window.location.search).get("id")
    );

    const product = products.find(item => item.id === productId);

    if (!product) {
        showError();
        return;
    }

    document.getElementById("productImage").textContent = product.image;
    document.getElementById("productCategory").textContent = product.category;
    document.getElementById("productName").textContent = product.name;
    document.getElementById("productBrand").textContent = `Brand: ${product.brand}`;

    const attributes = document.getElementById("productAttributes");
    attributes.innerHTML = "";

    const brandAttribute = document.createElement("span");
    brandAttribute.textContent = `Brand: ${product.brand}`;

    const categoryAttribute = document.createElement("span");
    categoryAttribute.textContent = `Category: ${product.category}`;

    attributes.append(brandAttribute, categoryAttribute);

    document.getElementById("offerCount").textContent =
        `${product.prices.length} retailer offers found`;

    displayOffers(product);

    loadingState.hidden = true;
    productContent.hidden = false;
}

if (offerSort) {
    offerSort.addEventListener("change", () => {
        const productId = Number(
            new URLSearchParams(window.location.search).get("id")
        );

        const product = products.find(item => item.id === productId);

        if (product) displayOffers(product);
    });
}

loadProduct();
