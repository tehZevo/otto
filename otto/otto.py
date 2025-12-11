import sys
import os
import argparse
import json
import time

from fastmcp import Client as MCPClient
from fastmcp.exceptions import ToolError

from .config import load_system_prompt, load_mcp_servers, load_config
from .utils import run_model, print_message, format_tools, print_tools, extract_tool_results, format_builtin_tools, get_openai_client, format_tool_call
from .builtin_tools import BUILTIN_TOOLS, sleep


parser = argparse.ArgumentParser(description="Otto Agent")
parser.add_argument("--config", default="otto.yaml", help="Path to config file")
args = parser.parse_args()

config = load_config(args.config)
config_dir = config.get("_config_dir", ".")
MODEL = config["client"]["model"]
OPENAI_API_KEY = config["client"]["api_key"]
OPENAI_BASE_URL = config["client"]["base_url"]
CONTEXT_LENGTH = config["client"]["context_length"]
MAX_TOKENS = config["client"].get("max_tokens", 256)
MAX_ITERS = config["max_iters"]
MAX_TOOLS_PER_ITER = config["max_tools_per_iter"]
NUM_RETRIES = config.get("num_retries", 10)
LOOP = config.get("loop", False)
SLEEP_TIME = config.get("sleep_time", 60)

#TODO: use as default in config.py
USER_PROMPT = "Execute your given tasks autonomously without any further user input. Use the built-in task completion tool when you are finished."

def add_message(message, role="user"):
  messages.append({"role": role, "content": message})

def add_tool_message(tool_call_id, name, content):
  messages.append({"role": "tool", "tool_call_id": tool_call_id, "content": f"<tool_response name=\"{name}\">\n{content}\n"})

messages = []
client = get_openai_client(OPENAI_API_KEY, OPENAI_BASE_URL)

system_prompt = load_system_prompt(config["system_prompts"], config_dir)
add_message(system_prompt, role="system")

#TODO: avoid `ValueError: No MCP servers defined in the config` if no mcp servers defined
mcp_servers_config = load_mcp_servers(config["mcp_servers"], config_dir)
#TODO: create dummy client if empty
mcp_client = MCPClient(mcp_servers_config)

#TODO: make non global
tools = []

async def get_tool_calls():
  """Get tool calls from the model, retrying if necessary."""
  retry_count = 0
  while retry_count <= NUM_RETRIES:
    content, tool_calls, reasoning_content, up_tokens, down_tokens = await run_model(client, MODEL, messages, tools, MAX_TOKENS)
    print(f"⇄ API Request [⬆ {up_tokens} / ⬇ {down_tokens}]")
    
    tool_calls = tool_calls or []
    if len(tool_calls) > 0:
      return content, tool_calls, reasoning_content, up_tokens, down_tokens
    
    if retry_count < NUM_RETRIES:
      retry_count += 1
      print(f"🔄 No tool calls detected. Retry {retry_count}/{NUM_RETRIES}...")
      add_message("No tool call detected. Please ensure that your message contains a tool call and is properly formatted.")
    else:
      print(f"✅ Agent completed (no more tools requested)")
      print(f"\n⏹ Stopped: Agent finished (no more tools after {NUM_RETRIES} retries)")
      return None, None, None, 0, 0

async def append_message_and_call_tools(content, reasoning_content, tool_calls):
  tool_calls = tool_calls or []
  
  # Log reasoning content (thought bubble) if present
  if reasoning_content and reasoning_content.strip():
    print(f"💭 Agent reasoning:")
    for line in reasoning_content.strip().split('\n'):
      if line.strip():
        print(f"   {line}")
  
  # Log content (speech bubble) if present
  if content and content.strip():
    print(f"� Agent response:")
    for line in content.strip().split('\n'):
      if line.strip():
        print(f"   {line}")
  
  # Always add assistant message when there are tool calls
  # This is required by the OpenAI API - tool messages must follow an assistant message with tool_calls
  if len(tool_calls) > 0:
    assistant_msg = {"role": "assistant", "content": content or ""}
    # Add tool_calls to the assistant message
    assistant_msg["tool_calls"] = [
      {
        "id": tc.id,
        "type": "function",
        "function": {"name": tc.function.name, "arguments": tc.function.arguments}
      }
      for tc in tool_calls
    ]
    messages.append(assistant_msg)
  elif content is not None and content.strip() != "":
    # No tool calls, just add content if present
    add_message(content, role="assistant")

  if len(tool_calls) > MAX_TOOLS_PER_ITER:
    print(f"⚠ Limiting tool execution to {MAX_TOOLS_PER_ITER} of {len(tool_calls)} requested tools")
  
  tool_calls = tool_calls[:MAX_TOOLS_PER_ITER]
  
  # Check for built-in tools first (like complete_task)
  built_in_tool_calls = []
  mcp_tool_calls = []
  
  for tool_call in tool_calls:
    if tool_call.function.name in BUILTIN_TOOLS:
      built_in_tool_calls.append(tool_call)
    else:
      mcp_tool_calls.append(tool_call)
  
  # Handle built-in tools first
  for tool_call in built_in_tool_calls:
    print(f"🔧 [Built-in] {format_tool_call(tool_call.function.name, tool_call.function.arguments)}")
    
    try:
      # For built-in tools, we call the function directly
      tool_result = BUILTIN_TOOLS[tool_call.function.name]()
      result_content = json.dumps(tool_result, indent=2)
    except Exception as e:
      result_content = f"ToolError: {str(e)}"
      print(f"❌ {tool_call.function.name}")
    
    add_tool_message(tool_call.id, tool_call.function.name, result_content)
  
  # Handle MCP tools
  for tool_call in mcp_tool_calls:
    print(f"🔧 [MCP] {format_tool_call(tool_call.function.name, tool_call.function.arguments)}")
    
    try:
      # Parse arguments from JSON string to dictionary
      # OpenAI returns arguments as a JSON string, but MCP client expects a dict
      arguments = json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
      tool_result = await mcp_client.call_tool(tool_call.function.name, arguments)
      # Extract content from result objects - only TextContent is allowed
      result_content = extract_tool_results(tool_result)
    except (ToolError, ValueError, json.JSONDecodeError) as e:
      result_content = f"ToolError: {str(e)}"
      print(f"❌ Tool error: {e}")
    
    add_tool_message(tool_call.id, tool_call.function.name, result_content)
    # print_message(messages[-1])

async def agent_loop():
  print(f"🚀 Starting agent loop (max steps: {MAX_ITERS}, max retries: {NUM_RETRIES})")

  steps = 0
  current_tokens = 0
  
  while True:
    # Add user prompt with context information before each iteration
    if steps == 0:
      # First iteration - no token info yet
      prompt = f"{USER_PROMPT}\n\nIteration: {steps + 1}/{MAX_ITERS}"
    else:
      # Subsequent iterations - include token usage
      context_pct = int((current_tokens / CONTEXT_LENGTH) * 100)
      prompt = f"{USER_PROMPT}\n\nIteration: {steps + 1}/{MAX_ITERS} | Context: {current_tokens:,}/{CONTEXT_LENGTH:,} tokens ({context_pct}%)"
    
    add_message(prompt, role="user")
    
    result = await get_tool_calls()
    content, tool_calls, reasoning_content, up_tokens, down_tokens = result
    if tool_calls is None:
      return
    
    current_tokens = up_tokens
    
    await append_message_and_call_tools(content, reasoning_content, tool_calls)
    steps += 1
    
    # Show iteration counter
    context_pct = int((current_tokens / CONTEXT_LENGTH) * 100)
    print(f"📊 Iteration {steps}/{MAX_ITERS} | Context: {current_tokens:,}/{CONTEXT_LENGTH:,} tokens ({context_pct}%)")

    if any(tool_call.function.name == "sleep" for tool_call in tool_calls):
      print(f"✅ Agent completed (sleep called)")
      break

    if steps >= MAX_ITERS:
      print(f"\n⏹ Stopped: Reached max steps ({MAX_ITERS})")
      break

def setup_tools(mcp_tools):
  mcp_tools = format_tools(mcp_tools)
  builtin_tools = format_builtin_tools(BUILTIN_TOOLS)
  
  available_mcp_tool_names = {tool["function"]["name"] for tool in mcp_tools}
  allowed_mcp_tool_names = config.get("tools", []) or [] #handle cases where it's just `tools:`
  total_mcp_tool_count = len(mcp_tools)
  
  # allowed_mcp_tools = [tool for tool in mcp_tools if tool["function"]["name"] in allowed_tool_names]
  allowed_mcp_tools = [tool for tool in mcp_tools if tool["function"]["name"] in allowed_mcp_tool_names]
  disallowed_mcp_tools = [tool for tool in mcp_tools if tool["function"]["name"] not in allowed_mcp_tool_names]
  allowed_mcp_tool_count = len(allowed_mcp_tools)

  missing_tools = set(allowed_mcp_tool_names) - available_mcp_tool_names

  if missing_tools:
    print(f"❌ Error: The following tools in config were not found: {', '.join(missing_tools)}")
    print("Exiting due to invalid tool references in otto.yaml")
    sys.exit(1)
  
  print(f"🔒 Allowing {allowed_mcp_tool_count} of {total_mcp_tool_count} tools:")
  print_tools(allowed_mcp_tools, disallowed_mcp_tools)

  return allowed_mcp_tools + builtin_tools

async def main():
  global tools
  
  print("🔌 Initializing MCP client...")
  async with mcp_client:
    print(f"📋 Fetching available tools from MCP servers...")
    mcp_tools = await mcp_client.list_tools()
    tools = setup_tools(mcp_tools)

    while True:
      await agent_loop()
      if not LOOP:
        break
      print(f"💤 Sleeping for {SLEEP_TIME} seconds before next loop...")
      time.sleep(SLEEP_TIME)
      # Reset messages for next loop
      messages.clear()
      # Re-add system prompt for next loop
      add_message(system_prompt, role="system")
