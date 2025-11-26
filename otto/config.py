import json
import yaml
import os
import re
from dotenv import load_dotenv

DEFAULT_MAX_TOOLS_PER_ITER = 1

def expand_env_vars(text):
  """
  Expand environment variables in text using ${VAR} or $VAR syntax.
  Returns the text with all environment variables replaced.
  """
  if not isinstance(text, str):
    return text
  
  # Pattern to match ${VAR} or $VAR
  def replace_var(match):
    var_name = match.group(1) or match.group(2)
    return os.environ.get(var_name, match.group(0))
  
  # Match ${VAR_NAME} or $VAR_NAME (word characters only for $VAR)
  pattern = r'\$\{([^}]+)\}|\$(\w+)'
  return re.sub(pattern, replace_var, text)

def load_config(path="otto.yaml"):
  # Load .env file from the same directory as the config file
  config_dir = os.path.dirname(os.path.abspath(path))
  env_file = os.path.join(config_dir, ".env")
  if os.path.exists(env_file):
    load_dotenv(env_file)
  
  with open(path, "r") as f:
    content = f.read()
    # Expand environment variables before parsing YAML
    content = expand_env_vars(content)
    config = yaml.safe_load(content)

  # Set default value for max_tools_per_iter if not present
  if "max_tools_per_iter" not in config:
    config["max_tools_per_iter"] = DEFAULT_MAX_TOOLS_PER_ITER
  
  # Store config directory for resolving relative paths
  config["_config_dir"] = config_dir
  return config
  
def load_system_prompt(prompt_files, base_dir="."):
  full_prompt = ""
  for filename in prompt_files:
    filepath = os.path.join(base_dir, filename)
    with open(filepath, "r", encoding="utf8") as f:
      content = f.read()
      # Expand environment variables in prompt content
      content = expand_env_vars(content)
      full_prompt += "\n\n" + content
  return full_prompt

def load_mcp_servers(mcp_files, base_dir="."):
  mcp_files = mcp_files or []
  servers = {}
  for filename in mcp_files:
    filepath = os.path.join(base_dir, filename)
    with open(filepath, "r") as f:
      content = f.read()
      # Expand environment variables before parsing JSON
      content = expand_env_vars(content)
      server = json.loads(content)["mcpServers"]
      servers.update(server)
  
  return {
    "mcpServers": servers
  }
