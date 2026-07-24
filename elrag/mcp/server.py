from fastmcp import FastMCP

from elrag.mcp.tools import register_tools

mcp = FastMCP("elrag-mcp", version="0.1.0")
register_tools(mcp)
mcp_app = mcp.http_app(path="/")
