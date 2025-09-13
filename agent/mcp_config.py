"""MCP (Model Context Protocol) configuration and client setup."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


@dataclass
class MCPToolResult:
    """Result from MCP tool execution."""
    success: bool
    result: Any
    error: Optional[str] = None


class MCPClient:
    """MCP client for tool calling."""
    
    def __init__(self, server_params: StdioServerParameters):
        self.server_params = server_params
        self.session: Optional[ClientSession] = None
        self._available_tools: List[Dict[str, Any]] = []
    
    async def connect(self) -> bool:
        """Connect to MCP server."""
        try:
            # Create stdio client connection
            self.stdio_client = stdio_client(self.server_params)
            self.session = await self.stdio_client.__aenter__()
            
            # Initialize the session
            await self.session.initialize()
            
            # Get available tools
            tools_result = await self.session.list_tools()
            self._available_tools = tools_result.tools if tools_result else []
            
            logger.info(f"Connected to MCP server. Available tools: {len(self._available_tools)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MCP server."""
        if self.session and hasattr(self, 'stdio_client'):
            try:
                await self.stdio_client.__aexit__(None, None, None)
                logger.info("Disconnected from MCP server")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """Call a tool via MCP."""
        if not self.session:
            return MCPToolResult(success=False, error="Not connected to MCP server")
        
        try:
            # Call the tool
            result = await self.session.call_tool(tool_name, arguments)
            
            return MCPToolResult(
                success=True,
                result=result.content if result else None
            )
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e)
            )
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools."""
        return self._available_tools.copy()
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is available."""
        return any(tool.get('name') == tool_name for tool in self._available_tools)


class MCPServerConfig:
    """Configuration for MCP servers."""
    
    @staticmethod
    def get_default_server() -> StdioServerParameters:
        """Get default MCP server configuration."""
        # This would typically point to your MCP server executable
        # For this example, we'll assume a Python-based MCP server
        return StdioServerParameters(
            command="python",
            args=["-m", "mcp_server"],  # Your MCP server module
            env=None
        )
    
    @staticmethod
    def get_custom_server(command: str, args: List[str], env: Optional[Dict[str, str]] = None) -> StdioServerParameters:
        """Get custom MCP server configuration."""
        return StdioServerParameters(
            command=command,
            args=args,
            env=env
        )


async def create_mcp_client(server_params: Optional[StdioServerParameters] = None) -> MCPClient:
    """Create and connect MCP client."""
    if server_params is None:
        server_params = MCPServerConfig.get_default_server()
    
    client = MCPClient(server_params)
    connected = await client.connect()
    
    if not connected:
        raise RuntimeError("Failed to connect to MCP server")
    
    return client
