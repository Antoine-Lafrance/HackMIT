#!/usr/bin/env python3
"""
Minimalist Agent using Anthropic API with MCP Tools
Designed to run on Modal cloud computing platform.
"""

import json
import os
import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from requests import get, post
import modal
from anthropic import Anthropic
from fastapi import File, UploadFile

from typing import Annotated


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Modal app configuration


load_dotenv()


@dataclass
class AgentConfig:
    """Configuration for the agent."""

    anthropic_api_key: str
    model: str = "claude-3-5-haiku-20241022"
    max_tokens: int = 4096
    temperature: float = 0.7
    max_iterations: int = 1


class MinimalistAgent:
    """
    A minimalist agent that uses Anthropic API and can decide to use MCP tools.
    Designed to process JSON context in a loop and make tool usage decisions.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.anthropic = Anthropic(
            api_key=config.anthropic_api_key,
        )
        self.mcp_sessions: Dict[str, Any] = {}
        self.available_tools = get("https://antlaf6--mcp-list-tools-dev.modal.run")

        print("yoyooyo", self.available_tools)

    async def initialize_mcp_tools(
        self, mcp_servers: Optional[List[Dict[str, Any]]] = None
    ):
        """Initialize MCP tool connections."""
        if not mcp_servers:
            # Default example MCP servers - replace with your actual servers
            mcp_servers = []

        for server_config in mcp_servers:
            try:
                server_params = StdioServerParameters(
                    command=server_config.get("command", ""),
                    args=server_config.get("args", []),
                    env=server_config.get("env", {}),
                )

                session = await stdio_client(server_params)
                await session.initialize()

                # Get available tools from this server
                list_tools_result = await session.list_tools()
                server_name = server_config.get("name", "unknown")

                self.mcp_sessions[server_name] = session
                self.available_tools.extend(
                    [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "server": server_name,
                            "schema": (
                                tool.inputSchema if hasattr(tool, "inputSchema") else {}
                            ),
                        }
                        for tool in list_tools_result.tools
                    ]
                )

                logger.info(f"Initialized MCP server: {server_name}")

            except Exception as e:
                logger.error(f"Failed to initialize MCP server {server_config}: {e}")

    def create_system_prompt(self) -> str:
        """Create the system prompt including available tools."""
        base_prompt = """You are an assistant to a patient suffering of dementia. You are tasked with assuring the safety of this person.

Your workflow:
1. Analyze the provided JSON context (this is a segmented view of the what the person's environment looks like)
2. Determine if any available tools would be helpful
3. If tools are needed, respond with a structured decision indicating which tools to use and why
4. If no tools are needed, provide a direct analysis/response

Available tools:"""

        if self.available_tools:
            tools_desc = "\n".join(
                [
                    f"- {tool['name']}: {tool['description']}"
                    for tool in self.available_tools
                ]
            )
            base_prompt += f"\n{tools_desc}"
        else:
            base_prompt += "\nNo tools are currently available."

        base_prompt += """

When you want to use tools, respond in this JSON format:
{
    "decision": "use_tools",
    "reasoning": "Brief explanation of why tools are needed",
    "tools_to_use": [
        {
            "tool_name": "tool_name",
            "parameters": {...},
            "purpose": "what this tool call will accomplish"
        }
    ]
}

When no tools are needed, respond in this JSON format:
{
    "decision": "direct_response", 
    "reasoning": "Why no tools are needed",
    "response": "Your analysis/answer to the context"
}

Always be concise and focused on the key decisions and insights.

Here are some basic rules:

examples for calling the PEOPLE tool:

    If the person is seeing someone's face, always call the tool to remember the name and return its response. If you feel like you should update the person in question's profile, don't hesitate to do so.

examples for calling the TIMER tool:

    if the person is manipulating a kettle and setting it on the stove, set an timer for it (about 10 mins).

    if the person says that they should do something in x amount of minutes, add a timer for x minutes, as they said. 

"""

        return base_prompt

    async def process_context(
        self, context: Dict[str, Any], image_data: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Process JSON context and decide on tool usage.

        Args:
            context: JSON context to analyze
            image_data: Optional dict with 'data' (base64) and 'media_type' (e.g., 'image/jpeg')

        Returns:
            Agent's decision and reasoning
        """
        system_prompt = self.create_system_prompt()

        # Build message content
        message_content = [
            {
                "type": "text",
                "text": f"Analyze this context and decide on appropriate actions:\n\n{json.dumps(context, indent=2)}",
            }
        ]

        # Add image if provided
        if image_data and image_data.get("data"):
            message_content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_data.get("media_type", "image/jpeg"),
                        "data": image_data["data"],
                    },
                }
            )

        try:
            # Call Anthropic API
            response = self.anthropic.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": message_content}],
            )

            # Parse response
            response_text = response.content[0].text

            try:
                decision = json.loads(response_text)
                logger.info(f"Agent decision: {decision['decision']}")

                # If agent wants to use tools, execute them
                if decision.get("decision") == "use_tools":
                    decision["tool_results"] = await self.execute_tools(
                        decision.get("tools_to_use", [])
                    )

                return decision

            except json.JSONDecodeError:
                # If response isn't valid JSON, treat as direct response
                return {
                    "decision": "direct_response",
                    "reasoning": "Response was not structured as requested",
                    "response": response_text,
                }

        except Exception as e:
            logger.error(f"Error processing context: {e}")
            return {
                "decision": "error",
                "reasoning": f"Error occurred: {str(e)}",
                "response": None,
            }

    async def execute_tools(
        self, tools_to_use: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute the requested MCP tools."""
        results = []

        for tool_request in tools_to_use:
            tool_name = tool_request.get("tool_name")
            parameters = tool_request.get("parameters", {})

            # Find which server has this tool
            tool_info = None
            for tool in self.available_tools:
                if tool["name"] == tool_name:
                    tool_info = tool
                    break

            if not tool_info:
                results.append(
                    {
                        "tool_name": tool_name,
                        "status": "error",
                        "error": f"Tool '{tool_name}' not found",
                    }
                )
                continue

            try:
                server_name = tool_info["server"]
                session = self.mcp_sessions[server_name]

                # Call the tool
                result = await session.call_tool(tool_name, parameters)

                results.append(
                    {
                        "tool_name": tool_name,
                        "status": "success",
                        "result": result.content,
                    }
                )

                logger.info(f"Successfully executed tool: {tool_name}")

            except Exception as e:
                results.append(
                    {"tool_name": tool_name, "status": "error", "error": str(e)}
                )
                logger.error(f"Error executing tool {tool_name}: {e}")

        return results

    async def run_loop(self, contexts):
        """
        Main processing loop - processes a list of JSON contexts.

        Args:
            contexts: List of JSON contexts to process

        Returns:
            List of agent decisions and results
        """
        results = []

        logger.info(f"Starting processing loop with {len(contexts)} contexts")

        for i, context in enumerate(contexts):
            logger.info(f"Processing context {i+1}/{len(contexts)}")

            result = await self.process_context(context)
            result["context_index"] = i
            results.append(result)

            # Brief pause between contexts
            await asyncio.sleep(0.1)

        logger.info("Processing loop completed")
        return results

    async def cleanup(self):
        """Clean up MCP sessions."""
        for session_name, session in self.mcp_sessions.items():
            try:
                await session.close()
                logger.info(f"Closed MCP session: {session_name}")
            except Exception as e:
                logger.error(f"Error closing session {session_name}: {e}")


image = modal.Image.debian_slim().pip_install("fastapi[standard]")

app = modal.App("minimalist-anthropic-agent")

# Define Modal image with required dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "anthropic", "mcp", "pydantic", "fastapi", "uvicorn"
)


@app.function(image=image, secrets=[modal.Secret.from_name("anthropic-api-key")])
@modal.fastapi_endpoint(method="POST")
async def analyze_context_endpoint(
    context_data: dict, audio_file: Annotated[UploadFile, File()]
):
    """
    Endpoint for analyzing context via HTTP POST.

    Args:
        context_data: Dictionary containing 'context' and optional 'mcp_servers'

    Returns:
        Agent's analysis result
    """
    try:
        # Get API key from Modal secret
        api_key = os.environ["ANTHROPIC_API_KEY"]

        # Create agent configuration
        config = AgentConfig(anthropic_api_key=api_key)
        agent = MinimalistAgent(config)

        # Initialize MCP tools if provided
        mcp_servers = context_data.get("mcp_servers")
        if mcp_servers:
            await agent.initialize_mcp_tools(mcp_servers)

        # Get context from request
        context = context_data.get("context")
        if not context:
            return {"status": "error", "error": "No context provided in request"}

        # Get optional image data

        image_data = context_data.get("image_data")

        # Process the context with optional image
        result = await agent.process_context(context, image_data)

        # Add success status
        result["status"] = "success"

        return result

    except Exception as e:
        return {"status": "error", "error": str(e)}
