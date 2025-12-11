import openai
import os
import json
from .config import load_config

def get_openai_client(api_key, base_url=None):
  base_url = base_url or "https://api.openai.com/v1"
  return openai.AsyncOpenAI(api_key=api_key, base_url=base_url)

def format_tool_call(name, arguments_json):
  """Format a tool call as functionname(k=v, k=v, ...)"""
  try:
    args = json.loads(arguments_json) if isinstance(arguments_json, str) else arguments_json
    if not args:
      return f"{name}()"
    
    # Format arguments as k=v pairs
    arg_strs = []
    for k, v in args.items():
      # Format value: strings in quotes, others as-is
      if isinstance(v, str):
        v_str = f'"{v}"' if len(v) < 50 else f'"{v[:47]}..."'
      else:
        v_str = str(v)
      arg_strs.append(f"{k}={v_str}")
    
    return f"{name}({', '.join(arg_strs)})"
  except:
    return f"{name}(...)"

def format_tools(tools):
  return [{
    "type": "function",
    "function": {
      "name": tool.name,
      "description": tool.description,
      "parameters": tool.inputSchema
    }
  } for tool in tools]


async def run_model(client, model, messages, tools, max_tokens=1024):
  response = await client.chat.completions.create(
    model=model,
    messages=messages,
    tools=tools,
    stream=False,
    max_tokens=max_tokens
  )

  up_tokens = response.usage.prompt_tokens
  down_tokens = response.usage.completion_tokens
  message = response.choices[0].message
  
  return message.content, message.tool_calls, up_tokens, down_tokens

def truncate_message(content, n=100):
  #TODO: undo
  return content
  lines = content.strip().split("\n")
  content = lines[0]
  ellipsis = False
  if len(lines) > 1:
    ellipsis = True
  if len(content) > n:
    ellipsis = True
  if ellipsis:
    content = content[:n] + "..."
  return content

def print_message(message):
  if message["role"] == "system":
    print(f"⚙ {message['content']}")  
  elif message["role"] == "user":
    content = truncate_message(message["content"])
    print(f"👤 {content}")
  elif message["role"] == "assistant":
    content = truncate_message(message["content"])
    if content and content.strip():
      print(f"💬 {content}")
  elif message["role"] == "tool":
    print(f"🔧 {message['tool_name']}")
    content = message["content"]
    for line in content.split("\n"):
      if line.strip():  # Only print non-empty lines
        print(f"   {line}")

def print_tools(allowed_tools, disallowed_tools):
  allowed_names = sorted([tool["function"]["name"] for tool in allowed_tools])
  disallowed_names = sorted([tool["function"]["name"] for tool in disallowed_tools])
  
  for t in allowed_names:
    print(f"✓ {t}")
  for t in disallowed_names:
    print(f"✗ {t}")

def extract_tool_results(tool_result):
  # Extract content from result objects - only TextContent is allowed
  if isinstance(tool_result.content, list):
    # Validate that all content items are TextContent
    text_contents = []
    for item in tool_result.content:
      if hasattr(item, 'text'):
        text_contents.append(item.text)
      else:
        # Non-text content is not allowed
        content_type = type(item).__name__
        raise ValueError(f"Non-text content type not supported: {content_type}")
    
    # Require at least one text content
    if not text_contents:
      raise ValueError("Tool result must contain at least one text content item")
    
    result_content = "\n".join(text_contents)
  else:
    result_content = str(tool_result.content)
  
  return result_content

def format_builtin_tools(builtin_tools_dict):
  tools = []
  for tool_name, tool_func in builtin_tools_dict.items():
    tool_def = {
      "type": "function",
      "function": {
        "name": tool_name,
        "description": tool_func.__doc__ or f"Built-in tool: {tool_name}",
        "parameters": {}
      }
    }
    tools.append(tool_def)
  return tools
