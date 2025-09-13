"""
Camera Feed Agent with MCP Tools - Test and Demo Script

This script demonstrates the camera feed agent that processes SAM-segmented 
camera data using MCP (Model Context Protocol) tools with Modal compute.
"""

import modal
import asyncio
import json
import time

app = modal.App("camera-feed-agent-test")

# Modal image with dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install([
    "numpy",
    "Pillow", 
    "pydantic"
])

# Mount local code
mount = modal.Mount.from_local_dir(".", remote_path="/agent")


@app.function(image=image, mounts=[mount])
def test_agent_setup():
    """Test that the agent components are properly set up."""
    import sys
    sys.path.append('/agent')
    
    try:
        # Import all modules to check they work
        from agent_core import Agent, AgentConfig, CameraFrame
        from mcp_tools import SimpleMCPServer, get_mcp_server
        from config import SystemConfig, get_config
        
        # Test basic configuration
        config = AgentConfig(feed_interval_ms=100, enable_logging=False)
        
        # Test frame creation
        frame_data = {
            'timestamp': time.time(),
            'frame_id': 1,
            'segments': [
                {
                    'label': 'test_object',
                    'confidence': 0.9,
                    'bbox': [10, 10, 50, 50]
                }
            ],
            'metadata': {'source': 'test'}
        }
        
        frame = CameraFrame(**frame_data)
        
        return {
            'success': True,
            'message': 'All agent components loaded successfully',
            'test_frame_id': frame.frame_id,
            'config_interval': config.feed_interval_ms
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to load agent components'
        }


@app.function(image=image, mounts=[mount], timeout=60)
async def test_mcp_tools():
    """Test MCP tools functionality."""
    import sys
    sys.path.append('/agent')
    
    try:
        from mcp_tools import get_mcp_server
        
        # Get MCP server
        server = await get_mcp_server()
        
        # List tools
        tools = server.list_tools()
        
        # Test camera analysis tool
        test_segments = [
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
        ]
        
        analysis_result = await server.call_tool(
            "analyze_camera_feed",
            {
                'segments': test_segments,
                'timestamp': time.time(),
                'frame_id': 123
            }
        )
        
        action_result = None
        if analysis_result.success:
            action_result = await server.call_tool(
                "decide_action",
                {
                    'analysis': analysis_result.result,
                    'frame_id': 123
                }
            )
        
        return {
            'success': True,
            'tools_available': len(tools),
            'tool_names': [t['name'] for t in tools],
            'analysis_success': analysis_result.success,
            'action_success': action_result.success if action_result else False,
            'analysis_result': analysis_result.result if analysis_result.success else None,
            'action_result': action_result.result if action_result and action_result.success else None
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@app.function(image=image, mounts=[mount], timeout=120)  
async def test_agent_processing():
    """Test full agent processing pipeline."""
    import sys
    sys.path.append('/agent')
    
    try:
        from agent_core import Agent, AgentConfig
        
        # Create agent
        config = AgentConfig(
            feed_interval_ms=100,
            max_queue_size=10,
            enable_logging=False
        )
        
        agent = Agent(config)
        await agent.initialize()
        
        # Create test frames
        test_frames = []
        for i in range(5):
            frame_data = {
                'timestamp': time.time() + i * 0.1,
                'frame_id': i,
                'segments': [
                    {
                        'label': ['person', 'car', 'tree', 'building'][i % 4],
                        'confidence': 0.7 + i * 0.05,
                        'bbox': [i * 10, i * 10, 100 + i * 10, 100 + i * 10]
                    }
                    for _ in range((i % 3) + 1)  # Variable number of segments
                ],
                'metadata': {
                    'source': 'test_camera',
                    'resolution': [640, 480]
                }
            }
            test_frames.append(json.dumps(frame_data))
        
        # Process frames
        processed_count = 0
        for frame_json in test_frames:
            success = await agent.feed_frame(frame_json)
            if success:
                processed_count += 1
        
        # Give time for processing
        await asyncio.sleep(1.0)
        
        # Get stats
        stats = agent.get_stats()
        
        return {
            'success': True,
            'frames_fed': len(test_frames),
            'frames_queued': processed_count,
            'stats': stats
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@app.local_entrypoint()
def main():
    """Main test function."""
    print("🧪 Testing Camera Feed Agent with MCP Tools")
    print("=" * 50)
    
    # Test 1: Basic setup
    print("\n1. Testing agent setup...")
    setup_result = test_agent_setup.remote()
    print(f"Setup result: {setup_result}")
    
    if not setup_result.get('success'):
        print("❌ Setup failed, stopping tests")
        return
    
    # Test 2: MCP tools
    print("\n2. Testing MCP tools...")
    mcp_result = test_mcp_tools.remote()
    print(f"MCP tools result: {mcp_result}")
    
    # Test 3: Full agent processing
    print("\n3. Testing agent processing...")
    processing_result = test_agent_processing.remote()
    print(f"Processing result: {processing_result}")
    
    # Summary
    print("\n" + "=" * 50)
    print("🎯 Test Summary:")
    print(f"  Setup: {'✅' if setup_result.get('success') else '❌'}")
    print(f"  MCP Tools: {'✅' if mcp_result.get('success') else '❌'}")
    print(f"  Processing: {'✅' if processing_result.get('success') else '❌'}")
    
    if all([
        setup_result.get('success'),
        mcp_result.get('success'), 
        processing_result.get('success')
    ]):
        print("\n🎉 All tests passed! Agent is ready for use.")
        
        if mcp_result.get('success'):
            print(f"\nAvailable MCP tools: {mcp_result.get('tool_names', [])}")
        
        if processing_result.get('success'):
            stats = processing_result.get('stats', {})
            print(f"Processing stats: {stats.get('frames_processed', 0)} frames processed")
    else:
        print("\n❌ Some tests failed. Check the logs above.")


if __name__ == "__main__":
    main()
