import sys
import os
import argparse
import json
import time

from ollama import Client
from fastmcp import Client as MCPClient
from fastmcp.exceptions import ToolError

from .config import load_system_prompt, load_mcp_servers, load_config
from .utils import run_ollama, print_message, format_tools, print_tools, extract_tool_results, format_builtin_tools
from .builtin_tools import BUILTIN_TOOLS, sleep

parser = argparse.ArgumentParser(description="Otto Agent")
parser.add_argument("--config", default="otto.yaml", help="Path to config file")
parser.add_argument("--loop", "-l", action="store_true", help="Loop indefinitely")
parser.add_argument("--sleep", "-s", type=int, default=60, help="Sleep time in seconds between loops (default: 60)")
args = parser.parse_args()

config = load_config(args.config)
config_dir = config.get("_config_dir", ".")
MODEL = config["ollama"]["model"]
CONTEXT_LENGTH = config["ollama"]["context_length"]
#TODO: add NUM_PREDICT to config
MAX_ITERS = config["max_iters"]
MAX_TOOLS_PER_ITER = config["max_tools_per_iter"]
NUM_RETRIES = config.get("num_retries", 10)

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", config["ollama"]["host"])

#TODO: use as default in config.py
USER_PROMPT = "Execute your given tasks autonomously without any further user input. Use the built-in task completion tool when you are finished."

def add_message(message, role="user"):
  messages.append({"role": role, "content": message})

def add_tool_message(name, content):
  messages.append({"role": "tool", "tool_name": name, "content": f"<tool_response name=\"{name}\">\n{content}\n"})

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
    print(f"🔧 [Built-in]: {tool_call.function.name}")
    # print(f"   Arguments: {tool_call.function.arguments}")
    
    try:
      # For built-in tools, we call the function directly
      tool_result = BUILTIN_TOOLS[tool_call.function.name]()
      result_content = json.dumps(tool_result, indent=2)
    except Exception as e:
      result_content = f"ToolError: {str(e)}"
      print(f"❌ {tool_call.function.name}")
    
    add_tool_message(tool_call.function.name, result_content)
  
  # Handle MCP tools
  for tool_call in mcp_tool_calls:
    print(f"🔧 [MCP] {tool_call.function.name}")
    
    try:
      tool_result = await mcp_client.call_tool(tool_call.function.name, tool_call.function.arguments)
      # Extract content from result objects - only TextContent is allowed
      result_content = extract_tool_results(tool_result)
    except (ToolError, ValueError) as e:
      result_content = f"ToolError: {str(e)}"
      print(f"❌ Tool error: {e}")
    
    add_tool_message(tool_call.function.name, result_content)
    # print_message(messages[-1])

async def agent_loop():
  add_message(USER_PROMPT, role="user")
  print(f"🚀 Starting agent loop (max iterations: {MAX_ITERS}, max retries: {NUM_RETRIES})")

  iters = 0
  tool_calls = []
  no_tools_retry_count = 0
  
  while True:
    # print(f"\n🔄 Iteration {iters + 1}/{MAX_ITERS}")

    response = await run_ollama(client, MODEL, CONTEXT_LENGTH, messages, tools, num_predict=256)
    
    up_tokens = response.prompt_eval_count
    down_tokens = response.eval_count
    # print(f"⇄ API Request [⬆ {up_tokens} / ⬇ {down_tokens}]")
    tool_calls = response.message.tool_calls or []
    
    if len(tool_calls) > 0:
      # print(f"🎯 Agent requested {len(tool_calls)} tool(s)")
      no_tools_retry_count = 0  # Reset retry counter when tools are called
    
    await append_message_and_call_tools(response.message.content, tool_calls)
    iters += 1

    # Check if sleep was called in the last iteration
    if any(tool_call.function.name == "sleep" for tool_call in tool_calls):
      print(f"✅ Agent completed (sleep called)")
      break

    if iters >= MAX_ITERS:
      print(f"\n⏹ Stopped: Reached max iterations ({MAX_ITERS})")
      break
    if len(tool_calls) == 0:
      if no_tools_retry_count < NUM_RETRIES:
        no_tools_retry_count += 1
        print(f"🔄 No tool calls detected. Retry {no_tools_retry_count}/{NUM_RETRIES}...")
        add_message("No tool call detected. Please ensure that your message contains a tool call and is properly formatted.")
        # print_message(messages[-1])
        continue
      else:
        print(f"✅ Agent completed (no more tools requested)")
        print(f"\n⏹ Stopped: Agent finished (no more tools after {NUM_RETRIES} retries)")
        break

async def main():
  global tools
  
  print("🔌 Initializing MCP client...")
  try:
    async with mcp_client:
      print("✅ MCP client initialized")
      print(f"📋 Fetching available tools from MCP servers...")
      raw_tools = await mcp_client.list_tools()
      tools = format_tools(raw_tools) + format_builtin_tools(BUILTIN_TOOLS)
      
      allowed_tools = config.get("tools", [])
      original_count = len(tools)
      
      print_tools(tools, allowed_tools)
      
      # Always allow built-in tools regardless of configuration
      # Filter MCP tools to only allowed tools, but keep all built-in tools
      if not allowed_tools:
        # If tools list is empty or missing, only built-in tools are available
        tools = [tool for tool in tools if tool["function"]["name"] in BUILTIN_TOOLS]
        print(f"🔒 No tools configured in otto.yaml - only built-in tools available")
      else:
        # Filter MCP tools to only allowed tools, but keep all built-in tools
        mcp_tools = [tool for tool in tools if tool["function"]["name"] not in BUILTIN_TOOLS]
        builtin_tools = [tool for tool in tools if tool["function"]["name"] in BUILTIN_TOOLS]
        filtered_mcp_tools = [tool for tool in mcp_tools if tool["function"]["name"] in allowed_tools]
        tools = filtered_mcp_tools + builtin_tools
        filtered_count = len(tools)
        print(f"🔒 Using {filtered_count} allowed tools (from {original_count} total)")
        
        # Validate that all tools in config actually exist
        available_tool_names = {tool["function"]["name"] for tool in tools}
        missing_tools = set(allowed_tools) - available_tool_names
        if missing_tools:
          print(f"❌ Error: The following tools in config were not found: {', '.join(missing_tools)}")
          print("Exiting due to invalid tool references in otto.yaml")
          sys.exit(1)
      
      # Handle looping logic
      if args.loop:
        print("🔁 Looping infinitely with sleep interval of", args.sleep, "seconds")
        while True:
          await agent_loop()
          print(f"💤 Sleeping for {args.sleep} seconds before next loop...")
          time.sleep(args.sleep)
          # Reset messages for next loop
          messages.clear()
          # Re-add system prompt for next loop
          add_message(system_prompt, role="system")
      else:
        await agent_loop()
        print("\n✅ Agent loop completed")
  except Exception as e:
    print(f"❌ Error initializing MCP client or loading servers: {e}")
    print("Exiting due to MCP server loading failure")
    sys.exit(1)
