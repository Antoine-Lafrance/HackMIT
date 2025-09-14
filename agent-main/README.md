# Minimalist Anthropic Agent with MCP Tools

A simple, single-file agent that uses the Anthropic API and can decide to use MCP (Model Context Protocol) tools. Designed to run on Modal cloud computing platform.

## Features

- Single Python file implementation
- Anthropic Claude integration
- MCP tool support (optional)
- Designed for Modal cloud execution
- Simple JSON context processing loop
- Structured decision making

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Modal

```bash
# Install Modal CLI
pip install modal

# Authenticate with Modal
modal setup
```

### 3. Configure Secrets

Add your Anthropic API key to Modal secrets:

```bash
modal secret create anthropic-api-key ANTHROPIC_API_KEY=your_api_key_here
```

### 4. Run the Agent

#### Local Testing

```bash
# Set environment variable locally
export ANTHROPIC_API_KEY=your_api_key_here

# Run local test
python agent.py
```

#### Deploy to Modal

```bash
# Deploy and run on Modal
modal run agent.py
```

## How It Works

The agent follows a simple workflow:

1. **Receives JSON context** - Any structured data you want analyzed
2. **Analyzes the context** - Uses Claude to understand the situation
3. **Decides on tools** - Determines if MCP tools would be helpful
4. **Executes tools** - Calls the necessary tools if needed
5. **Returns results** - Provides analysis and tool outputs

## Example Usage

```python
# Example contexts the agent can process
contexts = [
    {
        "type": "camera_frame",
        "timestamp": "2025-01-13T10:30:00Z",
        "objects_detected": ["person", "car", "traffic_light"],
        "question": "Are there any safety concerns?"
    },
    {
        "type": "sensor_data",
        "temperature": 25.5,
        "humidity": 60.2,
        "motion_detected": True,
        "question": "Should I adjust the environment?"
    }
]
```

## Agent Decisions

The agent responds in structured JSON format:

```json
{
    "decision": "use_tools" | "direct_response",
    "reasoning": "Why this decision was made",
    "response": "Direct answer (if no tools needed)",
    "tools_to_use": [...], // If tools are needed
    "tool_results": [...] // Results from tool execution
}
```

## MCP Tools Configuration

To add MCP tools, provide server configurations:

```python
mcp_servers = [
    {
        "name": "filesystem",
        "command": "python",
        "args": ["-m", "mcp_server_filesystem"],
        "env": {}
    }
]
```

## Modal Deployment

The agent is designed to run efficiently on Modal with:

- Automatic dependency management
- Secret handling for API keys
- Cloud-scale execution
- Serverless pricing model

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   JSON Context │───▶│   Agent      │───▶│  Anthropic  │
│                 │    │   (Loop)     │    │    API      │
└─────────────────┘    └──────┬───────┘    └─────────────┘
                              │
                              ▼
                      ┌──────────────┐
                      │  MCP Tools   │
                      │  (Optional)  │
                      └──────────────┘
```

## Customization

- Modify the system prompt in `create_system_prompt()`
- Add your own MCP tools via `mcp_servers` configuration
- Adjust Claude model settings in `AgentConfig`
- Extend context processing in `process_context()`

## License

MIT License
