function formatPrice(price, currency = "TRY") {
    if (price === null || price === undefined || price === "") {
        return "Price unavailable";
    }

    const amount = Number(price);
    if (!Number.isFinite(amount)) return String(price);

    const currencyCode = /^[A-Z]{3}$/.test(currency) ? currency : "TRY";
    return new Intl.NumberFormat("tr-TR", {
        style: "currency",
        currency: currencyCode,
        maximumFractionDigits: 2
    }).format(amount);
}

function getCategoryPlaceholder(categoryName) {
    const category = (categoryName || "").toLocaleLowerCase("tr-TR");

    if (category.includes("elect")) return "💻";
    if (category.includes("gaming")) return "🎮";
    if (category.includes("fashion")) return "👟";
    if (category.includes("home")) return "🏠";
    return "🛍️";
}

function populateProductImage(container, imageUrl, categoryName, altText) {
    container.replaceChildren();

    if (imageUrl) {
        const image = document.createElement("img");
        image.src = imageUrl;
        image.alt = altText || "Product image";
        image.loading = "lazy";
        container.appendChild(image);
        return;
    }

    const placeholder = document.createElement("span");
    placeholder.className = "image-placeholder";
    placeholder.setAttribute("aria-hidden", "true");
    placeholder.textContent = getCategoryPlaceholder(categoryName);
    container.appendChild(placeholder);
}

function createProductCard(product) {
    const card = document.createElement("article");
    card.className = "product-card";

    const image = document.createElement("div");
    image.className = "product-image";
    populateProductImage(image, product.image_url, product.category?.name, product.name);

    const details = document.createElement("div");
    details.className = "product-details";

    const category = document.createElement("span");
    category.className = "product-category";
    category.textContent = product.category?.name || "Product";

    const name = document.createElement("h3");
    name.textContent = product.name || "Unnamed product";

    const brand = document.createElement("p");
    brand.className = "product-brand";
    brand.textContent = product.brand?.name
        ? "Brand: " + product.brand.name
        : "Brand not specified";

    const attributes = document.createElement("div");
    attributes.className = "product-attributes product-attributes-compact";

    [product.model && "Model: " + product.model, product.variant && "Variant: " + product.variant]
        .filter(Boolean)
        .forEach(value => {
            const attribute = document.createElement("span");
            attribute.textContent = value;
            attributes.appendChild(attribute);
        });

    const price = document.createElement("div");
    price.className = "product-price";

    const label = document.createElement("span");
    label.textContent = "Indicative price";

    const value = document.createElement("strong");
    value.textContent = formatPrice(product.lowest_price, product.currency);

    price.append(label, value);

    const storeCount = document.createElement("p");
    storeCount.className = "store-count";
    const offerCount = Number(product.offer_count) || 0;
    const retailerCount = Number(product.retailer_count) || 0;
    storeCount.textContent = offerCount + " offers from " + retailerCount + " sellers";

    const link = document.createElement("a");
    link.className = "compare-button";
    link.href = "product.html?id=" + encodeURIComponent(product.product_id);
    link.textContent = "Compare sellers →";

    details.append(category, name, brand);
    if (attributes.childElementCount) details.appendChild(attributes);
    details.append(price, storeCount, link);
    card.append(image, details);

    return card;
}

function createOfferCard(offer) {
    const card = document.createElement("article");
    card.className = offer.is_lowest
        ? "offer-card cheapest-offer"
        : "offer-card";

    const store = document.createElement("div");
    store.className = "offer-store";

    const icon = document.createElement("div");
    icon.className = "store-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = "🏬";

    const details = document.createElement("div");

    const name = document.createElement("h3");
    name.textContent = offer.retailer?.name || "Retailer";

    const description = document.createElement("p");
    if (offer.in_stock === true) {
        description.textContent = "In stock";
    } else if (offer.in_stock === false) {
        description.textContent = "Out of stock";
    } else {
        description.textContent = "Stock status unavailable";
    }

    details.append(name, description);
    store.append(icon, details);

    const offerDetails = document.createElement("div");
    offerDetails.className = "offer-details";

    const badge = document.createElement("span");
    badge.className = "offer-badge";
    badge.textContent = offer.is_lowest ? "BEST PRICE" : "SELLER OFFER";

    const price = document.createElement("strong");
    price.className = "offer-price";
    price.textContent = formatPrice(offer.price, offer.currency);

    offerDetails.append(badge, price);

    if (offer.product_url) {
        const link = document.createElement("a");
        link.className = "visit-store-button";
        link.href = offer.product_url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "Visit store";
        offerDetails.appendChild(link);
    }

    card.append(store, offerDetails);
    return card;
}
