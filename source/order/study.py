from mcp.server.fastmcp import FastMCP
import requests
import json
import os
from openai import OpenAI
import tempfile
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

# Initialize OpenAI client with API key from environment variable
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("Warning: OPENAI_API_KEY environment variable not set. Please set it in your .env file.")
    # You can set a default API key here if needed
    # api_key = "your-default-api-key"

client = OpenAI(api_key=api_key)

VECTOR_STORE_NAME = "MEMORIES_PRODUCT"

mcp = FastMCP("Study")

def get_or_create_vector_store(store_id: str):
    # Try to find existing vector store, else create
    stores = client.vector_stores.list()
    for store in stores:
        if store.name == f"{VECTOR_STORE_NAME}_{store_id}":
            return store
    return client.vector_stores.create(name=f"{VECTOR_STORE_NAME}_{store_id}")

# # Load product data from the saved file
# def load_product_data():
#     """Load product data from the JSON file"""
#     try:
#         file_path = os.path.join(os.path.dirname(__file__), "memory_file", "product_link_id.json")
#         with open(file_path, 'r', encoding='utf-8') as f:
#             return json.load(f)
#     except FileNotFoundError:
#         return {}

# # Create product name to ID mapping
# def create_product_name_to_id_mapping():
#     """Create a mapping from product names to IDs"""
#     product_data = load_product_data()
#     name_to_id = {}
    
#     # Check if product_data is a dictionary and not an error response
#     if not isinstance(product_data, dict) or "success" in product_data and product_data["success"] is False:
#         print(f"Warning: Invalid product data format. Please use learn-product-data tool to fetch valid data.")
#         return name_to_id
    
#     for product_id, product_info in product_data.items():
#         # Check if product_info is a dictionary
#         if not isinstance(product_info, dict):
#             continue
            
#         # Use the 1st_name as the primary key
#         if product_info.get("1st_name"):
#             name_to_id[product_info["1st_name"].lower()] = product_id
        
#         # Also add 2nd_name and 3rd_name if they exist
#         if product_info.get("2nd_name"):
#             name_to_id[product_info["2nd_name"].lower()] = product_id
#         if product_info.get("3rd_name"):
#             name_to_id[product_info["3rd_name"].lower()] = product_id
    
#     return name_to_id

# # Initialize the mapping
# product_name_to_id = create_product_name_to_id_mapping()


@mcp.tool("learn-product-data")
def learn_product_data(api_token: str, supplier_company_id: str, buy_company_id: str, is_delete: bool = False, page: int = 1) -> str:
    """
    Fetches product data from a specified API URL using POST method
    and saves it to product_link_id.json file
    
    Args:
        api_token: The API token for authentication
        supplier_company_id: The ID of the supplier company to fetch products from
        buy_company_id: The ID of the buy company to fetch products from
        is_delete: Whether to delete existing files in the vector store
        page: The page number to fetch products from
    """
    try:
        vector_store = get_or_create_vector_store(supplier_company_id + '_' + buy_company_id)
        # Delete all existing files in the vector store
        try:
            files = client.vector_stores.files.list(vector_store_id=vector_store.id)
            if is_delete:
                for file in files:
                    client.vector_stores.files.delete(vector_store_id=vector_store.id, file_id=file.id)
        except Exception as e:
            return f"Error deleting existing files from vector store: {str(e)}"
        

        # Send GET request to the API
        # Initialize variables for pagination
        max_page = page + 5
        limit = 100
        total_products = 0
        file_ids = []  # List to store all file IDs
        
        while True:
            # Add pagination parameters to the API URL
            if not api_token or not supplier_company_id or not buy_company_id:
                return "Error: API token or supplier company ID or buy company ID is missing"
            api_url = f"https://dev-api.oda.vn/web/v1/guest/automation/product-study/{api_token}/{supplier_company_id}/{buy_company_id}?page={page}&limit={limit}"
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
                
                # Process this page of data
                page_data = {}
                page_product_count = 0
                for product in data:
                    if 'id' in product:
                        page_data[product['id']] = product
                        page_product_count += 1
                    elif 'product_id' in product:
                        page_data[product['product_id']] = product
                        page_product_count += 1
                
                total_products += page_product_count
                
                # Write this page of data to vector store
                with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as f:
                    # Convert dictionary to JSON string
                    json_data = json.dumps(page_data)
                    f.write(json_data)
                    f.flush()
                    try:
                        # Upload the file directly to the vector store
                        # The file_id will be generated by the API
                        file_response = client.vector_stores.files.upload(
                            vector_store_id=vector_store.id,
                            file=open(f.name, "rb")
                        )
                        
                        # Store the file ID with page information
                        current_file_id = file_response.id
                        file_ids.append(f"page_{page}:{current_file_id}")
                    except Exception as e:
                        return f"Error uploading page {page} to vector store: {str(e)}"
                
                # If fewer items than limit, we've reached the end
                if len(data) < limit:
                    break
                page += 1
                if page > max_page:
                    break
        
        # Return success message as string
        return f"Successfully saved {total_products} products to vector store {vector_store.id} with file ids: {', '.join(file_ids)}"
    except requests.exceptions.RequestException as e:
        return f"Error fetching data from API: {str(e)}"
    except json.JSONDecodeError:
        return "Error: The API response is not valid JSON"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

@mcp.tool("delete-product-data")
def delete_product_data(supplier_company_id: str, buy_company_id: str):
    """Delete all existing files in the vector store"""
    try:
        vector_store = get_or_create_vector_store(supplier_company_id + '_' + buy_company_id)
        files = client.vector_stores.files.list(vector_store_id=vector_store.id)
        for file in files:
            client.vector_stores.files.delete(vector_store_id=vector_store.id, file_id=file.id)
        return f"Successfully deleted all existing files from vector store {vector_store.id}"
    except Exception as e:
        return f"Error deleting existing files from vector store: {str(e)}"
    

# @mcp.prompt("learn-products")
# def learn_products_prompt(api_token: str, supplier_company_id: str, buy_company_id: str):
#     """
#     Let learn product data with api token is {api_token} and supplier company id is {supplier_company_id} and buy company id is {buy_company_id}. 
#     Let start with page = 1, after that page = page + 6 until no product to learn, it will stop.
#     """
#     return """Let learn product data with api token is {api_token} and supplier company id is {supplier_company_id} and buy company id is {buy_company_id}. 
# Let start with page = 1, after that page = page + 6 until no product to learn, it will stop."""



if __name__ == "__main__":
    mcp.run()
