def format_tools(tools):
  return [{
    'type': 'function',
    'function': {
      'name': tool.name,
      'description': tool.description,
      'parameters': tool.inputSchema
    }
  } for tool in tools]

async def run_ollama(client, model, num_ctx, messages, tools):
  print(f"🤖 Calling Ollama model: {model}")
  #TODO: make ollama call async?
  return client.chat(
    model=model,
    messages=messages,
    tools=tools,
    stream=False,
    options={
      "num_ctx": num_ctx
    }
  )

def print_message(message):
  if message['role'] == 'system':
    print(f"⚙ {message['content']}")
  elif message['role'] == 'user':
    print(f"👤 {message['content']}")
  elif message['role'] == 'assistant':
    print(f"💬 {message['content']}")
  elif message['role'] == 'tool':
    print(f"🔧 {message['tool_name']}")
    # Print the tool response content with indentation for readability
    content = message['content']
    # Indent each line of the content for better formatting
    for line in content.split('\n'):
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
