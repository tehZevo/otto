"""
Built-in tools that are always available to the agent.
These tools are not loaded from MCP servers but are part of the core agent functionality.
"""

import json
from typing import Dict, Any

def sleep() -> Dict[str, Any]:
    """
    Built-in tool to signal that the agent would like to pause work and exit the agentic loop.
    
    Returns:
        A dictionary with a 'completed' flag to indicate the agent should exit.
    """
    return {
        "completed": True,
        "message": "Task completion signal received. Exiting agent loop."
    }

# Dictionary mapping built-in tool names to their functions
BUILTIN_TOOLS = {
    "sleep": sleep
}
