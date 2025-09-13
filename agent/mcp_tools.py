"""Basic MCP tool example for the agent."""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class MCPToolResult:
    """Result from MCP tool execution."""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None


class SimpleMCPTool:
    """Base class for MCP tools."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    async def execute(self, arguments: Dict[str, Any]) -> MCPToolResult:
        """Execute the tool with given arguments."""
        raise NotImplementedError


class CameraAnalysisTool(SimpleMCPTool):
    """Tool for analyzing camera feed data."""
    
    def __init__(self):
        super().__init__(
            name="analyze_camera_feed",
            description="Analyze segmented camera feed data and extract insights, considering conversation context"
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> MCPToolResult:
        """Analyze the camera feed data."""
        try:
            segments = arguments.get('segments', [])
            timestamp = arguments.get('timestamp')
            conversation_text = arguments.get('conversation_text')
            conversation_speaker = arguments.get('conversation_speaker')
            
            # Basic visual analysis
            visual_analysis = {
                'object_count': len(segments),
                'objects_detected': [
                    {
                        'id': i,
                        'type': segment.get('label', 'unknown'),
                        'confidence': segment.get('confidence', 0.0),
                        'bbox': segment.get('bbox', [])
                    }
                    for i, segment in enumerate(segments)
                ],
                'scene_description': f"Detected {len(segments)} objects in the scene"
            }
            
            # Conversation analysis
            conversation_analysis = {
                'has_conversation': conversation_text is not None and len(conversation_text.strip()) > 0,
                'conversation_content': conversation_text,
                'speaker': conversation_speaker,
                'conversation_length': len(conversation_text.split()) if conversation_text else 0
            }
            
            # Context correlation
            context_insights = []
            if conversation_analysis['has_conversation'] and conversation_text:
                # Analyze relationship between conversation and visual scene
                conv_lower = conversation_text.lower()
                
                # Look for object references in conversation
                for obj in visual_analysis['objects_detected']:
                    obj_type = obj['type'].lower()
                    if obj_type in conv_lower:
                        context_insights.append(f"Conversation mentions {obj_type} which is visible in scene")
                
                # Look for action words that might relate to scene
                action_words = ['look', 'see', 'watch', 'point', 'here', 'there', 'this', 'that']
                mentioned_actions = [word for word in action_words if word in conv_lower]
                if mentioned_actions:
                    context_insights.append(f"Conversation contains spatial/visual references: {', '.join(mentioned_actions)}")
                
                # Look for emotional indicators
                emotion_words = ['happy', 'sad', 'angry', 'excited', 'worried', 'scared', 'surprised']
                mentioned_emotions = [word for word in emotion_words if word in conv_lower]
                if mentioned_emotions:
                    context_insights.append(f"Emotional context detected: {', '.join(mentioned_emotions)}")
            
            # Combined analysis
            analysis = {
                'timestamp': timestamp,
                'visual_analysis': visual_analysis,
                'conversation_analysis': conversation_analysis,
                'context_insights': context_insights,
                'multimodal_score': self._calculate_multimodal_score(visual_analysis, conversation_analysis),
                'scene_description': self._generate_enhanced_description(visual_analysis, conversation_analysis, context_insights)
            }
            
            logger.info(f"Analyzed camera feed with conversation: {len(segments)} segments, conversation: {conversation_analysis['has_conversation']}")
            return MCPToolResult(success=True, result=analysis)
            
        except Exception as e:
            logger.error(f"Error analyzing camera feed: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _calculate_multimodal_score(self, visual: Dict[str, Any], conversation: Dict[str, Any]) -> float:
        """Calculate a score indicating how well visual and conversation data complement each other."""
        score = 0.5  # Base score
        
        if conversation['has_conversation']:
            score += 0.2  # Bonus for having conversation
            
            # Bonus for conversation length (more context)
            conv_length = conversation['conversation_length']
            if conv_length > 10:
                score += 0.1
            elif conv_length > 5:
                score += 0.05
            
            # Bonus if objects are mentioned in conversation
            visual_objects = [obj['type'] for obj in visual['objects_detected']]
            conv_text = conversation['conversation_content'].lower() if conversation['conversation_content'] else ""
            
            for obj_type in visual_objects:
                if obj_type.lower() in conv_text:
                    score += 0.1
                    break
        
        return min(1.0, score)
    
    def _generate_enhanced_description(self, visual: Dict[str, Any], conversation: Dict[str, Any], insights: List[str]) -> str:
        """Generate an enhanced scene description combining visual and conversation data."""
        description_parts = []
        
        # Visual component
        obj_count = visual['object_count']
        if obj_count == 0:
            description_parts.append("No objects detected in the scene")
        else:
            object_types = [obj['type'] for obj in visual['objects_detected']]
            unique_types = list(set(object_types))
            description_parts.append(f"Scene contains {obj_count} objects: {', '.join(unique_types)}")
        
        # Conversation component
        if conversation['has_conversation']:
            conv_length = conversation['conversation_length']
            speaker = conversation.get('speaker', 'unknown speaker')
            description_parts.append(f"Active conversation detected from {speaker} ({conv_length} words)")
            
            # Add sample of conversation if available
            conv_text = conversation['conversation_content']
            if conv_text and len(conv_text) > 50:
                sample = conv_text[:47] + "..."
                description_parts.append(f"Conversation sample: '{sample}'")
            elif conv_text:
                description_parts.append(f"Conversation: '{conv_text}'")
        else:
            description_parts.append("No active conversation detected")
        
        # Context insights
        if insights:
            description_parts.append(f"Context insights: {'; '.join(insights)}")
        
        return ". ".join(description_parts)


class ActionDecisionTool(SimpleMCPTool):
    """Tool for making action decisions based on analysis."""
    
    def __init__(self):
        super().__init__(
            name="decide_action",
            description="Decide what action to take based on camera analysis and conversation context"
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> MCPToolResult:
        """Decide action based on analysis."""
        try:
            analysis = arguments.get('analysis', {})
            
            # Extract analysis components
            visual_analysis = analysis.get('visual_analysis', {})
            conversation_analysis = analysis.get('conversation_analysis', {})
            context_insights = analysis.get('context_insights', [])
            multimodal_score = analysis.get('multimodal_score', 0.5)
            
            object_count = visual_analysis.get('object_count', 0)
            objects = visual_analysis.get('objects_detected', [])
            has_conversation = conversation_analysis.get('has_conversation', False)
            conversation_text = conversation_analysis.get('conversation_content', '')
            
            # Decision logic considering both visual and conversation context
            action = self._determine_action(
                object_count, objects, has_conversation, 
                conversation_text, context_insights, multimodal_score
            )
            
            logger.info(f"Action decision: {action['type']} - {action['reason']}")
            return MCPToolResult(success=True, result=action)
            
        except Exception as e:
            logger.error(f"Error deciding action: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _determine_action(self, object_count: int, objects: List[Dict], has_conversation: bool, 
                         conversation_text: str, context_insights: List[str], multimodal_score: float) -> Dict[str, Any]:
        """Determine action based on multimodal analysis."""
        
        # Initialize action
        action = {
            'type': 'monitor',
            'priority': 'normal',
            'reason': 'Standard monitoring',
            'conversation_influenced': False,
            'multimodal_score': multimodal_score,
            'context_factors': []
        }
        
        # Visual-based decisions
        if object_count == 0:
            action.update({
                'type': 'wait',
                'reason': 'No objects detected',
                'priority': 'low'
            })
        elif object_count > 5:
            action.update({
                'type': 'alert',
                'reason': f'Many objects detected ({object_count})',
                'priority': 'high',
                'object_count': object_count
            })
        
        # Conversation-influenced decisions
        if has_conversation and conversation_text:
            conv_lower = conversation_text.lower()
            action['conversation_influenced'] = True
            
            # Emergency/urgent keywords
            emergency_words = ['help', 'emergency', 'urgent', 'danger', 'problem', 'issue', 'wrong', 'stop']
            if any(word in conv_lower for word in emergency_words):
                action.update({
                    'type': 'alert',
                    'reason': 'Emergency keywords detected in conversation',
                    'priority': 'critical',
                    'emergency_detected': True
                })
                action['context_factors'].append('emergency_language')
            
            # Attention/pointing keywords
            attention_words = ['look', 'see', 'watch', 'here', 'there', 'this', 'that', 'point']
            if any(word in conv_lower for word in attention_words):
                if action['type'] == 'wait':  # Upgrade from wait to monitor
                    action.update({
                        'type': 'monitor',
                        'reason': 'Conversation indicates attention to scene',
                        'priority': 'normal'
                    })
                action['context_factors'].append('visual_reference')
            
            # Question/inquiry keywords
            question_words = ['what', 'where', 'who', 'how', 'why', 'when', '?']
            if any(word in conv_lower for word in question_words):
                action['context_factors'].append('inquiry_detected')
                if action['priority'] != 'critical':
                    action['priority'] = 'high'  # Questions need attention
            
            # Emotional context
            negative_emotions = ['scared', 'worried', 'angry', 'upset', 'confused']
            positive_emotions = ['happy', 'excited', 'good', 'great', 'wonderful']
            
            if any(word in conv_lower for word in negative_emotions):
                action['context_factors'].append('negative_emotion')
                if action['priority'] in ['low', 'normal']:
                    action['priority'] = 'high'
                    action['reason'] += ' (negative emotional context detected)'
            elif any(word in conv_lower for word in positive_emotions):
                action['context_factors'].append('positive_emotion')
        
        # Context insights influence
        if context_insights:
            action['context_factors'].append('multimodal_correlation')
            # If there's good correlation between visual and conversation, increase confidence
            if multimodal_score > 0.8:
                action['confidence'] = 'high'
                action['reason'] += ' (high multimodal correlation)'
            elif multimodal_score > 0.6:
                action['confidence'] = 'medium'
            else:
                action['confidence'] = 'low'
        else:
            action['confidence'] = 'medium'
        
        # Object-specific conversation correlations
        object_types = [obj['type'] for obj in objects]
        if has_conversation and object_types:
            mentioned_objects = []
            for obj_type in object_types:
                if obj_type.lower() in conversation_text.lower():
                    mentioned_objects.append(obj_type)
            
            if mentioned_objects:
                action['mentioned_objects'] = mentioned_objects
                action['context_factors'].append('object_reference')
                if action['type'] == 'wait':
                    action['type'] = 'monitor'
                    action['reason'] = f'Objects mentioned in conversation: {", ".join(mentioned_objects)}'
        
        # Final action assignment
        action['objects'] = [obj['type'] for obj in objects]
        action['total_context_factors'] = len(action['context_factors'])
        
        return action


class SimpleMCPServer:
    """Simple MCP-like server for our agent."""
    
    def __init__(self):
        self.tools: Dict[str, SimpleMCPTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default tools."""
        self.register_tool(CameraAnalysisTool())
        self.register_tool(ActionDecisionTool())
    
    def register_tool(self, tool: SimpleMCPTool):
        """Register a tool."""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """Call a tool by name."""
        if tool_name not in self.tools:
            return MCPToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found"
            )
        
        tool = self.tools[tool_name]
        return await tool.execute(arguments)
    
    def list_tools(self) -> List[Dict[str, str]]:
        """List available tools."""
        return [
            {
                'name': tool.name,
                'description': tool.description
            }
            for tool in self.tools.values()
        ]
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if tool exists."""
        return tool_name in self.tools


# Global MCP server instance
mcp_server = SimpleMCPServer()


async def get_mcp_server() -> SimpleMCPServer:
    """Get the MCP server instance."""
    return mcp_server
