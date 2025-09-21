# MongoDB Data Management Chatbot

This project provides an interactive chatbot interface for managing data within MongoDB databases. It leverages the Multi-Channel Protocol (MCP) to expose a set of robust tools for database operations, and integrates with large language models (LLMs) to interpret user commands and execute these tools.

## Features

The chatbot offers a comprehensive set of functionalities for interacting with MongoDB, designed to be accessible through natural language commands:

### MongoDB Operations

* **Collection Management:**
    * `create_user_collection_only(user_id: str, collection_name: str = "main")`: Creates an empty collection within a user's dedicated MongoDB database.
    * `delete_entire_collection(user_id: str, collection_name: str)`: Permanently deletes an entire collection from a user's database. **Use with caution.**
    * `get_user_collections(user_id: str)`: Lists all collections present in a user's database.

* **Document Management:**
    * `insert_to_collection(user_id: str, collection_name: str, new_data: dict)`: Inserts a document into a specified collection. Includes schema validation to prevent accidental introduction of new fields or type mismatches.
    * `find_documents_by_filter(user_id: str, collection_name: str, filter_query: dict = {})`: Retrieves documents from a collection that match a given filter.
    * `find_document_by_id(user_id: str, collection_name: str, document_id: str)`: Retrieves a single document by its MongoDB `_id`.
    * `update_document_by_id(user_id: str, collection_name: str, document_id: str, update_fields: dict)`: Updates specific fields of a single document identified by its `_id`.
    * `update_documents_by_filter(user_id: str, collection_name: str, filter_query: dict, update_fields: dict)`: Updates specific fields for all documents matching a given filter.
    * `delete_document_by_id(user_id: str, collection_name: str, document_id: str)`: Deletes a single document by its MongoDB `_id`.
    * `delete_documents_by_filter(user_id: str, collection_name: str, filter_query: dict)`: Deletes all documents matching a given filter.
    * `count_documents(user_id: str, collection_name: str, filter_query: dict = {})`: Counts the number of documents in a collection that match a filter.
    * `get_all_documents(user_id: str, collection_name: str)`: Retrieves all documents from a specified collection.

* **Schema Interaction:**
    * `get_collection_schema(user_id: str, collection_name: str = "main")`: Returns a sample schema (keys and inferred types) from a collection based on existing documents.
    * `update_collection_schema_fields(user_id: str, collection_name: str, new_fields: dict)`: Adds new fields with default values to all existing documents in a collection. This tool is crucial for schema evolution when inserting documents with new fields.

### Chatbot Capabilities

* **User ID-based Data Isolation:** All MongoDB operations are scoped to a specific `user_id`, which acts as the database name, ensuring data separation for different users.
* **LLM Integration:** Supports various Large Language Models (LLMs) for natural language understanding:
    * **Anthropic:** Configurable via `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL`.
    * **Ollama:** Configurable via `OLLAMA_MODEL` for local model inference.
    * **Hugging Face:** Configurable via `HF_API_KEY` and `HF_MODEL` for inference API.
* **Conversational Interface:** Processes user queries, executes relevant tools, and provides clear, non-technical summaries of tool outcomes or errors.
* **Schema Mismatch Handling:** Specifically guides the user to use `update_collection_schema_fields` if an `insert_to_collection` operation encounters new fields not in the current schema.
* **Prompt Execution:** Allows listing and executing predefined prompts with arguments.
* **Resource Access:** Provides functionality to access resources identified by URIs (e.g., `papers://`).

## Repository Layout

```
config/                 # MCP server launch configuration
data/papers/            # Cached arXiv metadata (created at runtime)
src/chatbot/app.py      # CLI chatbot entry point
src/servers/mongo_server.py    # MongoDB FastMCP tool server
src/servers/research_server.py # Research FastMCP tool server
```

## Getting Started

### Prerequisites

* Python 3.11+
* A running MongoDB instance (defaults to `mongodb://localhost:27017/`).
* An Anthropic API key exported in your environment or stored in `.env`.
* Project dependencies installed via `uv pip install --system .` or `pip install -r requirements.txt`.

### Configure Environment

Create a `.env` file in the project root to load Anthropic credentials:

```env
ANTHROPIC_API_KEY="your_key_here"
ANTHROPIC_MODEL="claude-3-haiku-20240307"
```

`python-dotenv` will load these values automatically when the chatbot starts.

### Run the Services

1. Start the MongoDB and research MCP servers (the chatbot will launch them on demand using `config/server_config.json`).
2. Launch the chatbot CLI:

```bash
uv run src/chatbot/app.py
```

3. Provide a `user_id` when prompted, then interact using natural language commands. Use `quit` to exit.

## Usage Examples

* **Create a new collection:**
    `Query: Create a new collection for user data.` (The chatbot will likely ask for the collection name or suggest "main")
    `Query: Create a collection named 'customers'.`

* **Insert a document:**
    `Query: Insert a customer named John Doe with email john@example.com into the 'customers' collection.`

* **Find documents:**
    `Query: Find all customers in 'customers' where name is 'John Doe'.`
    `Query: Show me all documents in 'customers'.`

* **Update a document:**
    `Query: Update the customer with ID '65c7f...' in 'customers' to set their email to 'john.doe@newemail.com'.`

* **Delete documents:**
    `Query: Delete the customer with ID '65c7f...' from 'customers'.`
    `Query: Delete all customers named 'John Doe' from 'customers'.`

* **Check schema:**
    `Query: What is the schema for the 'customers' collection?`

* **Update schema (if insertion fails due to new fields):**
    If an `insert_to_collection` fails because of new fields, the chatbot will provide an error message similar to:
    `Error: Your document contains new fields that are not in the current schema: ['new_field']. Please use the tool 'update_collection_schema_fields' to update the schema first. Example: update_collection_schema_fields(user_id='YOUR_USER_ID', collection_name='YOUR_COLLECTION', new_fields={'new_field_name': 'default_value'}).`
    You would then execute the suggested command:
    `Query: /prompt update_collection_schema_fields user_id=YOUR_USER_ID collection_name=customers new_fields={'status':'active'}` (Note: The `/prompt` command expects dictionary-like strings for arguments; actual usage will depend on the `mcp.tool` argument parsing, which for `new_fields` expects a Python dict string).

* **List and execute prompts:**
    `Query: /prompts`
    `Query: /prompt my_custom_prompt arg1=value1`

## System Architecture

The project consists of three main components:

1.  **MongoDB Tools Server (`src/servers/mongo_server.py`):** exposes MongoDB CRUD utilities as MCP tools, scoped per user database. The chatbot launches it via stdio when needed.
2.  **Research Tools Server (`src/servers/research_server.py`):** wraps arXiv search/extraction features and publishes MCP resources/prompts backed by cached metadata.
3.  **Chatbot Client (`src/chatbot/app.py`):** connects to every MCP server listed in `config/server_config.json`, orchestrates tool calls based on Anthropic model responses, and handles the interactive CLI loop.

Communication between components is brokered by the `mcp` library over stdio. Anthropic's Messages API powers the natural-language reasoning layer.
