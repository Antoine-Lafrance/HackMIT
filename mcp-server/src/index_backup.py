#!/usr/bin/env python3
"""
src/index.py
Python translation of the MCP server for dementia aid tools
"""

import asyncio
import base64
import io
import json
import logging
import os
import signal
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import cv2
import numpy as np
from PIL import Image

from mcp import ClientSession, StdioServerParameters
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    TextContent,
    Tool,
)


class python_face_recognition_service:
    async def recognize_face(*args):
        pass


from supabase import create_client, Client


load_dotenv()


url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(url, key)

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize face recognition service
""" python_face_recognition_service = PythonFaceRecognitionService()
 """
# Server initialization - creates core MCP server instance
server = Server("dementia-aid-mcp-server")

# Tool definitions - defines the tools that the server can call

ping_tool = Tool(
    name="ping",
    description="Simple ping tool to test MCP connection",
    inputSchema={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Message to echo back",
                "default": "Hello from MCP!",
            },
        },
        "required": [],
    },
)

# Face recognition tool
face_recognition_tool = Tool(
    name="recognize_face",
    description="Identify a person from camera input using facial recognition",
    inputSchema={
        "type": "object",
        "properties": {
            "image_data": {
                "type": "string",
                "description": "Base64 encoded image data",
            },
            "operation": {
                "type": "string",
                "enum": ["identify", "add_face", "list_faces"],
                "description": (
                    "Operation to perform: identify (recognize face), "
                    "add_face (add new person), list_faces (get all known faces)"
                ),
            },
            "name": {
                "type": "string",
                "description": "Name of the person (required for add_face operation)",
            },
            "relationship": {
                "type": "string",
                "description": "Relationship to the person (required for add_face operation)",
            },
            "color": {
                "type": "string",
                "description": "UI color for the person (optional, defaults to blue)",
            },
        },
        "required": ["image_data", "operation"],
    },
)

timer_tool = Tool(
    name="manage_timer",
    description="Timer management for time-sensitive events",
    inputSchema={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["set"],
                "description": "Timer action",
            },
            "duration_minutes": {
                "type": "number",
                "description": "Duration in minutes",
            },
        },
        "required": ["action"],
    },
)

location_tool = Tool(
    name="monitor_location",
    description="Location monitoring and safety checks",
    inputSchema={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["check_safety"],
                "description": "Location action",
            },
        },
        "required": ["action"],
    },
)

# Tool handlers - contains the logic for each tool


async def handle_ping(args: Dict[str, Any]) -> CallToolResult:
    """Handle ping tool requests"""
    message = args.get("message", "Hello from MCP!")
    logger.info(f"Ping received: {message}")

    response_data = {
        "success": True,
        "echo": message,
        "timestamp": datetime.now().isoformat(),
        "server": "dementia-aid-mcp-server",
    }

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(response_data))]
    )


async def handle_face_recognition(args: Dict[str, Any]) -> CallToolResult:
    """Handle face recognition tool requests"""
    image_data = args.get("image_data")
    operation = args.get("operation")
    name = args.get("name")
    relationship = args.get("relationship")
    color = args.get("color", "blue")

    logger.info(f"Face recognition called with operation: {operation}")

    try:
        if operation == "identify":
            recognition_result = await python_face_recognition_service.recognize_face(
                image_data
            )
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(recognition_result))]
            )

        elif operation == "add_face":
            if not name or not relationship:
                error_response = {
                    "success": False,
                    "message": "Name and relationship are required for add_face operation",
                }
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(error_response))]
                )

            # Process image to get embedding
            image_buffer = await python_face_recognition_service.process_image(
                image_data
            )
            face_detections = await python_face_recognition_service.detect_faces(
                image_buffer
            )

            if len(face_detections) == 0:
                error_response = {
                    "success": False,
                    "message": "No face detected in the image. Please provide a clear image with a face.",
                }
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(error_response))]
                )

            # Add the first detected face to database
            new_face = await python_face_recognition_service.add_face(
                {
                    "name": name,
                    "relationship": relationship,
                    "color": color,
                    "face_embedding": face_detections[0]["embedding"],
                    "user_id": None,  # You might want to pass user_id from the client
                }
            )

            if new_face:
                success_response = {
                    "success": True,
                    "message": f"Successfully added {name} ({relationship}) to the database",
                    "person": new_face["name"],
                    "relationship": new_face["relationship"],
                    "color": new_face["color"],
                    "id": new_face["id"],
                }
                return CallToolResult(
                    content=[
                        TextContent(type="text", text=json.dumps(success_response))
                    ]
                )
            else:
                error_response = {
                    "success": False,
                    "message": "Failed to add face to database",
                }
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(error_response))]
                )

        elif operation == "list_faces":
            all_faces = await python_face_recognition_service.get_all_faces()
            response_data = {
                "success": True,
                "message": f"Found {len(all_faces)} known faces",
                "faces": [
                    {
                        "id": face["id"],
                        "name": face["name"],
                        "relationship": face["relationship"],
                        "color": face["color"],
                        "created_at": face["created_at"],
                    }
                    for face in all_faces
                ],
            }
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(response_data))]
            )

        else:
            error_response = {
                "success": False,
                "message": f"Unknown operation: {operation}. Supported operations: identify, add_face, list_faces",
            }
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(error_response))]
            )

    except Exception as error:
        logger.error(f"Error in face recognition: {error}")
        error_response = {
            "success": False,
            "message": "Face recognition failed",
            "error": str(error),
        }
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(error_response))]
        )


async def handle_timer(args: Dict[str, Any]) -> CallToolResult:
    """Handle timer tool requests"""
    logger.info("Timer management called")

    response_data = {
        "success": True,
        "message": "Timer processing...",
        "timer_id": f"timer_{int(datetime.now().timestamp() * 1000)}",
        "duration": args.get("duration_minutes", 30),
    }

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(response_data))]
    )


async def handle_location(args: Dict[str, Any]) -> CallToolResult:
    """Handle location monitoring tool requests"""
    logger.info("Location monitoring called")

    response_data = {
        "success": True,
        "message": "Location processing...",
        "is_safe": True,
        "location": "Unknown",
    }

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(response_data))]
    )


# Request handlers - handles the requests from the client


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """Handle list tools requests"""
    logger.info("Tools list requested")
    return [ping_tool, face_recognition_tool, timer_tool, location_tool]


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool call requests"""
    logger.info(f"Tool called: {name}, args: {arguments}")

    try:
        if name == "ping":
            return await handle_ping(arguments)
        elif name == "recognize_face":
            return await handle_face_recognition(arguments)
        elif name == "manage_timer":
            return await handle_timer(arguments)
        elif name == "monitor_location":
            return await handle_location(arguments)
        else:
            raise McpError(ErrorCode.METHOD_NOT_FOUND, f"Unknown tool: {name}")

    except Exception as error:
        logger.error(f"Error in tool {name}: {error}")
        raise McpError(ErrorCode.INTERNAL_ERROR, f"Tool {name} failed: {str(error)}")


# Server startup - starts the server and connects to the client


async def main():
    """Main function to start the MCP server"""
    logger.info("Starting Dementia Aid MCP Server...")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")

    try:
        # Initialize Python face recognition service
        logger.info("Initializing Python face recognition service...")
        # await python_face_recognition_service.initialize()

        # Test Supabase connection
        logger.info("Testing Supabase connection...")
        try:
            # Test basic connection
            response = supabase.table("faces").select("count").limit(1).execute()
            if response.data is None:
                logger.warning("Supabase connection warning")
                logger.warning(
                    "Face recognition database features may not work properly"
                )
            else:
                logger.info("✅ Supabase connection successful")

            # Test if faces table exists and is accessible
            table_test = supabase.table("faces").select("id").limit(1).execute()
            if table_test.data is None:
                logger.warning("⚠️  Faces table issue")
                logger.warning("You may need to run the database schema setup")
            else:
                logger.info("✅ Faces table accessible")

            # Test vector extension (if available)
            try:
                dummy_vector = [0.0] * 512  # Dummy vector
                vector_test = supabase.rpc(
                    "match_faces",
                    {
                        "query_embedding": dummy_vector,
                        "match_threshold": 0.1,
                        "match_count": 1,
                    },
                ).execute()

                if vector_test.data is None:
                    logger.warning("⚠️  Vector functions issue")
                    logger.warning(
                        "You may need to run the supabase-functions.sql setup"
                    )
                else:
                    logger.info("✅ Vector functions accessible")
            except Exception as vector_error:
                logger.warning(f"⚠️  Vector functions issue: {vector_error}")
                logger.warning("You may need to run the supabase-functions.sql setup")

        except Exception as connection_error:
            logger.error(f"❌ Supabase connection failed: {connection_error}")
            logger.error("Check your environment variables and network connection")

        # Start the server
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="dementia-aid-mcp-server",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities=None,
                    ),
                ),
            )

        logger.info("MCP Server connected and ready!")
        logger.info("Available tools:")
        logger.info("   - ping (test connectivity)")
        logger.info(
            "   - recognize_face (face identification, adding faces, listing faces)"
        )
        logger.info("   - manage_timer (timer management)")
        logger.info("   - monitor_location (location monitoring)")
        logger.info("")
        logger.info("Face recognition operations:")
        logger.info("   - identify: Recognize a person from an image")
        logger.info("   - add_face: Add a new person to the database")
        logger.info("   - list_faces: Get all known faces")

    except Exception as error:
        logger.error(f"Failed to start MCP server: {error}")
        sys.exit(1)


# Graceful shutdown handlers
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("\nShutting down MCP server gracefully...")
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Start server if this is the main module
if __name__ == "__main__":
    asyncio.run(main())
