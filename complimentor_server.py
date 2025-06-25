from mcp.server.fastmcp import FastMCP
from pymongo import MongoClient
from bson.objectid import ObjectId

mongo_client = MongoClient("mongodb://localhost:27017/")

mcp = FastMCP("mongo")

@mcp.tool()
def create_user_collection_only(
    user_id: str, # user_id is now mandatory
    collection_name: str = "main"
) -> str:
    """
    Create an empty collection inside the user's MongoDB database.
    Do not create new documents inside the collection, just create the collection itself.

    Args:
        user_id: The ID of the user (used as the database name)
        collection_name: The name of the collection to create

    Returns:
        Confirmation string
    """
    try:
        user_db = mongo_client[user_id] # This line correctly uses the dynamic user_id

        if collection_name in user_db.list_collection_names():
            return f"Collection '{collection_name}' already exists in DB '{user_id}'."

        user_db.create_collection(collection_name)
        # FIX IS HERE: Use the actual user_id variable, not a hardcoded string
        return f"Empty collection '{collection_name}' was successfully created in DB '{user_id}'."

    except Exception as e:
        return f"Error creating collection: {str(e)}"

@mcp.tool()
def find_documents_by_filter(user_id: str, collection_name: str, filter_query: dict = {}) -> list:
    """
    Find documents in a collection that match a given filter query.
    """
    try:
        collection = mongo_client[user_id][collection_name]
        docs = collection.find(filter_query)
        return [{**doc, "_id": str(doc["_id"])} for doc in docs]
    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool()
def delete_document_by_id(user_id: str, collection_name: str, document_id: str) -> str:
    """
    Delete a single document from a collection by its MongoDB _id.
    """
    try:
        collection = mongo_client[user_id][collection_name]
        result = collection.delete_one({"_id": ObjectId(document_id)})
        return f"{result.deleted_count} document deleted."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def delete_documents_by_filter(user_id: str, collection_name: str, filter_query: dict) -> str:
    """
    Delete all documents that match a given filter query.
    """
    try:
        collection = mongo_client[user_id][collection_name]
        result = collection.delete_many(filter_query)
        return f"{result.deleted_count} documents deleted."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def update_document_by_id(user_id: str, collection_name: str, document_id: str, update_fields: dict) -> str:
    """
    Update a single document by _id.
    """
    try:
        collection = mongo_client[user_id][collection_name]
        result = collection.update_one({"_id": ObjectId(document_id)}, {"$set": update_fields})
        return f"{result.modified_count} document updated."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def update_documents_by_filter(user_id: str, collection_name: str, filter_query: dict, update_fields: dict) -> str:
    """
    Update all documents matching the filter with the specified fields.
    """
    try:
        collection = mongo_client[user_id][collection_name]
        result = collection.update_many(filter_query, {"$set": update_fields})
        return f"{result.modified_count} documents updated."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def count_documents(user_id: str, collection_name: str, filter_query: dict = {}) -> int:
    """
    Count documents in a collection matching the given filter.
    """
    try:
        collection = mongo_client[user_id][collection_name]
        return collection.count_documents(filter_query)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def get_all_documents(user_id: str, collection_name: str) -> list:
    """
    Retrieve all documents from a collection.
    """
    try:
        collection = mongo_client[user_id][collection_name]
        return [{**doc, "_id": str(doc["_id"])} for doc in collection.find()]
    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool()
def get_collection_schema(
    user_id: str, # user_id is now mandatory
    collection_name: str = "main"
) -> dict:
    """
    Returns sample schema (keys and types) from a MongoDB collection, based on a sample of documents.

    Args:
        user_id: The ID of the user (used as the database name)
        collection_name: The name of the collection

    Returns:
        A dictionary showing sample keys and their inferred types
    """
    try:
        user_db = mongo_client[user_id]

        if collection_name not in user_db.list_collection_names():
            return {"error": f"Collection '{collection_name}' does not exist."}

        collection = user_db[collection_name]
        sample = collection.find_one()

        if not sample:
            return {"info": "Collection is empty."}

        schema = {k: str(type(v).__name__) for k, v in sample.items() if k != "_id"}
        return schema

    except Exception as e:
        return {"error": str(e)}

def default_value_for_type(t: type) -> any:
    """Return a default value based on the given Python type."""
    if t == int:
        return 0
    if t == float:
        return 0.0
    if t == bool:
        return False
    if t == list:
        return []
    if t == dict:
        return {}
    return ""  # Default for str and others

@mcp.tool()
def insert_to_collection(
    user_id: str,
    collection_name: str,
    new_data: dict
) -> str:
    """
    Inserts a document into a MongoDB collection after validating it against existing schema.
    If schema mismatch is found, returns an error and asks for schema update approval.
    """
    try:
        user_db = mongo_client[user_id]

        if collection_name not in user_db.list_collection_names():
            return f"Error: Collection '{collection_name}' does not exist in DB '{user_id}'. Please create it first using 'create_user_collection_only'."

        collection = user_db[collection_name]
        sample = collection.find_one()

        if not sample:
            collection.insert_one(new_data)
            return f"First document inserted into collection '{collection_name}': {new_data}"

        existing_keys = set(sample.keys()) - {"_id"}
        new_keys = set(new_data.keys())

        extra_keys = new_keys - existing_keys
        if extra_keys:
            return (
                f"Error: Your document contains new fields that are not in the current schema: {list(extra_keys)}. "
                "Please use the tool 'update_collection_schema_fields' to update the schema first. "
                "Example: update_collection_schema_fields(user_id='{user_id}', collection_name='{collection_name}', new_fields={{'new_field_name': 'default_value'}})."
            )

        # Validate types for existing fields
        for key, value in new_data.items():
            if key in sample and type(value) != type(sample[key]):
                return (
                    f"Error: Type mismatch for field '{key}'. Expected '{type(sample[key]).__name__}', but got '{type(value).__name__}'. "
                    "Please provide data with matching types or update the schema if you intend to change the field type."
                )

        full_data = {}
        for key in existing_keys:
            if key in new_data:
                full_data[key] = new_data[key]
            else:
                inferred_type = type(sample[key])
                full_data[key] = default_value_for_type(inferred_type)

        collection.insert_one(full_data)
        return f"Document inserted into '{collection_name}' with full schema: {full_data}"

    except Exception as e:
        return f"Error inserting document: {str(e)}"

@mcp.tool()
def find_document_by_id(user_id: str, collection_name: str, document_id: str) -> dict:
    """
    Find a single document in a collection by its MongoDB _id.
    """
    try:
        collection = mongo_client[user_id][collection_name]
        doc = collection.find_one({"_id": ObjectId(document_id)})
        if not doc:
            return {"info": "Document not found."}
        doc["_id"] = str(doc["_id"])
        return doc
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_user_collections(user_id: str) -> list:
    """
    Return the list of collections inside the user's MongoDB database.
    """
    try:
        user_db = mongo_client[user_id]
        return user_db.list_collection_names()
    except Exception as e:
        return [f"Error: {str(e)}"]

@mcp.tool()
def update_collection_schema_fields(
    user_id: str,
    collection_name: str,
    new_fields: dict
) -> str:
    """
    Adds new fields with default values to all existing documents in the collection.
    If a field in `new_fields` already exists, its value will be updated across all documents.

    Args:
        user_id: The user's database
        collection_name: The collection to update
        new_fields: A dict of new fields and their default values (e.g., {"new_field": "default_value", "age": 0})

    Returns:
        Success or error message
    """
    try:
        user_db = mongo_client[user_id]
        collection = user_db[collection_name]

        if collection_name not in user_db.list_collection_names():
            return f"Error: Collection '{collection_name}' does not exist."

        update_result = collection.update_many(
            {},  # Apply to all docs
            {"$set": new_fields}
        )

        # Also, if there are no documents, this update_many will not create the fields in the schema.
        # We might want to explicitly insert an empty document with the new fields if the collection is empty.
        # This is an edge case, but important for schema consistency.
        if collection.count_documents({}) == 0:
            collection.insert_one(new_fields)
            return f"Collection was empty. Schema updated and an initial document with new fields inserted. New fields: {list(new_fields.keys())}."


        return f"Schema updated. {update_result.modified_count} documents modified with new fields: {list(new_fields.keys())}."

    except Exception as e:
        return f"Error updating schema: {str(e)}"

# Add new tools for demonstration and future use
@mcp.tool()
def delete_entire_collection(user_id: str, collection_name: str) -> str:
    """
    Deletes an entire collection from the user's database. USE WITH CAUTION as this operation is irreversible.

    Args:
        user_id: The ID of the user (used as the database name)
        collection_name: The name of the collection to delete

    Returns:
        Confirmation string
    """
    try:
        user_db = mongo_client[user_id]
        if collection_name not in user_db.list_collection_names():
            return f"Collection '{collection_name}' does not exist in DB '{user_id}'."
        
        user_db.drop_collection(collection_name)
        return f"Collection '{collection_name}' successfully deleted from DB '{user_id}'."
    except Exception as e:
        return f"Error deleting collection: {str(e)}"


# Step 3: Run the server (stdio)
if __name__ == "__main__":
    mcp.run(transport="stdio")