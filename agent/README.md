# Camera Feed Agent with MCP Tools & Anthropic AI

A sophisticated agent system that processes camera feeds (pre-segmented through SAM) using Model Context Protocol (MCP) tools and Anthropic AI for intelligent analysis, deployed on Modal compute infrastructure.

## Overview

This system provides:
- **Real-time camera feed processing** with configurable intervals
- **MCP tool integration** for extensible functionality
- **Anthropic AI integration** for intelligent analysis and decision making
- **Customizable prompt system** for different scenarios
- **Modal compute deployment** for scalable processing
- **SAM segmentation support** for object detection and analysis
- **Configurable hyperparameters** for optimal performance

## Quick Start

### 1. Setup Environment

```bash
cd agent
cp .env.example .env  # Edit with your Anthropic API key
pipenv install
pipenv shell
```

### 2. Configure Your API Key

Edit `.env` file:
```bash
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 3. Customize Your Agent Prompt

The default prompt is located in `prompts/system_prompt.txt`. Edit this file to define:
- Your agent's objectives and behavior
- Available MCP tools descriptions
- Specific instructions for your use case

### 4. Run Demo

```bash
python demo.py
```

## Architecture

```
Camera Feed (JSON) → Agent → [Anthropic AI | MCP Tools] → Actions
                        ↓
                   Modal Compute
```

### Processing Modes

1. **Anthropic AI Mode**: Uses Claude for intelligent analysis
2. **MCP Tools Mode**: Uses built-in MCP tools for analysis
3. **Hybrid Mode**: Combines both approaches

### Components

1. **Agent Core** (`agent_core.py`) - Main processing engine
2. **MCP Tools** (`mcp_tools.py`) - Tool definitions and execution
3. **Anthropic Client** (`anthropic_client.py`) - AI integration
4. **Prompt System** (`prompt_config.py`) - Customizable prompts
5. **Configuration** (`config.py`) - System configuration management  
6. **Modal Deployment** (`modal_agent.py`) - Cloud compute functions
7. **Demo Script** (`demo.py`) - Usage examples and testing

## Installation

### Prerequisites
- Python 3.11+
- Modal account and CLI setup
- Pipenv (recommended)

### Setup

1. **Install dependencies:**
```bash
cd agent
pipenv install
pipenv shell
```

2. **Install Modal CLI:**
```bash
pip install modal
modal token new
```

3. **Deploy to Modal:**
```bash
modal deploy modal_agent.py
```

## Usage

## Customizing Your Agent

### Default Prompt

Your agent's behavior is controlled by the system prompt in `prompts/system_prompt.txt`. This file starts with:

```
add default prompt here
```

Edit this file to:
- Define your agent's role and objectives
- Describe available MCP tools
- Set specific instructions for your use case
- Configure response formats and priorities

### Environment Configuration

Key environment variables in `.env`:

```bash
# Anthropic AI
ANTHROPIC_API_KEY=your_api_key_here
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# Agent Behavior
AGENT_FEED_INTERVAL_MS=100  # Process every 100ms
AGENT_MAX_QUEUE_SIZE=1000   # Queue up to 1000 frames

# Processing Mode
USE_ANTHROPIC=true          # Enable AI analysis
DEFAULT_SCENARIO=security   # Use security scenario
```

### Scenario-Specific Prompts

Create custom scenarios in `prompts/scenarios/`:
- `security.txt` - Security monitoring
- `traffic.txt` - Traffic analysis  
- `retail.txt` - Retail monitoring
- `general.txt` - General purpose

## Usage Examples

### With Anthropic AI

```python
import asyncio
from agent_core import create_agent, AgentConfig
from anthropic_client import AnthropicConfig

# Configure for AI analysis
config = AgentConfig(
    feed_interval_ms=100,
    use_anthropic=True,
    scenario="security"  # Use security-focused prompts
)

agent = await create_agent(config)
```

### MCP Tools Only

```python
config = AgentConfig(
    feed_interval_ms=100,
    use_anthropic=False  # Use MCP tools only
)

agent = await create_agent(config)
```

### Camera Feed Format

The agent expects JSON-formatted camera frames with SAM segmentation:

```json
{
  "timestamp": 1234567890.123,
  "frame_id": 1,
  "segments": [
    {
      "label": "person",
      "confidence": 0.95,
      "bbox": [100, 50, 200, 300],
      "mask_id": "segment_001",
      "area": 30000
    }
  ],
  "metadata": {
    "source": "camera_1",
    "resolution": [640, 480],
    "fps": 30,
    "sam_model": "SAM-B"
  }
}
```

### Configuration

Configure the agent through environment variables or config files:

```python
from config import SystemConfig, AgentRuntimeConfig

config = SystemConfig(
    agent=AgentRuntimeConfig(
        feed_interval_ms=100,  # Process every 100ms
        max_queue_size=1000,   # Queue up to 1000 frames
        processing_timeout=5.0 # Timeout after 5 seconds
    )
)
```

## MCP Tools

The system includes built-in MCP tools:

### Camera Analysis Tool
- **Name:** `analyze_camera_feed`  
- **Purpose:** Analyze SAM segments and extract insights
- **Input:** Frame segments, timestamp, frame ID
- **Output:** Object count, scene description, detected objects

### Action Decision Tool
- **Name:** `decide_action`
- **Purpose:** Decide actions based on analysis
- **Input:** Analysis results, frame ID
- **Output:** Action type (alert, monitor, wait) and reasoning

### Custom Tools

Add custom MCP tools by extending `SimpleMCPTool`:

```python
from mcp_tools import SimpleMCPTool, MCPToolResult

class CustomTool(SimpleMCPTool):
    def __init__(self):
        super().__init__("custom_tool", "Custom tool description")
    
    async def execute(self, arguments):
        # Your tool logic here
        return MCPToolResult(success=True, result={"status": "processed"})

# Register the tool
mcp_server.register_tool(CustomTool())
```

## Modal Deployment

### Functions Available

1. **`process_camera_frame`** - Process single frame
2. **`run_agent_continuous`** - Continuous processing
3. **`get_available_tools`** - List MCP tools
4. **`validate_frame_data`** - Validate frame format

### Example Modal Usage

```python
import modal

# Process a single frame
result = modal.Function.lookup("camera-feed-agent", "process_camera_frame").remote(frame_json)

# Run continuous processing
continuous_result = modal.Function.lookup("camera-feed-agent", "run_agent_continuous").remote(
    feed_interval_ms=200,
    max_frames=100
)
```

## Configuration Options

### Agent Configuration
- `feed_interval_ms`: Processing interval (default: 100)
- `max_queue_size`: Maximum queued frames (default: 1000)
- `processing_timeout`: Processing timeout seconds (default: 5.0)
- `enable_logging`: Enable logging (default: True)

### Camera Configuration  
- `expected_fps`: Expected camera FPS (default: 30)
- `min_confidence_threshold`: Minimum confidence for segments (default: 0.5)
- `max_segments_per_frame`: Maximum segments per frame (default: 100)

### Modal Configuration
- `cpu_count`: CPU cores per function (default: 2)
- `memory_mb`: Memory allocation MB (default: 2048)
- `timeout_seconds`: Function timeout (default: 300)

## Environment Variables

Override configuration with environment variables:

```bash
export AGENT_FEED_INTERVAL_MS=50
export AGENT_MAX_QUEUE_SIZE=2000
export CAMERA_MIN_CONFIDENCE=0.8
export MODAL_CPU_COUNT=4
export MODAL_MEMORY_MB=4096
```

## Running Tests

### Local Testing
```bash
python demo.py
```

### Modal Testing
```bash
modal run test.py
```

## Performance Considerations

### Optimal Settings
- **High frequency:** `feed_interval_ms=50` (20 FPS processing)
- **Standard:** `feed_interval_ms=100` (10 FPS processing)  
- **Low frequency:** `feed_interval_ms=200` (5 FPS processing)

### Memory Usage
- Each frame uses ~1-10KB depending on segment count
- Queue size directly affects memory usage
- Modal functions have configurable memory limits

### Scaling
- Modal automatically scales based on demand
- Configure `max_concurrent` for parallel processing
- Use `scale_down_delay` to control resource cleanup

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure Modal CLI is properly installed
2. **Queue Full**: Increase `max_queue_size` or reduce `feed_interval_ms`
3. **Processing Slow**: Increase Modal CPU/memory allocation
4. **Tool Failures**: Check MCP tool arguments and implementation

### Debugging

Enable debug logging:
```python
config = AgentConfig(enable_logging=True, log_level="DEBUG")
```

Check agent statistics:
```python
stats = agent.get_stats()
print(f"Processed: {stats['frames_processed']}")
print(f"Dropped: {stats['frames_dropped']}")
print(f"Avg time: {stats.get('avg_processing_time', 0):.3f}s")
```

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality  
4. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section
- Review the demo script for examples
- Open an issue on GitHub
