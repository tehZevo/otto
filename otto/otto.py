import sys
import os
import argparse
import json

from ollama import Client
from fastmcp import Client as MCPClient
from fastmcp.exceptions import ToolError

from .config import load_system_prompt, load_mcp_servers, load_config
from .utils import run_ollama, print_message, format_tools, print_tools, extract_tool_results
from .builtin_tools import BUILTIN_TOOLS, complete_task

parser = argparse.ArgumentParser(description="Otto Agent")
parser.add_argument("--config", default="otto.yaml", help="Path to config file")
args = parser.parse_args()

config = load_config(args.config)
config_dir = config.get("_config_dir", ".")
MODEL = config["ollama"]["model"]
CONTEXT_LENGTH = config["ollama"]["context_length"]
MAX_ITERS = config["max_iters"]
MAX_TOOLS_PER_ITER = config["max_tools_per_iter"]
NUM_RETRIES = config.get("num_retries", 10)

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", config["ollama"]["host"])

#TODO: use as default in config.py
USER_PROMPT = "Execute your given tasks autonomously without any further user input. Use the built-in task completion tool when you are finished."

def add_message(message, role="user"):
  messages.append({"role": role, "content": message})

def add_tool_message(name, content):
  messages.append({"role": "tool", "tool_name": name, "content": f"<tool_response name=\"{name}\">\n{content}\n</tool_response>"})

client = Client(host=OLLAMA_HOST)
messages = []

system_prompt = load_system_prompt(config["system_prompts"], config_dir)
add_message(system_prompt, role="system")

#TODO: avoid `ValueError: No MCP servers defined in the config` if no mcp servers defined
mcp_servers_config = load_mcp_servers(config["mcp_servers"], config_dir)
#TODO: create dummy client if empty
mcp_client = MCPClient(mcp_servers_config)

tools = []

async def append_message_and_call_tools(content, tool_calls):
  if content.strip() != "":
    add_message(content, role="assistant")
    print_message(messages[-1])
  
  # Limit the number of tools executed per iteration
  tools_to_execute = tool_calls[:MAX_TOOLS_PER_ITER]
  
  if len(tool_calls) > MAX_TOOLS_PER_ITER:
    print(f"⚠ Limiting tool execution to {MAX_TOOLS_PER_ITER} of {len(tool_calls)} requested tools")
  
  # Check for built-in tools first (like complete_task)
  built_in_tool_calls = []
  mcp_tool_calls = []
  
  for tool_call in tools_to_execute:
    if tool_call.function.name in BUILTIN_TOOLS:
      built_in_tool_calls.append(tool_call)
    else:
      mcp_tool_calls.append(tool_call)
  
  # Handle built-in tools first
  for tool_call in built_in_tool_calls:
    print(f"🔧 Calling built-in tool: {tool_call.function.name}")
    # print(f"   Arguments: {tool_call.function.arguments}")
    
    try:
      # For built-in tools, we call the function directly
      tool_result = BUILTIN_TOOLS[tool_call.function.name]()
      result_content = json.dumps(tool_result, indent=2)
    except Exception as e:
      result_content = f"ToolError: {str(e)}"
      # print(f"❌ Tool error: {e}")
      print(f"❌ {tool_call.function.name}")
    
    add_tool_message(tool_call.function.name, result_content)
    print_message(messages[-1])
  
  # Handle MCP tools
  for tool_call in mcp_tool_calls:
    print(f"🔧 Calling tool: {tool_call.function.name}")
    # print(f"   Arguments: {tool_call.function.arguments}")
    
    try:
      tool_result = await mcp_client.call_tool(tool_call.function.name, tool_call.function.arguments)
      # Extract content from result objects - only TextContent is allowed
      result_content = extract_tool_results(tool_result)
    except (ToolError, ValueError) as e:
      result_content = f"ToolError: {str(e)}"
      print(f"❌ Tool error: {e}")
    
    add_tool_message(tool_call.function.name, result_content)
    print_message(messages[-1])

async def agent_loop():
  add_message(USER_PROMPT, role="user")
  print(f"🚀 Starting agent loop (max iterations: {MAX_ITERS}, max retries: {NUM_RETRIES})")

  iters = 0
  tool_calls = []
  no_tools_retry_count = 0
  
  while True:
    print(f"\n🔄 Iteration {iters + 1}/{MAX_ITERS}")

    response = await run_ollama(client, MODEL, CONTEXT_LENGTH, messages, tools)
    
    up_tokens = response.prompt_eval_count
    down_tokens = response.eval_count
    print(f"⇄ API Request [⬆ {up_tokens} / ⬇ {down_tokens}]")
    tool_calls = response.message.tool_calls or []
    
    if len(tool_calls) > 0:
      print(f"🎯 Agent requested {len(tool_calls)} tool(s)")
      no_tools_retry_count = 0  # Reset retry counter when tools are called
    
    await append_message_and_call_tools(response.message.content, tool_calls)
    iters += 1

    # Check if complete_task was called in the last iteration
    if any(tool_call.function.name == "complete_task" for tool_call in tool_calls):
      print(f"✅ Agent completed (complete_task called)")
      break

    if iters >= MAX_ITERS:
      print(f"\n⏹ Stopped: Reached max iterations ({MAX_ITERS})")
      break
    if len(tool_calls) == 0:
      if no_tools_retry_count < NUM_RETRIES:
        no_tools_retry_count += 1
        print(f"🔄 No tool calls detected. Retry {no_tools_retry_count}/{NUM_RETRIES}...")
        add_message("No tool call detected. Please ensure that your message contains a tool call and is properly formatted.")
        print_message(messages[-1])
        continue
      else:
        print(f"✅ Agent completed (no more tools requested)")
        print(f"\n⏹ Stopped: Agent finished (no more tools after {NUM_RETRIES} retries)")
        break

async def main():
  global tools
  
  print("🔌 Initializing MCP client...")
  async with mcp_client:
    print("✅ MCP client initialized")
    
    # Load tools once at initialization
    print(f"📋 Fetching available tools from MCP servers...")
    raw_tools = await mcp_client.list_tools()
    tools = format_tools(raw_tools)
    
    # Add built-in tools to the tools list so they can be called by the agent
    for tool_name, tool_func in BUILTIN_TOOLS.items():
      # Create tool definition for built-in tools
      tool_def = {
        'type': 'function',
        'function': {
          'name': tool_name,
          'description': tool_func.__doc__ or f'Built-in tool: {tool_name}',
          'parameters': {}
        }
      }
      tools.append(tool_def)
    
    # Filter tools based on allowed list in config (mandatory whitelist)
    allowed_tools = config.get("tools", [])
    original_count = len(tools)
    
    print_tools(tools, allowed_tools)
    
    if not allowed_tools:
      # If tools list is empty or missing, no tools are available
      tools = []
      print(f"🔒 No tools configured in otto.yaml - agent cannot call any tools")
    else:
      # Filter to only allowed tools
      tools = [tool for tool in tools if tool["function"]["name"] in allowed_tools]
      filtered_count = len(tools)
      print(f"🔒 Using {filtered_count} allowed tools (from {original_count} total)")
      
      # Warn about tools in config that weren't found
      available_tool_names = {tool["function"]["name"] for tool in tools}
      missing_tools = set(allowed_tools) - available_tool_names
      if missing_tools:
        print(f"⚠ Warning: The following tools in config were not found: {', '.join(missing_tools)}")
    
    await agent_loop()
    print("\n✅ Agent loop completed")
