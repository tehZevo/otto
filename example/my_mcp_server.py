from fastmcp import FastMCP

mcp = FastMCP("My MCP Server")

@mcp.tool
def add_numbers(a: int, b: int) -> int:
    """ Adds 2 numbers"""
    return a + b

if __name__ == "__main__":
    mcp.run()