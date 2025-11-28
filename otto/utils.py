def format_tools(tools):
  return [{
    "type": "function",
    "function": {
      "name": tool.name,
      "description": tool.description,
      "parameters": tool.inputSchema
    }
  } for tool in tools]

async def run_ollama(client, model, num_ctx, messages, tools, num_predict=1024):
  #TODO: make ollama call async?
  return client.chat(
    model=model,
    messages=messages,
    tools=tools,
    stream=False,
    options={
      "num_ctx": num_ctx,
      "num_predict": num_predict
    }
  )

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
    print(f"💬 {content}")
  elif message["role"] == "tool":
    print(f"🔧 {message['tool_name']}")
    content = message["content"]
    for line in content.split("\n"):
      if line.strip():  # Only print non-empty lines
        print(f"   {line}")

def print_tools(tools, allowed_tools):
  # Get all tool names and sort alphabetically
  all_tool_names = sorted([tool["function"]["name"] for tool in tools])
  
  # Print tools with allowed/disallowed status
  print(f"Found {len(all_tool_names)} tools:")
  for tool_name in all_tool_names:
    if allowed_tools and tool_name in allowed_tools:
      print(f"✓ {tool_name}")
    else:
      print(f"✗ {tool_name}")

def extract_tool_results(tool_result):
  """
  Extract content from tool result objects - only TextContent is allowed.
  
  Args:
      tool_result: The result object from a tool call
  
  Returns:
      str: The extracted text content from the tool result
  
  Raises:
      ValueError: If the tool result contains non-text content or no text content
  """
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
