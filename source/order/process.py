from mcp.server.fastmcp import FastMCP
from openai import OpenAI
import tempfile
from dotenv import load_dotenv
import os

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

mcp = FastMCP('Process')

def get_or_create_vector_store(store_id: str):
    # Try to find existing vector store, else create
    stores = client.vector_stores.list()
    for store in stores:
        if store.name == f"{VECTOR_STORE_NAME}_{store_id}":
            return store
    return client.vector_stores.create(name=f"{VECTOR_STORE_NAME}_{store_id}")


@mcp.tool()
def seach_product_id(product_name: str, store_id: str):
    """Search memories in the vector store and return relevant chunks."""
    vector_store = get_or_create_vector_store(store_id)
    
    # The OpenAI API search method doesn't support filtering by file_ids directly
    # We'll use the standard search method which searches across all files in the vector store
    
    # Check if there are any files in the vector store
    files = client.vector_stores.files.list(vector_store_id=vector_store.id)
    if not files.data:
        return []
    
    # Enhance the query to improve fuzzy matching
    # Add some context to help the vector search understand we're looking for products
    enhanced_query = f"Find product name similar to: {product_name}"
    
    # Search across the vector store with improved parameters for better matching
    results = client.vector_stores.search(
        vector_store_id=vector_store.id,
        query=enhanced_query,
        max_num_results=50  # Increase results to find more potential matches
    )

    content_texts = [
        content.text
        for item in results.data
        for content in item.content
        if content.type == "text"
    ]

    return content_texts

@mcp.tool()
def process_order_product(product_ids: list[str], product_names: list[str], quantities: list[int], notes: list[str]):
    """Format product information into a JSON object with product_name, product_id, quantity, and note.
    
    Args:
        product_ids: The ID of the product
        product_names: The name of the product
        quantities: The quantity of the product
        notes: Any additional notes for the product
        
    Returns:
        JSON formatted order object with product information
    """
    import json
    
    # Create product info object
    product_info = []
    for product_id, product_name, quantity, note in zip(product_ids, product_names, quantities, notes):
        product_info.append({
            "product_name": product_name,
            "product_id": product_id,
            "quantity": quantity,
            "note": note if note is not None else ""
        })
    
    # Return as JSON string
    return json.dumps(product_info)
    

# @mcp.tool()
# def process_order(conversation: str, store_id: str, seach_product_id_result):
#     """Format content_texts into a list of order product objects with product information.
    
#     Args:
#         conversation: The conversation to process
#         store_id: The ID of the store to fetch products from
#         seach_product_id_result: The result of the search_product_id tool (can be string or dict)
        
#     Returns:
#         JSON formatted list of order product objects with product_name, product_id, quantity, and note
#     """
    
#     # Format content_texts into list of order product objects
#     import json
#     import re
    
#     # Parse the input based on its type
#     order_products = []
    
#     # Handle dictionary input (direct product data from vector store)
#     if isinstance(seach_product_id_result, dict):
#         for product_id, product_data in seach_product_id_result.items():
#             try:
#                 # Extract product information from the dictionary
#                 product_info = {
#                     "product_name": product_data.get("1st_name", ""),
#                     "product_id": product_id,
#                     "quantity": 1,  # Default quantity
#                     "note": ""  # Default empty note
#                 }
                
#                 # Extract quantity from conversation if possible
#                 quantity_match = re.search(r'\b(\d+)\s+' + re.escape(product_info["product_name"]), conversation, re.IGNORECASE)
#                 if quantity_match:
#                     product_info["quantity"] = int(quantity_match.group(1))
                
#                 # Extract note from conversation if possible
#                 note_match = re.search(r'note[\s:]*([^\n]+)\s+' + re.escape(product_info["product_name"]), conversation, re.IGNORECASE)
#                 if note_match:
#                     product_info["note"] = note_match.group(1).strip()
                
#                 order_products.append(product_info)
#             except Exception as e:
#                 # Skip invalid entries
#                 continue
    
#     # Handle list of strings input
#     elif isinstance(seach_product_id_result, list):
#         for text in seach_product_id_result:
#             try:
#                 # Parse the text to extract product information
#                 product_name = re.search(r'product[\s_-]?name[\s:]*([^\n,]+)', text, re.IGNORECASE)
#                 product_id = re.search(r'product[\s_-]?id[\s:]*([^\n,]+)', text, re.IGNORECASE)
#                 quantity = re.search(r'quantity[\s:]*([0-9]+)', text, re.IGNORECASE)
#                 note = re.search(r'note[\s:]*([^\n]+)', text, re.IGNORECASE)
                
#                 product_info = {
#                     "product_name": product_name.group(1).strip() if product_name else "",
#                     "product_id": product_id.group(1).strip() if product_id else "",
#                     "quantity": int(quantity.group(1)) if quantity else 1,
#                     "note": note.group(1).strip() if note else ""
#                 }
#                 order_products.append(product_info)
#             except Exception as e:
#                 # Skip invalid entries
#                 continue
    
#     # Handle string input (try to parse as JSON first)
#     elif isinstance(seach_product_id_result, str):
#         try:
#             # Try to parse as JSON
#             json_data = json.loads(seach_product_id_result)
#             if isinstance(json_data, dict):
#                 # Process as dictionary
#                 for product_id, product_data in json_data.items():
#                     try:
#                         product_info = {
#                             "product_name": product_data.get("1st_name", ""),
#                             "product_id": product_id,
#                             "quantity": 1,
#                             "note": ""
#                         }
#                         order_products.append(product_info)
#                     except Exception:
#                         # Skip this item and continue with the next one
#                         pass
#             elif isinstance(json_data, list):
#                 # Already in the right format
#                 order_products = json_data
#         except json.JSONDecodeError:
#             # Not valid JSON, try to parse as text
#             try:
#                 product_name = re.search(r'product[\s_-]?name[\s:]*([^\n,]+)', seach_product_id_result, re.IGNORECASE)
#                 product_id = re.search(r'product[\s_-]?id[\s:]*([^\n,]+)', seach_product_id_result, re.IGNORECASE)
#                 quantity = re.search(r'quantity[\s:]*([0-9]+)', seach_product_id_result, re.IGNORECASE)
#                 note = re.search(r'note[\s:]*([^\n]+)', seach_product_id_result, re.IGNORECASE)
                
#                 if product_name or product_id:
#                     product_info = {
#                         "product_name": product_name.group(1).strip() if product_name else "",
#                         "product_id": product_id.group(1).strip() if product_id else "",
#                         "quantity": int(quantity.group(1)) if quantity else 1,
#                         "note": note.group(1).strip() if note else ""
#                     }
#                     order_products.append(product_info)
#             except Exception:
#                 # Unable to parse
#                 pass
#         except Exception:
#             # General exception handling for the string processing
#             pass
    
#     # Return as JSON
#     return json.dumps(order_products)


if __name__ == "__main__":
    mcp.run(transport="stdio")