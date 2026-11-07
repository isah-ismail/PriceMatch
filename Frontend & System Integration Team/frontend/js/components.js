const formatPrice = (price) =>
    new Intl.NumberFormat("tr-TR", {
        style: "currency",
        currency: "TRY",
        maximumFractionDigits: 0
    }).format(price);

// Reusable product card
function createProductCard(product) {
    const cheapestPrice = Math.min(...product.prices.map(p => p.price));

    const card = document.createElement("article");
    card.className = "product-card";

    const image = document.createElement("div");
    image.className = "product-image";
    image.textContent = product.image;

    const details = document.createElement("div");
    details.className = "product-details";

    const category = document.createElement("span");
    category.className = "product-category";
    category.textContent = product.category;

    const name = document.createElement("h3");
    name.textContent = product.name;

    const brand = document.createElement("p");
    brand.className = "product-brand";
    brand.textContent = product.brand;

    const price = document.createElement("div");
    price.className = "product-price";

    const label = document.createElement("span");
    label.textContent = "From";

    const value = document.createElement("strong");
    value.textContent = formatPrice(cheapestPrice);

    price.append(label, value);

    const storeCount = document.createElement("p");
    storeCount.className = "store-count";
    storeCount.textContent = `${product.prices.length} stores compared`;

    const link = document.createElement("a");
    link.className = "compare-button";
    link.href = `product.html?id=${encodeURIComponent(product.id)}`;
    link.textContent = "Compare Prices →";

    details.append(category, name, brand, price, storeCount, link);
    card.append(image, details);

    return card;
}

// Reusable retailer offer card
function createOfferCard(offer, isCheapest) {
    const card = document.createElement("article");
    card.className = isCheapest
        ? "offer-card cheapest-offer"
        : "offer-card";

    const store = document.createElement("div");
    store.className = "offer-store";

    const icon = document.createElement("div");
    icon.className = "store-icon";
    icon.textContent = "🏬";

    const details = document.createElement("div");

    const name = document.createElement("h3");
    name.textContent = offer.store;

    const description = document.createElement("p");
    description.textContent = isCheapest
        ? "Lowest available price"
        : "Alternative offer";

    details.append(name, description);
    store.append(icon, details);

    const offerDetails = document.createElement("div");
    offerDetails.className = "offer-details";

    const badge = document.createElement("span");
    badge.className = "offer-badge";
    badge.textContent = isCheapest ? "BEST PRICE" : "AVAILABLE";

    const price = document.createElement("strong");
    price.className = "offer-price";
    price.textContent = formatPrice(offer.price);

    offerDetails.append(badge, price);
    card.append(store, offerDetails);

    return card;
}
