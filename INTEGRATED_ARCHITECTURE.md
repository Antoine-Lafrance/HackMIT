# Integrated Face Recognition Architecture

## Overview
The face recognition system is now fully integrated into the MCP server, providing a clean interface for agent-based face recognition.

## Architecture

```
Agent (Camera Monitoring) 
    ↓ (image + optional name/relationship)
MCP Server (mcp-server/src/index.ts)
    ↓ (HTTP call to /search-person)
Python Face Service (python-face-service/face_service.py)
    ↓ (face detection + database search/add)
In-Memory Database (Python service)
```

## Components

### 1. MCP Server (`mcp-server/`)
- **Tool**: `recognize_face`
- **Parameters**: 
  - `image_data` (required): Base64 encoded image
  - `person_name` (optional): Name for new person creation
  - `person_relationship` (optional): Relationship for new person creation
- **Function**: Calls Python service `/search-person` endpoint

### 2. Python Face Service (`python-face-service/`)
- **Endpoint**: `POST /search-person`
- **Function**: 
  - Detects faces in image
  - Searches existing database for matches
  - If no match and name/relationship provided, adds new person
  - Returns recognition result

### 3. Agent Integration
Your teammate's agent should call the MCP server tool:

```python
# Example agent code
import requests

# Call MCP server recognize_face tool
response = requests.post('http://localhost:3000/mcp/tools/recognize_face', json={
    'image_data': base64_image,
    'person_name': 'John Doe',  # optional
    'person_relationship': 'Friend'  # optional
})
```

## Usage Flow

1. **Agent detects face** in camera feed
2. **Agent calls MCP server** with image + optional name/relationship
3. **MCP server calls Python service** `/search-person` endpoint
4. **Python service**:
   - Detects faces using OpenCV
   - Searches in-memory database for matches
   - If no match and name provided, adds new person
   - Returns result
5. **MCP server returns** result to agent
6. **Agent can update Supabase** with recognition results

## Benefits

- ✅ **Clean separation**: MCP server handles tool interface, Python service handles face detection
- ✅ **Agent-friendly**: Simple tool interface for your teammate
- ✅ **Scalable**: Python service can be deployed separately
- ✅ **No frontend complexity**: Pure backend integration
- ✅ **Database flexibility**: Can easily switch from in-memory to Supabase

## Next Steps

1. **Test the integration** by calling the MCP server tool
2. **Your teammate implements** agent that calls MCP server
3. **Optional**: Add Supabase integration to Python service for persistence
