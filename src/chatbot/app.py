from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
from pathlib import Path
import json
import asyncio
import nest_asyncio

nest_asyncio.apply()

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config" / "server_config.json"

class MCP_ChatBot:
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.chat_history = []
        self.available_tools = []
        self.available_prompts = []
        self.sessions = {}
        self.user_id = None # Store the user ID here

        # Define the initial system prompt
        # self.system_prompt = {
        #     'role': 'user',
        #     'content': "You are an intelligent assistant for managing personal and business data, specializing in interacting with MongoDB databases via provided tools. Your role is to interpret user intentions, convert them into appropriate tool calls, and present the results clearly and user-friendly.\n\n"
        #                "You can perform various data management operations: creating collections, finding, deleting, updating, inserting documents, counting documents, and retrieving collection schemas. You are also capable of listing and executing predefined prompts.\n\n"
        #                "Crucially, if you encounter an error during an 'insert_to_collection' operation that indicates new fields not present in the current schema, you MUST inform the user and instruct them to use the 'update_collection_schema_fields' tool first to add the new fields. Do not attempt to insert the document again until the schema is updated.\n\n"
        #                "**IMPORTANT:** You are the SOLE entity to communicate with the user. DO NOT print or display raw tool outputs. Instead, analyze the tool results and integrate them naturally into your conversational responses. Avoid generic phrases like 'Okay, I will...' or 'Let me try this again properly:'. Your response to the user should be concise, informative, and reflect the outcome of the tool operation directly, or ask for clarification if needed. If a tool call fails, explain the error to the user in a helpful manner and suggest a solution. If a tool call is successful, summarize the achievement for the user.\n\n"
        #                "When performing operations, assume the user's data is stored under their unique ID. Your default user ID for all MongoDB operations is the one provided at the start of the session. Do not ask for the user ID again unless explicitly instructed to or if it changes."
        # }
        self.system_prompt = {
                    'role': 'user',
                    'content': """You are an intelligent assistant for managing personal and business data, specializing in interacting with MongoDB databases via provided tools. Your role is to interpret user intentions, convert them into appropriate tool calls, and present the results clearly and user-friendly.

        You can perform various data management operations: creating collections, finding, deleting, updating, inserting documents, counting documents, and retrieving collection schemas. You are also capable of listing and executing predefined prompts.

        **Core Principles for Tool Usage and Response Generation:**

        1.  **Strict Context Adherence:**
            * Maintain awareness of the most recently discussed or implicitly targeted collection. If the user refers to a collection (e.g., "friends collection"), prioritize operations within that collection unless explicitly instructed otherwise.
            * If a user's request is ambiguous about the target collection, clarify with the user.

        2.  **Intent Understanding & Multi-Step Reasoning:**
            * If a user specifies a location or other attribute relative to another entity (e.g., "Refael lives where Goldis lives"), you MUST perform this as a multi-step operation:
                1.  First, use a tool (e.g., `find_document_by_id` or `find_documents_by_filter`) to retrieve the necessary information (e.g., Goldis's location).
                2.  Then, use the actual retrieved value (e.g., "Petah Tikva") as the argument for the subsequent tool call (e.g., `insert_to_collection` or `update_document_by_id`).
            * Do not insert or update with literal descriptive phrases like "Goldis's location" when an actual data value is expected.

        3.  **Data Integrity & No Hallucination:**
            * **Crucially, do NOT invent or hallucinate data.** If the user provides partial information for an insert/update (e.g., only "Remember book page 248" for a note, without a date or specific location), use only the provided information. If a required field is missing and cannot be logically inferred, you may:
                * Prompt the user to provide the missing information.
                * Use an appropriate default value (e.g., empty string, `None`, current date/time for dates if you have a tool for it).
            * **For current date/time:** Your internal time is now **{current_datetime_placeholder}**. Use this information when a user refers to "today" or "now" for dates or timestamps.
            * Ensure all inserted/updated data directly reflects the user's explicit request.

        4.  **Schema Validation & Correction:**
            * If an 'insert_to_collection' operation indicates new fields not present in the current schema, you MUST inform the user and instruct them to use 'update_collection_schema_fields' first. Provide the exact tool call format they need, including example new fields and default values. Do not retry the insertion until the schema is explicitly updated by the user.

        5.  **Communication Protocol:**
            * You are the SOLE entity to communicate with the user. DO NOT print or display raw tool outputs (e.g., JSON results, or direct text from tool function returns).
            * Analyze all tool results, including successful outcomes and errors.
            * Integrate tool results naturally into your conversational responses. Avoid generic phrases like "Okay, I will..." or "Let me try this again properly:".
            * Your response to the user should be concise, informative, and reflect the *outcome* of the tool operation directly.
            * If a tool call fails, explain the error to the user in a helpful, non-technical manner and suggest a clear solution or next steps.
            * If a tool call is successful, summarize the achievement or the retrieved information for the user in plain language.
            * Always confirm completed actions and ensure the user's intent was met.

        6.  **Error Handling for Tool Not Found:**
            * If a tool is not found, inform the user that the requested functionality is not available.

        """
                }

        # Extend the system prompt with collection inference and retrieval defaults
        self.system_prompt['content'] += """

        \n\nAdditional Guidance - Collection Inference and Retrieval Defaults:\n\n
        When the user requests data from an unspecified collection (e.g., "my friends"), do not ask for the collection name immediately. Instead:
        1) Call get_user_collections(user_id).
        2) Infer the best candidate collection(s) using name similarity with this priority list: ["friends", "friend", "contacts", "people", "friendsmain", "main"]. Prefer exact matches; otherwise choose the highest-similarity candidate.
        3) For the first viable candidate, call get_all_documents(user_id, collection_name). If empty, try the next candidate.
        4) If documents are found, extract and return the "name" field; if absent, choose a name-like field (e.g., "full_name", or concatenate "first_name" + "last_name"). Never fabricate values.
        5) If no collections match or all are empty, inform the user briefly and propose next steps: either provide the correct collection name or add entries via insert_to_collection.

        Act without asking clarifying questions unless the choice is ambiguous after attempts. Never invent data or assume documents exist.
        """

    async def connect_to_server(self, server_name, server_config):
        try:
            server_params = StdioServerParameters(**server_config)
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            
            try:
                response = await session.list_tools()
                for tool in response.tools:
                    self.sessions[tool.name] = session
                    self.available_tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema
                    })
                
                prompts_response = await session.list_prompts()
                if prompts_response and prompts_response.prompts:
                    for prompt in prompts_response.prompts:
                        self.sessions[prompt.name] = session
                        self.available_prompts.append({
                            "name": prompt.name,
                            "description": prompt.description,
                            "arguments": prompt.arguments
                        })
                resources_response = await session.list_resources()
                if resources_response and resources_response.resources:
                    for resource in resources_response.resources:
                        resource_uri = str(resource.uri)
                        self.sessions[resource_uri] = session
            
            except Exception as e:
                print(f"Error listing tools/prompts/resources from {server_name}: {e}")
                
        except Exception as e:
            print(f"Error connecting to {server_name}: {e}")

    async def connect_to_servers(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as file:
                data = json.load(file)
            servers = data.get("mcpServers", {})
            for server_name, server_config in servers.items():
                await self.connect_to_server(server_name, server_config)
        except Exception as e:
            print(f"Error loading server config: {e}")
            raise
    
    async def process_query(self, query):
        if len(self.chat_history) > 10:
            self.chat_history = self.chat_history[-9:] # Keep latest 9 user/assistant messages + current user query
        
        self.chat_history.append({'role': 'user', 'content': query})
        
        
        aggregated_text_output = []
        while True:
            messages_for_anthropic = []
            for msg in self.chat_history:
                messages_for_anthropic.append(msg)

            response = self.anthropic.messages.create(
                max_tokens=2024,
                model='claude-3-haiku-20240307',
                tools=self.available_tools,
                messages=messages_for_anthropic,
                system=self.system_prompt['content']
            )

            assistant_content = []
            has_tool_use = False

            for content in response.content:
                if content.type == 'text':
                    print(content.text)
                    assistant_content.append(content)
                    aggregated_text_output.append(content.text)
                elif content.type == 'tool_use':
                    has_tool_use = True
                    assistant_content.append(content)
                    # We append the assistant's tool_use message to history *before* calling the tool
                    self.chat_history.append({'role': 'assistant', 'content': assistant_content})

                    session = self.sessions.get(content.name)
                    if not session:
                        error_msg = f"Tool '{content.name}' not found. This indicates an internal configuration error."
                        print(f"Internal Error: {error_msg}") # Print for debugging, but model should explain
                        self.chat_history.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": {"error": error_msg}
                            }]
                        })
                        continue 

                    tool_arguments = content.input.copy()
                    # Ensure user_id is always passed, overriding if the default was sent by mistake
                    if self.user_id:
                        tool_arguments['user_id'] = self.user_id

                    try:
                        result = await session.call_tool(content.name, arguments=tool_arguments)
                        # NO DIRECT PRINTING OF TOOL RESULT HERE.
                        # The tool result is added to chat history, and the model will generate the user-facing text.
                        self.chat_history.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": result.content # Add the raw tool result here
                            }]
                        })
                    except Exception as e:
                        error_message = f"Tool '{content.name}' execution failed: {str(e)}"
                        # NO DIRECT PRINTING OF TOOL ERROR HERE.
                        # The error result is added to chat history, and the model will generate the user-facing text.
                        self.chat_history.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": {"error": error_message}
                            }]
                        })

            if not has_tool_use:
                # Only append assistant content if it was pure text, otherwise it was already appended after tool_use
                if all(c.type == 'text' for c in assistant_content):
                    self.chat_history.append({'role': 'assistant', 'content': assistant_content})
                break

        return "\n".join(aggregated_text_output).strip()

    async def ask(self, query: str) -> str:
        """Convenience wrapper to process a query and return assistant text."""
        return await self.process_query(query)

    async def get_resource(self, resource_uri):
        session = self.sessions.get(resource_uri)
        
        if not session and resource_uri.startswith("papers://"):
            for uri, sess in self.sessions.items():
                if uri.startswith("papers://"):
                    session = sess
                    break
            
        if not session:
            print(f"Resource '{resource_uri}' not found.")
            return
        
        try:
            result = await session.read_resource(uri=resource_uri)
            if result and result.contents:
                print(f"\nResource: {resource_uri}")
                print("Content:")
                # Ensure content is extracted correctly if it's a list of content blocks
                content_text = ""
                if isinstance(result.contents, list):
                    for item in result.contents:
                        if hasattr(item, 'text'):
                            content_text += item.text + "\n"
                        elif isinstance(item, str):
                            content_text += item + "\n"
                elif hasattr(result.contents, 'text'):
                    content_text = result.contents.text
                elif isinstance(result.contents, str):
                    content_text = result.contents

                print(content_text)
            else:
                print("No content available.")
        except Exception as e:
            print(f"Error reading resource: {e}")
    
    async def list_prompts(self):
        """List all available prompts."""
        if not self.available_prompts:
            print("No prompts available.")
            return
        
        print("\nAvailable prompts:")
        for prompt in self.available_prompts:
            print(f"- {prompt['name']}: {prompt['description']}")
            if prompt['arguments']:
                print(f"   Arguments:")
                for arg in prompt['arguments']:
                    arg_name = arg.name if hasattr(arg, 'name') else arg.get('name', '')
                    print(f"     - {arg_name}")
    
    async def execute_prompt(self, prompt_name, args):
        """Execute a prompt with the given arguments."""
        session = self.sessions.get(prompt_name)
        if not session:
            print(f"Prompt '{prompt_name}' not found.")
            return
        
        try:
            # Inject user_id into prompt arguments if available and not explicitly provided
            if self.user_id and 'user_id' not in args:
                args['user_id'] = self.user_id

            result = await session.get_prompt(prompt_name, arguments=args)
            if result and result.messages:
                prompt_content = result.messages[0].content
                
                if isinstance(prompt_content, str):
                    text = prompt_content
                elif hasattr(prompt_content, 'text'):
                    text = prompt_content.text
                else:
                    text = " ".join(item.text if hasattr(item, 'text') else str(item) 
                                     for item in prompt_content)
                
                print(f"\nExecuting prompt '{prompt_name}'...")
                await self.process_query(text)
        except Exception as e:
            print(f"Error executing prompt: {e}")
    
    async def chat_loop(self):
        print("\nMCP Chatbot Started!")
        print("Type your queries or 'quit' to exit.")
        print("Use @folders to see available topics")
        print("Use @<topic> to search papers in that topic")
        print("Use /prompts to list available prompts")
        print("Use /prompt <name> <arg1=value1> to execute a prompt")
        
        # Ask for user_id at the beginning
        while True:
            user_id_input = input("Please enter your User ID to start (e.g., 68511be6b86b76f4a3e5d35b): ").strip()
            if user_id_input:
                self.user_id = user_id_input
                print(f"User ID set to: {self.user_id}")
                break
            else:
                print("User ID cannot be empty. Please try again.")


        while True:
            try:
                query = input("\nQuery: ").strip()
                if not query:
                    continue
        
                if query.lower() == 'quit':
                    break
                
                if query.startswith('@'):
                    topic = query[1:]
                    if topic == "folders":
                        resource_uri = "papers://folders"
                    else:
                        resource_uri = f"papers://{topic}"
                    await self.get_resource(resource_uri)
                    continue
                
                if query.startswith('/'):
                    parts = query.split()
                    command = parts[0].lower()
                    
                    if command == '/prompts':
                        await self.list_prompts()
                    elif command == '/prompt':
                        if len(parts) < 2:
                            print("Usage: /prompt <name> <arg1=value1> <arg2=value2>")
                            continue
                        
                        prompt_name = parts[1]
                        args = {}
                        
                        for arg in parts[2:]:
                            if '=' in arg:
                                key, value = arg.split('=', 1)
                                args[key] = value
                        
                        await self.execute_prompt(prompt_name, args)
                    else:
                        print(f"Unknown command: {command}")
                    continue
                
                await self.process_query(query)
                        
            except Exception as e:
                print(f"\nError in chat loop: {str(e)}")
    
    async def cleanup(self):
        await self.exit_stack.aclose()

async def main():
    chatbot = MCP_ChatBot()
    try:
        await chatbot.connect_to_servers()
        await chatbot.chat_loop()
    finally:
        await chatbot.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
