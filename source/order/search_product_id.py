from mcp.server.fastmcp import FastMCP
import requests
import json
import os


def save_product_name_mapping(store_id: str, original_name: str, replacement_name: str) -> None:
    """
    Save a mapping of original product name to replacement product name in a JSON file.
    
    Args:
        store_id: The store ID to save the mapping for
        original_name: The original product name
        replacement_name: The replacement product name that successfully found products
    """
    # Define the path to the mapping file
    memory_file_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    mapping_file = os.path.join(memory_file_dir, f"{store_id}_product_mappings.json")
    
    # Load existing mappings if the file exists
    mappings = {}
    if os.path.exists(mapping_file):
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
        except json.JSONDecodeError:
            # If the file is corrupted, start with an empty dictionary
            mappings = {}
    
    # Add or update the mapping
    mappings[original_name.lower()] = replacement_name.lower()
    
    # Save the updated mappings
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, ensure_ascii=False, indent=2)

mcp = FastMCP("SearchProductId")

@mcp.tool("search-product-id")
def search_product_id(product_name: str, store_id: str = "5341", replace_product_name: str = "null", api_token: str = "odaautomation2323") -> str:
    """
    Search for products by name and return the best match.
    
    Args:
        product_name: The product name to search for
        store_id: The store ID to search in (default: 5341)
        replace_product_name: Alternative product name to search if original search fails (default: "null")
        api_token: The API token for authentication (default: odaautomation2323)
        
    Returns:
        A JSON string containing the best matching product information
    """
    page = 1
    limit = 50
    all_products = []
    
    # Check if we have a saved mapping for this product name
    memory_file_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    mapping_file = os.path.join(memory_file_dir, f"{store_id}_product_mappings.json")
    
    # Load existing mappings if the file exists
    saved_mappings = {}
    if os.path.exists(mapping_file):
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                saved_mappings = json.load(f)
        except json.JSONDecodeError:
            # If the file is corrupted, continue with empty mappings
            pass
    
    # Check if we have a saved mapping for this product
    product_name_lower = product_name.lower()
    used_saved_mapping = False
    if product_name_lower in saved_mappings and replace_product_name == "null":
        # Use the saved mapping
        search_term = saved_mappings[product_name_lower]
        used_saved_mapping = True
    else:
        # Use the provided search term
        search_term = product_name if replace_product_name == "null" else replace_product_name
    
    # First attempt with the search term
    try:
        api_url = f"https://dev-api.oda.vn/web/v1/guest/automation/product-study/{api_token}/{store_id}?page={page}&limit={limit}&search={search_term}"
        response = requests.post(api_url)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Parse the JSON response
        response_json = response.json()
        
        if "data" in response_json and "products" in response_json["data"]:
            all_products = response_json["data"]["products"]
    except Exception as e:
        return json.dumps({"error": str(e)})
    
    # If no results found and we're using the original product name
    if not all_products:
        return json.dumps({"products": [], "message": f"Can not find. {product_name} has any other name?"})
    
    # If results found and we're using a replacement name, save the mapping
    if all_products and replace_product_name != "null":
        # Save the mapping to store_id.json
        save_product_name_mapping(store_id, product_name, replace_product_name)
        return json.dumps({
            "products": all_products, 
            "message": f"Found products for replacement name '{replace_product_name}'. Mapping saved."
        })
    
    # If multiple results, find the best match
    if len(all_products) > 1:
        # Score each product based on how well it matches the search term
        scored_products = []
        for product in all_products:
            score = 0
            product_name_lower = product.get("1st_name", "").lower()
            query_lower = search_term.lower()
            
            # Exact match gets highest score
            if product_name_lower == query_lower:
                score += 100
            # Contains all words in the query
            elif all(word in product_name_lower for word in query_lower.split()):
                score += 50
            # Contains some words in the query
            else:
                for word in query_lower.split():
                    if word in product_name_lower and len(word) > 2:
                        score += 10
            
            scored_products.append((score, product))
        
        # Sort by score (highest first)
        scored_products.sort(reverse=True, key=lambda x: x[0])
        
        # Return the best match
        best_product = scored_products[0][1]
        
        # Create appropriate message based on whether we used a saved mapping
        message = ""
        if used_saved_mapping:
            message = f"Using saved mapping '{product_name}' → '{search_term}'. Found {len(all_products)} products, returning best match."
        else:
            message = f"Found {len(all_products)} products, returning best match."
            
        return json.dumps({
            "products": [best_product], 
            "message": message,
            "used_mapping": used_saved_mapping
        })
    
    # If only one result, return it
    message = "Found exact match"
    if used_saved_mapping:
        message = f"Using saved mapping '{product_name}' → '{search_term}'. Found exact match."
        
    return json.dumps({
        "products": all_products, 
        "message": message,
        "used_mapping": used_saved_mapping
    })


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()