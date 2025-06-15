from dotenv import load_dotenv
import os
import asyncio
import nest_asyncio
from typing import List, Dict, Any
import json
from contextlib import AsyncExitStack

from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

nest_asyncio.apply()
load_dotenv()

class GeminiMCPChatBot:

    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.sessions: Dict[str, ClientSession] = {}
        self.messages: List[types.Content] = []
        self.tool_config = None
        self.exit_stack = AsyncExitStack()
        self.resources = []

    def clean_schema_for_gemini(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(schema, dict):
            return schema
        cleaned = {}
        unsupported_keys = {
            'exclusiveMaximum', 'exclusiveMinimum', 'const', 'examples',
            'additionalProperties', '$schema', '$id', 'definitions'
        }
        supported_string_formats = {'enum', 'date-time'}
        for key, value in schema.items():
            if key in unsupported_keys:
                continue
            if key == 'format' and isinstance(value, str):
                if schema.get('type') == 'string' and value not in supported_string_formats:
                    continue
            if isinstance(value, dict):
                cleaned[key] = self.clean_schema_for_gemini(value)
            elif isinstance(value, list):
                cleaned[key] = [self.clean_schema_for_gemini(item) if isinstance(item, dict) else item for item in value]
            else:
                cleaned[key] = value
        return cleaned

    def load_server_config(self, config_path: str = "server_config.json") -> List[Dict]:
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            return [
                {
                    "name": name,
                    "params": StdioServerParameters(
                        command=cfg["command"],
                        args=cfg["args"],
                        env=cfg.get("env")
                    )
                }
                for name, cfg in config.get("mcpServers", {}).items()
            ]
        except Exception as e:
            print(f"❌ Failed to load server config: {e}")
            return []

    async def connect_to_server_and_setup_tools(self):
        servers = self.load_server_config()
        if not servers:
            print("❌ No server configurations found. Exiting.")
            return

        all_function_declarations = []

        for server in servers:
            name = server["name"]
            try:
                print(f"\n🔄 Connecting to {name} server...")
                read, write = await self.exit_stack.enter_async_context(stdio_client(server["params"]))
                session = await self.exit_stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                self.sessions[name] = session

                response = await session.list_tools()
                for tool in response.tools:
                    cleaned_schema = self.clean_schema_for_gemini(tool.inputSchema)
                    func_decl = types.FunctionDeclaration(
                        name=tool.name,
                        description=tool.description,
                        parameters=cleaned_schema
                    )
                    all_function_declarations.append(func_decl)
                    self.sessions[tool.name] = session
                    print(f"✅ Tool loaded: {tool.name}")

                # --- START: NEWLY ADDED CODE ---
                # Not all servers implement prompts. Handle this gracefully.
                try:
                    prompts_response = await session.list_prompts()
                    if prompts_response and prompts_response.prompts:
                        for prompt in prompts_response.prompts:
                            self.sessions[prompt.name] = session
                            print(f"🧠 Prompt loaded: {prompt.name}")
                except Exception as e:
                    if "Method not found" in str(e):
                        print(f"ℹ️ Server '{name}' does not provide prompts (this is normal).")
                    else:
                        print(f"⚠️ Could not list prompts from '{name}': {e}")
                # --- END: NEWLY ADDED CODE ---

                # Not all servers implement resources. We'll handle this gracefully.
                try:
                    resources_response = await session.list_resources()
                    if resources_response and resources_response.resources:
                        for res in resources_response.resources:
                            uri = str(res.uri)
                            self.resources.append(uri)
                            self.sessions[uri] = session
                            print(f"📚 Resource available: {uri}")
                except Exception as e:
                    # Check for the specific error to confirm it's what we expect.
                    if "Method not found" in str(e):
                        print(f"ℹ️ Server '{name}' does not provide resources (this is normal).")
                    else:
                        # If it's a different error, we still want to know about it.
                        print(f"⚠️ Could not list resources from '{name}': {e}")

            except Exception as e:
                print(f"❌ Failed to connect to {name} server: {e}")

        if all_function_declarations:
            self.tool_config = types.Tool(function_declarations=all_function_declarations)
            print(f"\n🎉 Total tools available: {len(all_function_declarations)}")
            await self.chat_loop()
        else:
            print("❌ No tools available. Exiting.")

    async def find_tool_session(self, name: str):
        return self.sessions.get(name)

    async def process_query(self, query: str):
        if query:
            self.messages.append(types.Content(role="user", parts=[types.Part(text=query)]))

        while True:
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=self.messages,
                    config=types.GenerateContentConfig(tools=[self.tool_config])
                )
            except Exception as e:
                print(f"❌ Generation error: {e}")
                break

            candidate = response.candidates[0]
            tool_calls = []
            new_parts = []

            for part in candidate.content.parts:
                if part.function_call:
                    tool_calls.append(part)
                elif hasattr(part, "text"):
                    print(f"\n🤖 {part.text}")
                    new_parts.append(part)

            if not tool_calls:
                if new_parts:
                    self.messages.append(types.Content(role="model", parts=new_parts))
                break

            for part in tool_calls:
                func_name = part.function_call.name
                func_args = part.function_call.args or {}
                print(f"\n🛠️ Calling tool '{func_name}' with args: {func_args}")
                try:
                    session = await self.find_tool_session(func_name)
                    if not session:
                        raise Exception(f"Tool '{func_name}' not found on any server")
                    result = await session.call_tool(func_name, arguments=func_args)
                    content = result.content

                    if isinstance(content, list):
                        content = {"results": content}
                    elif not isinstance(content, dict):
                        content = {"message": str(content)}

                    self.messages.append(types.Content(role="model", parts=[part]))
                    self.messages.append(types.Content(role="user", parts=[
                        types.Part(function_response={
                            "name": func_name,
                            "response": content
                        })
                    ]))
                except Exception as e:
                    print(f"❌ Tool execution failed: {e}")

    async def list_prompts(self):
        print("\n📋 Available prompts:")
        seen = set()
        for name, session in self.sessions.items():
            try:
                response = await session.list_prompts()
                for prompt in response.prompts:
                    if prompt.name in seen:
                        continue
                    seen.add(prompt.name)
                    print(f"🧠 {prompt.name}: {prompt.description}")
                    if prompt.arguments:
                        print("   Arguments:")
                        for arg in prompt.arguments:
                            arg_name = arg.name if hasattr(arg, 'name') else arg.get('name', '')
                            print(f"     - {arg_name}")
            except Exception:
                continue

    async def execute_prompt(self, prompt_name: str, args: Dict[str, str]):
        session = self.sessions.get(prompt_name)
        if not session:
            print(f"❌ Prompt '{prompt_name}' not found.")
            return
        try:
            result = await session.get_prompt(prompt_name, arguments=args)
            if result and result.messages:
                content = result.messages[0].content
                prompt_text = content.text if hasattr(content, "text") else str(content)
                print(f"\n🧠 Executing prompt '{prompt_name}'...")
                await self.process_query(prompt_text)
        except Exception as e:
            print(f"❌ Failed to execute prompt '{prompt_name}': {e}")

    async def get_resource(self, uri: str):
        session = self.sessions.get(uri)
        
        # If a direct lookup fails, try to find a session for the base URI scheme.
        # This handles dynamic resources like papers://{topic}.
        if not session and '://' in uri:
            uri_scheme = uri.split('://')[0] + '://'
            for known_key, s in self.sessions.items():
                if known_key.startswith(uri_scheme):
                    session = s
                    break  # Found a session for this scheme, so we'll use it.

        if not session:
            print(f"❌ Resource '{uri}' not found.")
            return
            
        try:
            result = await session.read_resource(uri=uri)
            if result and result.contents:
                print(f"\n📚 Resource: {uri}\n")
                print(result.contents[0].text)
            else:
                print("No content available.")
        except Exception as e:
            print(f"❌ Failed to read resource '{uri}': {e}")

    async def chat_loop(self):
        print("\n💬 Gemini MCP ChatBot Started!")
        print("Type your queries or '/prompt <name> <arg1=value1>' or '/prompts'. Type 'quit' to exit.")
        print("Use @<resource> to access resources like papers://folders or papers://<topic>")
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == "quit":
                    print("👋 Goodbye!")
                    break
                if query.startswith("/prompts"):
                    await self.list_prompts()
                    continue
                if query.startswith("/prompt"):
                    parts = query.split()
                    if len(parts) < 2:
                        print("Usage: /prompt <name> <arg1=value1>")
                        continue
                    prompt_name = parts[1]
                    args = dict(arg.split("=", 1) for arg in parts[2:] if "=" in arg)
                    await self.execute_prompt(prompt_name, args)
                    continue
                if query.startswith("@"):
                    uri = query[1:].strip()
                    if uri == "folders":
                        uri = "papers://folders"
                    elif not uri.startswith("papers://"):
                        safe_topic = uri.lower().replace(" ", "_")
                        uri = f"papers://{safe_topic}"
                    await self.get_resource(uri)
                    continue
                await self.process_query(query)
            except Exception as e:
                print(f"❌ Error: {e}")

async def main():
    bot = GeminiMCPChatBot()
    try:
        await bot.connect_to_server_and_setup_tools()
    finally:
        await bot.exit_stack.aclose()

if __name__ == "__main__":
    asyncio.run(main())