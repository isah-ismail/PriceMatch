function createDemoOffer(offerId, retailerId, retailerName, price, isLowest, inStock = true) {
    return {
        offer_id: offerId,
        retailer: {
            retailer_id: retailerId,
            name: retailerName
        },
        retailer_product_id: null,
        retailer_product_name: null,
        product_url: null,
        price: Number(price).toFixed(2),
        currency: "TRY",
        in_stock: inStock,
        last_updated: "2026-11-15T09:00:00Z",
        is_lowest: isLowest
    };
}

function createDemoProduct(product) {
    const availableOffers = product.offers.filter(offer => offer.in_stock !== false);
    const prices = availableOffers.map(offer => Number(offer.price));

    return {
        product_id: product.product_id,
        name: product.name,
        brand: product.brand,
        category: product.category,
        model: product.model,
        variant: product.variant,
        image_url: null,
        lowest_price: prices.length ? Math.min(...prices).toFixed(2) : null,
        currency: "TRY",
        offer_count: product.offers.length,
        retailer_count: new Set(product.offers.map(offer => offer.retailer.retailer_id)).size,
        offers: product.offers
    };
}

const products = [
    createDemoProduct({
        product_id: 1,
        name: "Apple iPhone 16 128GB",
        brand: { brand_id: 1, name: "Apple" },
        category: { category_id: 1, name: "Electronics", parent_category_id: null },
        model: "iPhone 16",
        variant: "128 GB",
        offers: [
            createDemoOffer(101, 1, "Store A", 54999, false),
            createDemoOffer(102, 2, "Store B", 52999, true, null),
            createDemoOffer(103, 3, "Store C", 55999, false)
        ]
    }),
    createDemoProduct({
        product_id: 2,
        name: "Samsung Galaxy S25 256GB",
        brand: { brand_id: 2, name: "Samsung" },
        category: { category_id: 1, name: "Electronics", parent_category_id: null },
        model: "Galaxy S25",
        variant: "256 GB",
        offers: [
            createDemoOffer(201, 1, "Store A", 44999, false),
            createDemoOffer(202, 2, "Store B", 42999, true),
            createDemoOffer(203, 3, "Store C", 45999, false, false)
        ]
    }),
    createDemoProduct({
        product_id: 3,
        name: "Sony WH-1000XM5 Headphones",
        brand: { brand_id: 3, name: "Sony" },
        category: { category_id: 1, name: "Electronics", parent_category_id: null },
        model: "WH-1000XM5",
        variant: "Wireless headphones",
        offers: [
            createDemoOffer(301, 1, "Store A", 11999, false),
            createDemoOffer(302, 2, "Store B", 10999, true)
        ]
    }),
    createDemoProduct({
        product_id: 4,
        name: "Apple MacBook Air M4",
        brand: { brand_id: 1, name: "Apple" },
        category: { category_id: 1, name: "Electronics", parent_category_id: null },
        model: "MacBook Air M4",
        variant: "13-inch · 16 GB",
        offers: [
            createDemoOffer(401, 1, "Store A", 48999, false),
            createDemoOffer(402, 2, "Store B", 47500, true),
            createDemoOffer(403, 3, "Store C", 49999, false)
        ]
    }),
    createDemoProduct({
        product_id: 5,
        name: "PlayStation 5 Slim",
        brand: { brand_id: 4, name: "Sony" },
        category: { category_id: 2, name: "Gaming", parent_category_id: null },
        model: "PlayStation 5 Slim",
        variant: "1 TB",
        offers: [
            createDemoOffer(501, 1, "Store A", 26999, true),
            createDemoOffer(502, 2, "Store B", 25999, false, false)
        ]
    }),
    createDemoProduct({
        product_id: 6,
        name: "Nike Air Force 1",
        brand: { brand_id: 5, name: "Nike" },
        category: { category_id: 3, name: "Fashion", parent_category_id: null },
        model: "Air Force 1",
        variant: "White",
        offers: [
            createDemoOffer(601, 1, "Store A", 4999, false),
            createDemoOffer(602, 2, "Store B", 4599, true, null),
            createDemoOffer(603, 3, "Store C", 5199, false)
        ]
    })
];
