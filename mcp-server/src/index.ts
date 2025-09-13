// src/index.ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ErrorCode,
  McpError,
} from "@modelcontextprotocol/sdk/types.js";

// Server initialization - creates core MCP server instance

const server = new Server(
  {
    name: "dementia-aid-mcp-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Tool definitions - defines the tools that the server can call

const pingTool = {
  name: "ping",
  description: "Simple ping tool to test MCP connection",
  inputSchema: {
    type: "object",
    properties: {
      message: {
        type: "string",
        description: "Message to echo back",
        default: "Hello from MCP!"
      }
    },
    required: []
  }
};

// Face recognition tool
const faceRecognitionTool = {
  name: "recognize_face",
  description: "Identify a person from camera input",
  inputSchema: {
    type: "object",
    properties: {
      image_data: { type: "string", description: "Base64 encoded image" },
      operation: { type: "string", enum: ["identify"], description: "Operation" }
    },
    required: ["image_data", "operation"]
  }
};

const timerTool = {
  name: "manage_timer", 
  description: "Timer management for time-sensitive events",
  inputSchema: {
    type: "object",
    properties: {
      action: { type: "string", enum: ["set"], description: "Timer action" },
      duration_minutes: { type: "number", description: "Duration in minutes" }
    },
    required: ["action"]
  }
};

const locationTool = {
  name: "monitor_location",
  description: "Location monitoring and safety checks", 
  inputSchema: {
    type: "object",
    properties: {
      action: { type: "string", enum: ["check_safety"], description: "Location action" }
    },
    required: ["action"]
  }
};

// Tool handlers - contains the logic for each tool

async function handlePing(args: any) {
  const message = args.message || "Hello from MCP!";
  console.log(`Ping received: ${message}`);
  
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify({
          success: true,
          echo: message,
          timestamp: new Date().toISOString(),
          server: "dementia-aid-mcp-server"
        })
      }
    ]
  };
}

async function handleFaceRecognition(args: any) {
  console.log("Face recognition called");
  return {
    content: [{
      type: "text",
      text: JSON.stringify({
        success: true,
        message: "Face recognition processing...",
        person: "Unknown",
        relationship: "Unknown",
        confidence: 0.0
      })
    }]
  };
}

async function handleTimer(args: any) {
  console.log("Timer management called");
  return {
    content: [{
      type: "text", 
      text: JSON.stringify({
        success: true,
        message: "Timer processing...",
        timer_id: `timer_${Date.now()}`,
        duration: args.duration_minutes || 30
      })
    }]
  };
}

async function handleLocation(args: any) {
  console.log("Location monitoring called");
  return {
    content: [{
      type: "text",
      text: JSON.stringify({
        success: true,
        message: "Location processing...",
        is_safe: true,
        location: "Unknown"
      })
    }]
  };
}


// Request handlers - handles the requests from the client

server.setRequestHandler(ListToolsRequestSchema, async () => {
  console.log("Tools list requested");
  
  return {
    tools: [
      pingTool,
      faceRecognitionTool,
      timerTool,
      locationTool
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  
  console.log(`Tool called: ${name}`, args);
  
  try {
    switch (name) {
      case "ping":
        return await handlePing(args);
      
      case "recognize_face":
        return await handleFaceRecognition(args);
      
      case "manage_timer":
        return await handleTimer(args);
      
      case "monitor_location":
        return await handleLocation(args);
      
      default:
        throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
    }
  } catch (error) {
    console.error(`Error in tool ${name}:`, error);
    throw new McpError(
      ErrorCode.InternalError, 
      `Tool ${name} failed: ${error instanceof Error ? error.message : String(error)}`
    );
  }
});

// Server startup - starts the server and connects to the client

async function main() {
  console.log("Starting Dementia Aid MCP Server...");
  console.log("Timestamp:", new Date().toISOString());
  
  try {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    
    console.log("MCP Server connected and ready!");
    console.log("Available tools:");
    console.log("   - ping (test connectivity)");
    console.log("   - recognize_face (face identification)");
    console.log("   - manage_timer (timer management)");
    console.log("   - monitor_location (location monitoring)");
    
  } catch (error) {
    console.error("Failed to start MCP server:", error);
    process.exit(1);
  }
}

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\nShutting down MCP server gracefully...');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\nShutting down MCP server gracefully...');
  process.exit(0);
});

// Start server if this is the main module
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    console.error("Fatal error:", error);
    process.exit(1);
  });
}