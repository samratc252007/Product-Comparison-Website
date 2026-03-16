import requests
import json

# Test the new Walmart API
url = "https://realtime-walmart-data.p.rapidapi.com/search"

querystring = {
    "keyword": "mobile",
    "page": "1",
    "sort": "price_high"
}

headers = {
    'x-rapidapi-key': "439c2eeeebmshb8a3324b65fc1adp1ed1adjsnea3faa1113e3",
    'x-rapidapi-host': "realtime-walmart-data.p.rapidapi.com"
}

print("Testing Walmart API...")
print(f"URL: {url}")
print(f"Query: {querystring}\n")

try:
    response = requests.get(url, headers=headers, params=querystring)
    response.raise_for_status()

    print(f"[SUCCESS] Status Code: {response.status_code}\n")

    response_data = response.json()
    products = response_data.get("results", [])

    print(f"Total Results Found: {response_data.get('totalResults', 0)}")
    print(f"Products in Page: {len(products)}\n")
    print("=" * 80)

    if products:
        for idx, product in enumerate(products[:5], 1):
            print(f"\nProduct {idx}:")
            print(f"   Name: {product.get('name', 'N/A')}")
            print(f"   Price: {product.get('price', 'N/A')}")
            print(f"   Original Price: {product.get('originalPrice', 'N/A')}")
            print(f"   Rating: {product.get('rating', 'N/A')}")
            print(f"   Reviews: {product.get('numberOfReviews', 'N/A')}")
            print(f"   Image: {product.get('image', 'N/A')}")
            print(f"   URL: {product.get('canonicalUrl', 'N/A')}")
            print(f"   Availability: {product.get('availability', 'N/A')}")
            print(f"   Seller: {product.get('sellerName', 'N/A')}")
            print("-" * 80)
    else:
        print("[ERROR] No products found in response!")
        print("\nFull Response Keys:")
        print(json.dumps(list(response_data.keys()), indent=2))

except requests.exceptions.RequestException as e:
    print(f"[ERROR] Request Error: {e}")
except json.JSONDecodeError as e:
    print(f"[ERROR] JSON Decode Error: {e}")
