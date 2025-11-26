from fastmcp import FastMCP
import subprocess

app = FastMCP()

@app.tool()
def execute_shell_command(cmd: str):
    """Run a command in the shell"""
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return p.stdout + p.stderr

app.run()