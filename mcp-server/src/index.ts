// src/index.ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ErrorCode,
  McpError,
} from "@modelcontextprotocol/sdk/types.js";
import { pythonFaceRecognitionService } from "./python-face-recognition.js";
import { supabase } from "./supabase.js";
import { Function_ } from "modal";

const echo = await Function_.lookup("my-deployed-app", "echo_string");

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
        default: "Hello from MCP!",
      },
    },
    required: [],
  },
};

// Face recognition tool
const faceRecognitionTool = {
  name: "recognize_face",
  description: "Identify a person from camera input using facial recognition",
  inputSchema: {
    type: "object",
    properties: {
      image_data: {
        type: "string",
        description: "Base64 encoded image data",
      },
      operation: {
        type: "string",
        enum: ["identify", "add_face", "list_faces"],
        description:
          "Operation to perform: identify (recognize face), add_face (add new person), list_faces (get all known faces)",
      },
      name: {
        type: "string",
        description: "Name of the person (required for add_face operation)",
      },
      relationship: {
        type: "string",
        description:
          "Relationship to the person (required for add_face operation)",
      },
      color: {
        type: "string",
        description: "UI color for the person (optional, defaults to blue)",
      },
    },
    required: ["image_data", "operation"],
  },
};

const timerTool = {
  name: "manage_timer",
  description: "Timer management for time-sensitive events",
  inputSchema: {
    type: "object",
    properties: {
      action: { type: "string", enum: ["set"], description: "Timer action" },
      duration_minutes: { type: "number", description: "Duration in minutes" },
    },
    required: ["action"],
  },
};

const locationTool = {
  name: "monitor_location",
  description: "Location monitoring and safety checks",
  inputSchema: {
    type: "object",
    properties: {
      action: {
        type: "string",
        enum: ["check_safety"],
        description: "Location action",
      },
    },
    required: ["action"],
  },
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
          server: "dementia-aid-mcp-server",
        }),
      },
    ],
  };
}

async function handleFaceRecognition(args: any) {
  const { image_data, operation, name, relationship, color } = args;

  console.log(`Face recognition called with operation: ${operation}`);

  try {
    switch (operation) {
      case "identify":
        const recognitionResult =
          await pythonFaceRecognitionService.recognizeFace(image_data);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(recognitionResult),
            },
          ],
        };

      case "add_face":
        if (!name || !relationship) {
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: false,
                  message:
                    "Name and relationship are required for add_face operation",
                }),
              },
            ],
          };
        }

        // Process image to get embedding
        const imageBuffer = await pythonFaceRecognitionService.processImage(
          image_data
        );
        const faceDetections = await pythonFaceRecognitionService.detectFaces(
          imageBuffer
        );

        if (faceDetections.length === 0) {
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: false,
                  message:
                    "No face detected in the image. Please provide a clear image with a face.",
                }),
              },
            ],
          };
        }

        // Add the first detected face to database
        const newFace = await pythonFaceRecognitionService.addFace({
          name,
          relationship,
          color: color || "blue",
          face_embedding: faceDetections[0].embedding,
          user_id: undefined, // You might want to pass user_id from the client
        });

        if (newFace) {
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  message: `Successfully added ${name} (${relationship}) to the database`,
                  person: newFace.name,
                  relationship: newFace.relationship,
                  color: newFace.color,
                  id: newFace.id,
                }),
              },
            ],
          };
        } else {
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: false,
                  message: "Failed to add face to database",
                }),
              },
            ],
          };
        }

      case "list_faces":
        const allFaces = await pythonFaceRecognitionService.getAllFaces();
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                message: `Found ${allFaces.length} known faces`,
                faces: allFaces.map((face) => ({
                  id: face.id,
                  name: face.name,
                  relationship: face.relationship,
                  color: face.color,
                  created_at: face.created_at,
                })),
              }),
            },
          ],
        };

      default:
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: false,
                message: `Unknown operation: ${operation}. Supported operations: identify, add_face, list_faces`,
              }),
            },
          ],
        };
    }
  } catch (error) {
    console.error("Error in face recognition:", error);
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            success: false,
            message: "Face recognition failed",
            error: error instanceof Error ? error.message : "Unknown error",
          }),
        },
      ],
    };
  }
}

async function handleTimer(args: any) {
  console.log("Timer management called");
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify({
          success: true,
          message: "Timer processing...",
          timer_id: `timer_${Date.now()}`,
          duration: args.duration_minutes || 30,
        }),
      },
    ],
  };
}

async function handleLocation(args: any) {
  console.log("Location monitoring called");
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify({
          success: true,
          message: "Location processing...",
          is_safe: true,
          location: "Unknown",
        }),
      },
    ],
  };
}

// Request handlers - handles the requests from the client

server.setRequestHandler(ListToolsRequestSchema, async () => {
  console.log("Tools list requested");

  return {
    tools: [pingTool, faceRecognitionTool, timerTool, locationTool],
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
      `Tool ${name} failed: ${
        error instanceof Error ? error.message : String(error)
      }`
    );
  }
});

// Server startup - starts the server and connects to the client

async function main() {
  console.log("Starting Dementia Aid MCP Server...");
  console.log("Timestamp:", new Date().toISOString());

  try {
    // Initialize Python face recognition service
    console.log("Initializing Python face recognition service...");
    //await pythonFaceRecognitionService.initialize();

    // Test Supabase connection
    console.log("Testing Supabase connection...");
    try {
      // Test basic connection
      const { data, error } = await supabase
        .from("faces")
        .select("count")
        .limit(1);
      if (error) {
        console.warn("Supabase connection warning:", error.message);
        console.warn(
          "Face recognition database features may not work properly"
        );
      } else {
        console.log("✅ Supabase connection successful");
      }

      // Test if faces table exists and is accessible
      const { data: tableTest, error: tableError } = await supabase
        .from("faces")
        .select("id")
        .limit(1);

      if (tableError) {
        console.warn("⚠️  Faces table issue:", tableError.message);
        console.warn("You may need to run the database schema setup");
      } else {
        console.log("✅ Faces table accessible");
      }

      // Test vector extension (if available)
      const { data: vectorTest, error: vectorError } = await supabase.rpc(
        "match_faces",
        {
          query_embedding: Array(512).fill(0), // Dummy vector
          match_threshold: 0.1,
          match_count: 1,
        }
      );

      if (vectorError) {
        console.warn("⚠️  Vector functions issue:", vectorError.message);
        console.warn("You may need to run the supabase-functions.sql setup");
      } else {
        console.log("✅ Vector functions accessible");
      }
    } catch (connectionError) {
      console.error("❌ Supabase connection failed:", connectionError);
      console.error("Check your environment variables and network connection");
    }

    const transport = new StdioServerTransport();
    await server.connect(transport);

    console.log("MCP Server connected and ready!");
    console.log("Available tools:");
    console.log("   - ping (test connectivity)");
    console.log(
      "   - recognize_face (face identification, adding faces, listing faces)"
    );
    console.log("   - manage_timer (timer management)");
    console.log("   - monitor_location (location monitoring)");
    console.log("");
    console.log("Face recognition operations:");
    console.log("   - identify: Recognize a person from an image");
    console.log("   - add_face: Add a new person to the database");
    console.log("   - list_faces: Get all known faces");
  } catch (error) {
    console.error("Failed to start MCP server:", error);
    process.exit(1);
  }
}

// Graceful shutdown
process.on("SIGINT", () => {
  console.log("\nShutting down MCP server gracefully...");
  process.exit(0);
});

process.on("SIGTERM", () => {
  console.log("\nShutting down MCP server gracefully...");
  process.exit(0);
});

// Start server if this is the main module
/* if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    console.error("Fatal error:", error);
    process.exit(1);
  });
} */

main();
