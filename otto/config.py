import json
import yaml

DEFAULT_MAX_TOOLS_PER_ITER = 1

def load_config(path="otto.yaml"):
  with open(path, "r") as f:
    config = yaml.safe_load(f)

  # Set default value for max_tools_per_iter if not present
  if "max_tools_per_iter" not in config:
    config["max_tools_per_iter"] = DEFAULT_MAX_TOOLS_PER_ITER
  
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
