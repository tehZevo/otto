import json

import yaml

def load_config(path="otto.yaml"):
  with open(path, "r") as f:
    config = yaml.safe_load(f)
  
  return config
  
def load_system_prompt(prompt_files):
  full_prompt = ""
  for filename in prompt_files:
    with open(filename, "r", encoding="utf8") as f:
      full_prompt += "\n\n" + f.read()
  return full_prompt

def load_mcp_servers(mcp_files):
  mcp_files = mcp_files or []
  servers = {}
  for filename in mcp_files:
    with open(filename, "r") as f:
      server = json.loads(f.read())["mcpServers"]
      servers.update(server)
  
  return {
    "mcpServers": servers
  }
