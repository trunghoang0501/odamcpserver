from mcp.server.fastmcp import FastMCP
import requests
import json
import os

mcp = FastMCP("Study")

# Load product data from the saved file
def load_product_data():
    """Load product data from the JSON file"""
    try:
        file_path = os.path.join(os.path.dirname(__file__), "memory_file", "product_link_id.json")
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Create product name to ID mapping
def create_product_name_to_id_mapping():
    """Create a mapping from product names to IDs"""
    product_data = load_product_data()
    name_to_id = {}
    
    # Check if product_data is a dictionary and not an error response
    if not isinstance(product_data, dict) or "success" in product_data and product_data["success"] is False:
        print(f"Warning: Invalid product data format. Please use learn-product-data tool to fetch valid data.")
        return name_to_id
    
    for product_id, product_info in product_data.items():
        # Check if product_info is a dictionary
        if not isinstance(product_info, dict):
            continue
            
        # Use the 1st_name as the primary key
        if product_info.get("1st_name"):
            name_to_id[product_info["1st_name"].lower()] = product_id
        
        # Also add 2nd_name and 3rd_name if they exist
        if product_info.get("2nd_name"):
            name_to_id[product_info["2nd_name"].lower()] = product_id
        if product_info.get("3rd_name"):
            name_to_id[product_info["3rd_name"].lower()] = product_id
    
    return name_to_id

# Initialize the mapping
product_name_to_id = create_product_name_to_id_mapping()

@mcp.resource("products/{product_name}/id")
def get_product_id_from_product_name(product_name: str) -> str:
    """
    Returns id from product name
    """
    # Try exact match first
    if product_name.lower() in product_name_to_id:
        return product_name_to_id[product_name.lower()]
    
    # Try partial match
    for name, product_id in product_name_to_id.items():
        if product_name.lower() in name or name in product_name.lower():
            return product_id
    
    return f"Product '{product_name}' not found in database"

@mcp.tool("learn-product-data")
def learn_product_data(api_token: str, store_id: str) -> str:
    """
    Fetches product data from a specified API URL using POST method
    and saves it to product_link_id.json file
    
    Args:
        api_token: The API token for authentication
        store_id: The ID of the store to fetch products from
    """
    try:
        # Send GET request to the API
        # Initialize variables for pagination
        page = 1
        limit = 50
        all_data = {}
        
        while True:
            # Add pagination parameters to the API URL
            if not api_token or not store_id:
                return "Error: API token or store ID is missing"
            api_url = f"https://dev-api.oda.vn/web/v1/guest/automation/product-study/{api_token}/{store_id}?page={page}&limit={limit}"
            response = requests.post(api_url)
            response.raise_for_status()  # Raise exception for HTTP errors
            
            # Parse the JSON response
            response_json = response.json()
            
            # Check if response_json has a 'data' key
            if isinstance(response_json, dict) and 'data' in response_json:
                data = response_json['data']
            else:
                data = response_json
            
            # Check if there's no more product data
            if not data:
                break
                
        
            # If data is a list, check if it's empty
            if isinstance(data, list):
                if not data:
                    break
                # Convert list to dictionary with product ID as key
                for product in data:
                    if 'id' in product:
                        all_data[product['id']] = product
                    elif 'product_id' in product:
                        all_data[product['product_id']] = product
                # If fewer items than limit, we've reached the end
                if len(data) < limit:
                    break
            
            # Move to the next page
            page += 1
        
        # Define the path for saving the file
        file_path = os.path.join(os.path.dirname(__file__), "memory_file", f"{store_id}.json")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Save the combined data to a JSON file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        # Update the product name to ID mapping after learning new data
        global product_name_to_id
        product_name_to_id = create_product_name_to_id_mapping()
        
        return f"Successfully learned product data from {api_url} and saved to {store_id}.json"
    except requests.exceptions.RequestException as e:
        return f"Error fetching data from API: {str(e)}"
    except json.JSONDecodeError:
        return "Error: The API response is not valid JSON"
    except Exception as e:
        return f"Unexpected error: {str(e)}"
