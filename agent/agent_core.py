"""Main Agent class for processing camera feeds with MCP tools."""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
import numpy as np

from mcp_tools import SimpleMCPServer, get_mcp_server, MCPToolResult
from prompt_config import get_prompt_manager, PromptManager
from anthropic_client import AnthropicClient, get_anthropic_client, AnthropicConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CameraFrame:
    """Represents a single camera frame with segmentation data."""
    timestamp: float
    frame_id: int
    segments: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    
    # Conversation context (speech-to-text input)
    conversation_text: Optional[str] = None
    conversation_timestamp: Optional[float] = None
    conversation_speaker: Optional[str] = None
    conversation_confidence: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_json(cls, data: str) -> 'CameraFrame':
        """Create from JSON string."""
        json_data = json.loads(data)
        return cls(**json_data)
    
    def has_conversation(self) -> bool:
        """Check if frame has conversation data."""
        return self.conversation_text is not None and len(self.conversation_text.strip()) > 0


@dataclass 
class AgentConfig:
    """Configuration for the agent."""
    feed_interval_ms: int = 100  # Process feed every 100ms
    max_queue_size: int = 1000   # Maximum frames to queue
    processing_timeout: float = 5.0  # Timeout for processing in seconds
    enable_logging: bool = True
    
    # Anthropic integration
    use_anthropic: bool = False  # Set to True to use Anthropic for analysis
    anthropic_config: Optional[AnthropicConfig] = None
    
    # Prompt configuration
    scenario: Optional[str] = None  # Scenario for context-specific prompts
    
    def __post_init__(self):
        """Validate configuration."""
        if self.feed_interval_ms <= 0:
            raise ValueError("feed_interval_ms must be positive")
        if self.max_queue_size <= 0:
            raise ValueError("max_queue_size must be positive")


class Agent:
    """Main agent class that processes camera feeds using MCP tools."""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.mcp_server: Optional[SimpleMCPServer] = None
        self.prompt_manager: Optional[PromptManager] = None
        self.anthropic_client: Optional[AnthropicClient] = None
        self.frame_queue: asyncio.Queue = asyncio.Queue(maxsize=config.max_queue_size)
        self.is_running = False
        self.stats = {
            'frames_processed': 0,
            'frames_dropped': 0,
            'total_processing_time': 0.0,
            'last_frame_time': None,
            'anthropic_calls': 0,
            'mcp_calls': 0
        }
        
        if config.enable_logging:
            logging.basicConfig(level=logging.INFO)
    
    async def initialize(self):
        """Initialize the agent."""
        logger.info("Initializing agent...")
        
        # Initialize prompt manager
        self.prompt_manager = get_prompt_manager()
        
        # Create prompt files if they don't exist
        prompt_files = self.prompt_manager.create_prompt_files()
        logger.info(f"Prompt files available at: {prompt_files}")
        
        # Initialize Anthropic client if configured
        if self.config.use_anthropic:
            try:
                if self.config.anthropic_config:
                    self.anthropic_client = AnthropicClient(self.config.anthropic_config)
                else:
                    self.anthropic_client = await get_anthropic_client()
                logger.info("Anthropic client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                logger.info("Falling back to MCP tools only")
                self.config.use_anthropic = False
        
        # Get MCP server
        self.mcp_server = await get_mcp_server()
        
        # Log available tools
        tools = self.mcp_server.list_tools()
        logger.info(f"Available MCP tools: {[tool['name'] for tool in tools]}")
        
        # Log prompt configuration
        if self.prompt_manager:
            system_prompt = self.prompt_manager.get_system_prompt(self.config.scenario)
            logger.info(f"System prompt loaded (length: {len(system_prompt)} chars)")
            if self.config.scenario:
                logger.info(f"Using scenario: {self.config.scenario}")
        
        logger.info("Agent initialized successfully")
    
    async def start(self):
        """Start the agent."""
        if not self.mcp_server:
            await self.initialize()
        
        self.is_running = True
        logger.info("Agent started")
        
        # Start processing loop
        processing_task = asyncio.create_task(self._processing_loop())
        
        try:
            await processing_task
        except asyncio.CancelledError:
            logger.info("Agent processing cancelled")
        finally:
            self.is_running = False
    
    async def stop(self):
        """Stop the agent."""
        self.is_running = False
        logger.info("Agent stopped")
    
    async def feed_frame(self, frame_data: str) -> bool:
        """
        Feed a camera frame to the agent.
        
        Args:
            frame_data: JSON string representing the camera frame with segments
            
        Returns:
            bool: True if frame was queued successfully, False if dropped
        """
        try:
            frame = CameraFrame.from_json(frame_data)
            
            # Try to add to queue
            try:
                self.frame_queue.put_nowait(frame)
                return True
            except asyncio.QueueFull:
                self.stats['frames_dropped'] += 1
                logger.warning(f"Frame queue full, dropped frame {frame.frame_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing frame data: {e}")
            return False
    
    async def _processing_loop(self):
        """Main processing loop."""
        logger.info("Starting processing loop")
        
        while self.is_running:
            try:
                # Wait for frame with timeout based on feed interval
                timeout = self.config.feed_interval_ms / 1000.0
                frame = await asyncio.wait_for(self.frame_queue.get(), timeout=timeout)
                
                # Process the frame
                await self._process_frame(frame)
                
            except asyncio.TimeoutError:
                # No frame received in timeout period - this is normal
                continue
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                await asyncio.sleep(0.1)  # Brief pause before retrying
    
    async def _process_frame(self, frame: CameraFrame):
        """Process a single frame."""
        start_time = time.time()
        
        try:
            logger.debug(f"Processing frame {frame.frame_id} with {len(frame.segments)} segments")
            
            # Ensure MCP server is available
            if not self.mcp_server:
                logger.error("MCP server not initialized")
                return
            
            analysis = None
            action = None
            
            # Choose processing method based on configuration
            if self.config.use_anthropic and self.anthropic_client and self.prompt_manager:
                # Use Anthropic for intelligent analysis
                analysis, action = await self._process_with_anthropic(frame)
            else:
                # Use MCP tools for analysis
                analysis, action = await self._process_with_mcp(frame)
            
            if analysis and action:
                # Step 3: Execute or log the action
                await self._execute_action(action, frame, analysis)
            
            # Update stats
            processing_time = time.time() - start_time
            self.stats['frames_processed'] += 1
            self.stats['total_processing_time'] += processing_time
            self.stats['last_frame_time'] = frame.timestamp
            
            logger.debug(f"Frame {frame.frame_id} processed in {processing_time:.3f}s")
            
        except Exception as e:
            logger.error(f"Error processing frame {frame.frame_id}: {e}")
    
    async def _process_with_anthropic(self, frame: CameraFrame) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Process frame using Anthropic AI."""
        try:
            if not self.anthropic_client or not self.prompt_manager:
                return None, None
            
            # Get prompts
            system_prompt = self.prompt_manager.get_system_prompt(self.config.scenario)
            user_prompt_template = self.prompt_manager.get_prompt_config().user_prompt_template
            
            # Analyze with Anthropic
            analysis_response = await self.anthropic_client.analyze_camera_frame(
                frame_data=frame.to_dict(),
                system_prompt=system_prompt,
                user_prompt_template=user_prompt_template
            )
            
            self.stats['anthropic_calls'] += 1
            
            if not analysis_response['success']:
                logger.error(f"Anthropic analysis failed: {analysis_response.get('error')}")
                return None, None
            
            analysis = analysis_response['analysis']
            if analysis is None:
                logger.error("Anthropic analysis result is None")
                return None, None
                
            logger.debug(f"Anthropic analysis complete: {analysis.get('scene_description', 'N/A')[:100]}...")
            
            # Make decision with Anthropic
            decision_response = await self.anthropic_client.make_decision(
                analysis=analysis,
                system_prompt=system_prompt,
                decision_context=self.prompt_manager.get_tool_context_prompt()
            )
            
            if not decision_response['success']:
                logger.error(f"Anthropic decision failed: {decision_response.get('error')}")
                return analysis, None
            
            action = decision_response['decision']
            if action is None:
                logger.error("Anthropic decision result is None")
                return analysis, None
            
            return analysis, action
            
        except Exception as e:
            logger.error(f"Error in Anthropic processing: {e}")
            return None, None
    
    async def _process_with_mcp(self, frame: CameraFrame) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Process frame using MCP tools."""
        try:
            if not self.mcp_server:
                logger.error("MCP server not initialized")
                return None, None
            
            # Step 1: Analyze the camera feed with conversation context
            analysis_args = {
                'segments': frame.segments,
                'timestamp': frame.timestamp,
                'frame_id': frame.frame_id
            }
            
            # Add conversation data if available
            if frame.has_conversation():
                analysis_args.update({
                    'conversation_text': frame.conversation_text,
                    'conversation_timestamp': frame.conversation_timestamp,
                    'conversation_speaker': frame.conversation_speaker,
                    'conversation_confidence': frame.conversation_confidence
                })
                conv_preview = frame.conversation_text[:50] + "..." if frame.conversation_text and len(frame.conversation_text) > 50 else frame.conversation_text
                logger.debug(f"Including conversation context: '{conv_preview}' from {frame.conversation_speaker}")
            
            analysis_result = await self.mcp_server.call_tool("analyze_camera_feed", analysis_args)
            
            self.stats['mcp_calls'] += 1
            
            if not analysis_result.success:
                logger.error(f"Analysis failed: {analysis_result.error}")
                return None, None
            
            analysis = analysis_result.result
            if analysis is None:
                logger.error("Analysis result is None")
                return None, None
                
            # Log analysis with conversation status
            scene_desc = analysis.get('scene_description', 'N/A')[:100]
            conv_status = "with conversation" if frame.has_conversation() else "no conversation"
            logger.debug(f"Analysis complete ({conv_status}): {scene_desc}...")
            
            # Step 2: Decide action based on analysis (already includes conversation context)
            action_result = await self.mcp_server.call_tool(
                "decide_action",
                {
                    'analysis': analysis,
                    'frame_id': frame.frame_id
                }
            )
            
            self.stats['mcp_calls'] += 1
            
            if not action_result.success:
                logger.error(f"Action decision failed: {action_result.error}")
                return analysis, None
            
            action = action_result.result
            if action is None:
                logger.error("Action result is None")
                return analysis, None
            
            return analysis, action
            
        except Exception as e:
            logger.error(f"Error in MCP processing: {e}")
            return None, None
    
    async def _execute_action(self, action: Dict[str, Any], frame: CameraFrame, analysis: Dict[str, Any]):
        """Execute the decided action."""
        action_type = action.get('type', 'unknown')
        reason = action.get('reason', 'No reason provided')
        
        logger.info(f"Action for frame {frame.frame_id}: {action_type} - {reason}")
        
        # Here you would implement actual actions based on the type
        if action_type == 'alert':
            await self._handle_alert(action, frame, analysis)
        elif action_type == 'monitor':
            await self._handle_monitor(action, frame, analysis)
        elif action_type == 'wait':
            await self._handle_wait(action, frame, analysis)
        else:
            logger.warning(f"Unknown action type: {action_type}")
    
    async def _handle_alert(self, action: Dict[str, Any], frame: CameraFrame, analysis: Dict[str, Any]):
        """Handle alert action."""
        logger.warning(f"ALERT: {action.get('reason')} - Object count: {action.get('count', 0)}")
        # In a real implementation, you might send notifications, save images, etc.
    
    async def _handle_monitor(self, action: Dict[str, Any], frame: CameraFrame, analysis: Dict[str, Any]):
        """Handle monitor action."""
        objects = action.get('objects', [])
        logger.info(f"Monitoring objects: {', '.join(objects) if objects else 'none'}")
    
    async def _handle_wait(self, action: Dict[str, Any], frame: CameraFrame, analysis: Dict[str, Any]):
        """Handle wait action."""
        logger.debug(f"Waiting - {action.get('reason')}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        stats = self.stats.copy()
        if stats['frames_processed'] > 0:
            stats['avg_processing_time'] = stats['total_processing_time'] / stats['frames_processed']
        else:
            stats['avg_processing_time'] = 0.0
        
        return stats
    
    async def register_custom_tool(self, tool):
        """Register a custom MCP tool."""
        if self.mcp_server:
            self.mcp_server.register_tool(tool)
        else:
            logger.warning("MCP server not initialized, cannot register tool")


# Utility function to create agent with default config
async def create_agent(config: Optional[AgentConfig] = None) -> Agent:
    """Create and initialize an agent."""
    if config is None:
        config = AgentConfig()
    
    agent = Agent(config)
    await agent.initialize()
    return agent
