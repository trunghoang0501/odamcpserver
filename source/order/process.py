from mcp.server.fastmcp import FastMCP
from openai import OpenAI
import tempfile
import requests
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
def seach_product_id(product_name: str, supplier_company_id: str, buy_company_id: str):
    """Search memories in the vector store and return relevant chunks."""
    vector_store = get_or_create_vector_store(supplier_company_id + '_' + buy_company_id)
    
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
    order_info = []
    for product_id, product_name, quantity, note in zip(product_ids, product_names, quantities, notes):
        order_info.append({
            "product_name": product_name,
            "product_id": product_id,
            "quantity": quantity,
            "note": note if note is not None else ""
        })
    
    # Return as JSON string
    return json.dumps(order_info)

@mcp.tool()
def create_oda_order(api_token: str, supplier_company_id: str, buy_company_id: str, order_info: list):
    """
    Creates a draft order in ODA.

    Args:
        api_token: The API token for authentication.
        supplier_company_id: The ID of the supplier company.
        buy_company_id: The ID of the buy company.
        order_info: A list of dictionaries representing the order information.

    Returns:
        The response from the ODA API.
    """
    import json

    api_url = f"https://dev-api.oda.vn/web/v1/guest/automation/make-draft-order/{api_token}/{supplier_company_id}/{buy_company_id}"
    
    try:
        # No need to parse JSON, order_info is already a list
        payload = {"order": order_info}
        response = requests.post(api_url, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
    

# @mcp.prompt("order")
# def order(api_token: str, supplier_company_id: str, buy_company_id: str, conversation: str):
#     """
#     Let search multiple product id first and process order product for this conversation for api_token is {api_token} and supplier company id is {supplier_company_id} and buy company id is {buy_company_id}. 
#     The conversation is: {conversation}
#     """
#     return """Let search multiple product id first and process order product for this conversation for api_token is {api_token} and supplier company id is {supplier_company_id} and buy company id is {buy_company_id}. 
#     The conversation is: {conversation}
# """


if __name__ == "__main__":
    mcp.run(transport="stdio")