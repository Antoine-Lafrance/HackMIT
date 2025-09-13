"""Example usage script for the Camera Feed Agent."""

import asyncio
import json
import time
from typing import Dict, Any

# Import our agent components
from agent_core import Agent, AgentConfig, CameraFrame, create_agent
from config import SystemConfig, get_config
from mcp_tools import get_mcp_server


async def demo_single_frame_processing():
    """Demonstrate processing a single camera frame."""
    print("=== Single Frame Processing Demo ===")
    
    # Create a sample frame with SAM segments
    sample_frame_data = {
        'timestamp': time.time(),
        'frame_id': 1,
        'segments': [
            {
                'label': 'person',
                'confidence': 0.95,
                'bbox': [100, 50, 200, 300],
                'mask_id': 'segment_001',
                'area': 30000
            },
            {
                'label': 'car',
                'confidence': 0.87,
                'bbox': [300, 100, 500, 250],
                'mask_id': 'segment_002', 
                'area': 37500
            },
            {
                'label': 'tree',
                'confidence': 0.76,
                'bbox': [50, 0, 150, 400],
                'mask_id': 'segment_003',
                'area': 40000
            }
        ],
        'metadata': {
            'source': 'demo_camera',
            'resolution': [640, 480],
            'fps': 30,
            'sam_model': 'SAM-B',
            'processing_time_ms': 45
        }
    }
    
    # Convert to JSON string (as it would come from camera feed)
    frame_json = json.dumps(sample_frame_data, indent=2)
    print(f"Sample frame data:\n{frame_json}\n")
    
    # Create agent with custom configuration
    config = AgentConfig(
        feed_interval_ms=50,
        enable_logging=True
    )
    
    agent = await create_agent(config)
    
    # Process the frame
    frame = CameraFrame.from_json(frame_json)
    print(f"Processing frame {frame.frame_id} with {len(frame.segments)} segments...")
    
    await agent._process_frame(frame)
    
    # Show statistics
    stats = agent.get_stats()
    print(f"Processing stats: {stats}")
    
    return agent


async def demo_continuous_processing():
    """Demonstrate continuous processing of multiple frames."""
    print("\n=== Continuous Processing Demo ===")
    
    # Configuration for continuous processing
    config = AgentConfig(
        feed_interval_ms=200,  # Process every 200ms
        max_queue_size=50,
        enable_logging=True
    )
    
    agent = Agent(config)
    await agent.initialize()
    
    # Start the agent in background
    agent_task = asyncio.create_task(agent.start())
    
    # Simulate camera feed
    print("Starting continuous feed simulation...")
    
    for i in range(10):  # Simulate 10 frames
        # Generate varied frame data
        num_segments = (i % 4) + 1  # 1-4 segments per frame
        segments = []
        
        for j in range(num_segments):
            segment = {
                'label': ['person', 'car', 'bike', 'tree', 'building'][j % 5],
                'confidence': 0.6 + (j * 0.1) + (i * 0.02),
                'bbox': [
                    50 + j * 60,
                    30 + j * 40,
                    100 + j * 20,
                    150 + j * 30
                ],
                'mask_id': f'segment_{i:03d}_{j:03d}',
                'area': 5000 + j * 1000 + i * 500
            }
            segments.append(segment)
        
        frame_data = {
            'timestamp': time.time(),
            'frame_id': i + 100,
            'segments': segments,
            'metadata': {
                'source': 'continuous_demo',
                'resolution': [640, 480],
                'fps': 30,
                'sam_model': 'SAM-B'
            }
        }
        
        frame_json = json.dumps(frame_data)
        
        # Feed frame to agent
        success = await agent.feed_frame(frame_json)
        print(f"Frame {i + 100}: {'✓' if success else '✗'} ({num_segments} segments)")
        
        # Wait between frames
        await asyncio.sleep(0.3)  # 300ms between feeds
    
    # Let processing finish
    await asyncio.sleep(2.0)
    
    # Stop the agent
    await agent.stop()
    
    # Wait for agent task to complete
    if not agent_task.done():
        agent_task.cancel()
        try:
            await agent_task
        except asyncio.CancelledError:
            pass
    
    # Show final statistics
    stats = agent.get_stats()
    print(f"\nFinal processing stats:")
    print(f"  Frames processed: {stats['frames_processed']}")
    print(f"  Frames dropped: {stats['frames_dropped']}")
    print(f"  Average processing time: {stats.get('avg_processing_time', 0):.3f}s")
    print(f"  Total processing time: {stats['total_processing_time']:.3f}s")
    
    return agent


async def demo_mcp_tools():
    """Demonstrate MCP tools functionality."""
    print("\n=== MCP Tools Demo ===")
    
    # Get the MCP server
    mcp_server = await get_mcp_server()
    
    # List available tools
    tools = mcp_server.list_tools()
    print("Available MCP tools:")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")
    
    # Test camera analysis tool
    print("\nTesting camera analysis tool...")
    analysis_result = await mcp_server.call_tool(
        "analyze_camera_feed",
        {
            'segments': [
                {'label': 'person', 'confidence': 0.95, 'bbox': [10, 20, 100, 200]},
                {'label': 'car', 'confidence': 0.88, 'bbox': [150, 50, 300, 180]}
            ],
            'timestamp': time.time(),
            'frame_id': 999
        }
    )
    
    print(f"Analysis result: {analysis_result.success}")
    if analysis_result.success:
        print(f"Analysis data: {json.dumps(analysis_result.result, indent=2)}")
    
    # Test action decision tool
    if analysis_result.success:
        print("\nTesting action decision tool...")
        action_result = await mcp_server.call_tool(
            "decide_action",
            {
                'analysis': analysis_result.result,
                'frame_id': 999
            }
        )
        
        print(f"Action result: {action_result.success}")
        if action_result.success:
            print(f"Action data: {json.dumps(action_result.result, indent=2)}")


async def demo_configuration():
    """Demonstrate configuration system."""
    print("\n=== Configuration Demo ===")
    
    # Get current configuration
    config = get_config()
    
    print("Current configuration:")
    print(f"  Agent feed interval: {config.agent.feed_interval_ms}ms")
    print(f"  Agent queue size: {config.agent.max_queue_size}")
    print(f"  Camera FPS: {config.camera.expected_fps}")
    print(f"  Modal CPU count: {config.modal.cpu_count}")
    print(f"  Environment: {config.environment}")
    
    # Create custom configuration
    custom_config = SystemConfig()
    custom_config.agent.feed_interval_ms = 50
    custom_config.camera.min_confidence_threshold = 0.8
    custom_config.debug_mode = True
    
    print(f"\nCustom configuration example:")
    print(f"  Feed interval: {custom_config.agent.feed_interval_ms}ms")
    print(f"  Min confidence: {custom_config.camera.min_confidence_threshold}")
    print(f"  Debug mode: {custom_config.debug_mode}")


def create_sample_config_file():
    """Create a sample configuration file."""
    print("\n=== Creating Sample Config File ===")
    
    from config import ConfigManager
    
    config_manager = ConfigManager()
    config_path = config_manager.create_default_config_file("sample_config.json")
    
    print(f"Created sample configuration file: {config_path}")
    
    # Also create a development config
    dev_config = SystemConfig()
    dev_config.environment = "development"
    dev_config.debug_mode = True
    dev_config.agent.feed_interval_ms = 50
    dev_config.agent.enable_logging = True
    
    dev_config_path = config_manager.config_dir / "config.development.json"
    dev_config.save_to_file(dev_config_path)
    
    print(f"Created development configuration file: {dev_config_path}")


async def main():
    """Run all demonstrations."""
    print("🤖 Camera Feed Agent with MCP Tools - Demo")
    print("=" * 50)
    
    try:
        # Configuration demo
        await demo_configuration()
        
        # Create sample config files
        create_sample_config_file()
        
        # MCP tools demo
        await demo_mcp_tools()
        
        # Single frame demo
        await demo_single_frame_processing()
        
        # Continuous processing demo
        await demo_continuous_processing()
        
        print("\n🎉 All demos completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
