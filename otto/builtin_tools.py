"""
Built-in tools that are always available to the agent.
These tools are not loaded from MCP servers but are part of the core agent functionality.
"""

import json
from typing import Dict, Any

def complete_task() -> Dict[str, Any]:
    """
    Built-in tool to signal that all tasks are complete and exit the agent loop.
    This tool allows the agent to explicitly signal that it has completed its tasks
    and should exit the loop, rather than relying on other mechanisms.
    
    Returns:
        A dictionary with a 'completed' flag to indicate the agent should exit.
    """
    return {
        "completed": True,
        "message": "Task completion signal received. Exiting agent loop."
    }

# Dictionary mapping built-in tool names to their functions
BUILTIN_TOOLS = {
    "complete_task": complete_task
}
