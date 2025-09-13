"""Modal deployment for the Camera Feed Agent with MCP tools."""

import modal
import asyncio
import json
import logging
from typing import Dict, Any, Optional

# Create Modal app
app = modal.App("camera-feed-agent")

# Define the Modal image with required dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install([
    "numpy",
    "Pillow",
    "pydantic",
    "httpx",
    "python-dotenv"
])

# Mount the agent code
mount = modal.Mount.from_local_dir(
    ".",
    remote_path="/agent",
    condition=lambda path: path.suffix in [".py"]
)


@app.function(
    image=image,
    mounts=[mount],
    cpu=2,
    memory=2048,
    timeout=300
)
async def process_camera_frame(frame_data: str, config_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Process a single camera frame using the agent.
    
    Args:
        frame_data: JSON string containing the camera frame with SAM segments
        config_data: Optional configuration dictionary
        
    Returns:
        Dictionary containing processing results and statistics
    """
    import sys
    sys.path.append('/agent')
    
    from agent_core import Agent, AgentConfig, CameraFrame
    
    try:
        # Create config
        if config_data:
            config = AgentConfig(**config_data)
        else:
            config = AgentConfig()
        
        # Create agent
        agent = Agent(config)
        await agent.initialize()
        
        # Parse frame data
        frame = CameraFrame.from_json(frame_data)
        
        # Process frame directly (bypass queue for single frame processing)
        await agent._process_frame(frame)
        
        # Return stats and results
        return {
            'success': True,
            'frame_id': frame.frame_id,
            'timestamp': frame.timestamp,
            'segments_processed': len(frame.segments),
            'stats': agent.get_stats()
        }
        
    except Exception as e:
        logging.error(f"Error processing frame: {e}")
        return {
            'success': False,
            'error': str(e),
            'frame_id': None,
            'timestamp': None,
            'segments_processed': 0
        }


@app.function(
    image=image,
    mounts=[mount],
    cpu=2,
    memory=2048,
    timeout=600,  # Longer timeout for continuous processing
    allow_concurrent_inputs=1
)
async def run_agent_continuous(
    feed_interval_ms: int = 100,
    max_frames: int = 1000,
    config_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run the agent in continuous mode for processing multiple frames.
    
    Args:
        feed_interval_ms: Interval between frame processing in milliseconds
        max_frames: Maximum number of frames to process before stopping
        config_data: Optional configuration dictionary
        
    Returns:
        Dictionary containing final statistics and results
    """
    import sys
    sys.path.append('/agent')
    
    from agent_core import Agent, AgentConfig
    
    try:
        # Create config
        if config_data:
            config_data['feed_interval_ms'] = feed_interval_ms
            config = AgentConfig(**config_data)
        else:
            config = AgentConfig(feed_interval_ms=feed_interval_ms)
        
        # Create and start agent
        agent = Agent(config)
        await agent.initialize()
        
        # Start agent processing (this will run the processing loop)
        # In a real scenario, you'd feed frames to the agent externally
        # For this demo, we'll simulate some frames
        
        frames_processed = 0
        start_time = asyncio.get_event_loop().time()
        
        # Start the agent
        agent_task = asyncio.create_task(agent.start())
        
        # Simulate feeding frames (in real use, this would come from camera feed)
        async def simulate_frames():
            nonlocal frames_processed
            for i in range(max_frames):
                if not agent.is_running:
                    break
                    
                # Create mock frame data
                mock_frame = {
                    'timestamp': asyncio.get_event_loop().time(),
                    'frame_id': i,
                    'segments': [
                        {
                            'label': 'person' if i % 3 == 0 else 'object',
                            'confidence': 0.8 + (i % 10) * 0.02,
                            'bbox': [10 + i % 50, 20 + i % 30, 100, 100]
                        }
                        for _ in range(i % 5 + 1)  # Variable number of segments
                    ],
                    'metadata': {'source': 'mock_camera', 'resolution': [640, 480]}
                }
                
                frame_json = json.dumps(mock_frame)
                success = await agent.feed_frame(frame_json)
                
                if success:
                    frames_processed += 1
                
                # Wait for feed interval
                await asyncio.sleep(feed_interval_ms / 1000.0)
        
        # Run simulation
        simulation_task = asyncio.create_task(simulate_frames())
        
        # Wait for either the agent to finish or simulation to complete
        try:
            await asyncio.wait_for(simulation_task, timeout=max_frames * feed_interval_ms / 1000.0 + 10)
        except asyncio.TimeoutError:
            logging.warning("Simulation timed out")
        
        # Stop the agent
        await agent.stop()
        
        # Cancel agent task if still running
        if not agent_task.done():
            agent_task.cancel()
            try:
                await agent_task
            except asyncio.CancelledError:
                pass
        
        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time
        
        # Return final statistics
        stats = agent.get_stats()
        stats.update({
            'total_runtime': total_time,
            'frames_fed': frames_processed,
            'fps': frames_processed / total_time if total_time > 0 else 0
        })
        
        return {
            'success': True,
            'stats': stats,
            'config': {
                'feed_interval_ms': feed_interval_ms,
                'max_frames': max_frames
            }
        }
        
    except Exception as e:
        logging.error(f"Error in continuous processing: {e}")
        return {
            'success': False,
            'error': str(e),
            'stats': {}
        }


@app.function(
    image=image,
    mounts=[mount]
)
def get_available_tools() -> Dict[str, Any]:
    """Get list of available MCP tools."""
    import sys
    sys.path.append('/agent')
    
    try:
        from mcp_tools import mcp_server
        tools = mcp_server.list_tools()
        
        return {
            'success': True,
            'tools': tools,
            'count': len(tools)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'tools': []
        }


@app.function(
    image=image,
    mounts=[mount]
)
def validate_frame_data(frame_data: str) -> Dict[str, Any]:
    """Validate camera frame data format."""
    import sys
    sys.path.append('/agent')
    
    try:
        from agent_core import CameraFrame
        
        # Try to parse the frame
        frame = CameraFrame.from_json(frame_data)
        
        return {
            'success': True,
            'valid': True,
            'frame_id': frame.frame_id,
            'timestamp': frame.timestamp,
            'segments_count': len(frame.segments),
            'has_metadata': bool(frame.metadata)
        }
        
    except Exception as e:
        return {
            'success': True,
            'valid': False,
            'error': str(e),
            'frame_id': None,
            'timestamp': None,
            'segments_count': 0
        }


# Local entrypoint for testing
@app.local_entrypoint()
def main():
    """Local entrypoint for testing the agent."""
    import json
    
    # Test frame data
    test_frame = {
        'timestamp': 1234567890.123,
        'frame_id': 1,
        'segments': [
            {
                'label': 'person',
                'confidence': 0.95,
                'bbox': [100, 50, 200, 300]
            },
            {
                'label': 'car',
                'confidence': 0.87,
                'bbox': [300, 100, 500, 250]
            }
        ],
        'metadata': {
            'source': 'test_camera',
            'resolution': [640, 480],
            'fps': 30
        }
    }
    
    frame_json = json.dumps(test_frame)
    
    print("Testing agent with sample frame...")
    print(f"Frame data: {frame_json}")
    
    # Test single frame processing
    result = process_camera_frame.remote(frame_json)
    print(f"Single frame result: {result}")
    
    # Test tool listing
    tools_result = get_available_tools.remote()
    print(f"Available tools: {tools_result}")
    
    # Test frame validation
    validation_result = validate_frame_data.remote(frame_json)
    print(f"Frame validation: {validation_result}")
    
    print("All tests completed!")


if __name__ == "__main__":
    main()
