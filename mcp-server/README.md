# Dementia Aid MCP Server

A Model Context Protocol (MCP) server that provides tools for dementia assistance, including face recognition, timer management, and location monitoring.

## Overview

This MCP server acts as a bridge between AI agents (like Modal) and dementia aid functionality. It provides three main tools that can be called by AI agents to assist dementia patients.

## Architecture

```
Modal Agent ←→ MCP Server ←→ Tool Implementations
     ↓              ↓              ↓
  AI Logic    JSON-RPC Protocol   Face Recognition
  Decision    stdio transport     Timer Management  
  Making      Tool Routing        Location Monitoring
```

## Available Tools

### 1. **Ping Tool** (`ping`)
- **Purpose**: Test connectivity between agent and server
- **Parameters**: 
  - `message` (optional): Message to echo back
- **Returns**: Success status, echo message, timestamp, server info

### 2. **Face Recognition Tool** (`recognize_face`)
- **Purpose**: Identify people from camera input
- **Parameters**:
  - `image_data` (required): Base64 encoded image
  - `operation` (required): "identify"
- **Returns**: Person name, relationship, confidence score

### 3. **Timer Management Tool** (`manage_timer`)
- **Purpose**: Set and manage timers for time-sensitive events
- **Parameters**:
  - `action` (required): "set"
  - `duration_minutes` (optional): Duration in minutes
- **Returns**: Timer ID, duration, status

### 4. **Location Monitoring Tool** (`monitor_location`)
- **Purpose**: Monitor user location and safety
- **Parameters**:
  - `action` (required): "check_safety"
- **Returns**: Safety status, location info

## Communication Protocol

The server uses **JSON-RPC 2.0** over **stdio** for all communication.

### Request Format
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "recognize_face",
    "arguments": {
      "image_data": "base64_string",
      "operation": "identify"
    }
  }
}
```

### Response Format
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\":true,\"person\":\"John\",\"confidence\":0.95}"
      }
    ]
  }
}
```

## Setup & Installation

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Build TypeScript:**
   ```bash
   npm run build
   ```

3. **Run the server:**
   ```bash
   node dist/index.js
   ```

## Testing

Run the automated test suite to verify server functionality:

```bash
node src/basic.test.js
```

This test simulates the exact communication flow that Modal will use:
- Initializes connection
- Lists available tools
- Tests ping tool
- Tests face recognition tool
- Validates JSON-RPC responses

## Integration with Modal

Modal agents connect to this server as a subprocess:

```python
import subprocess
import json

# Start MCP server
mcp_process = subprocess.Popen(
    ['node', 'dist/index.js'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Send initialization
init_msg = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {"tools": {}},
        "clientInfo": {"name": "modal-agent", "version": "1.0.0"}
    }
}
mcp_process.stdin.write(json.dumps(init_msg) + '\n')
```

## Development Status

- ✅ **MCP Server Foundation**: Complete
- ✅ **Tool Definitions**: Complete  
- ✅ **JSON-RPC Protocol**: Complete
- ✅ **Testing Suite**: Complete
- 🔄 **Face Recognition**: Mock implementation (needs real implementation)
- 🔄 **Timer Management**: Mock implementation (needs real implementation)
- 🔄 **Location Monitoring**: Mock implementation (needs real implementation)

## Next Steps

1. **Implement real face recognition** using Modal's inference engines
2. **Add timer functionality** with device notifications
3. **Integrate location services** for safety monitoring
4. **Add error handling** for edge cases
5. **Performance optimization** for real-time processing

## File Structure

```
mcp-server/
├── src/
│   ├── index.ts          # Main server implementation
│   └── basic.test.js     # Test suite
├── dist/                 # Compiled JavaScript (generated)
├── package.json          # Dependencies and scripts
├── tsconfig.json         # TypeScript configuration
└── README.md            # This file
```

## Error Handling

The server includes comprehensive error handling:
- **Method Not Found**: Unknown tool names
- **Internal Errors**: Tool execution failures
- **Invalid Parameters**: Missing required arguments
- **Graceful Shutdown**: SIGINT/SIGTERM handling

## Contributing

When implementing real tool functionality:
1. Replace mock handlers with actual implementations
2. Update tool descriptions to remove "MOCK" references
3. Add proper error handling for external service calls
4. Test thoroughly with the automated test suite
5. Update this README with new capabilities
