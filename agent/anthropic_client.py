"""Anthropic client integration for the agent."""

import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from dotenv import load_dotenv

try:
    from anthropic import Anthropic, AsyncAnthropic
except ImportError:
    Anthropic = None
    AsyncAnthropic = None
    logging.warning("Anthropic SDK not installed. Install with: pip install anthropic")

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class AnthropicConfig:
    """Configuration for Anthropic API."""
    api_key: str
    model: str = "claude-3-sonnet-20240229"
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: float = 30.0
    max_retries: int = 3


class AnthropicClient:
    """Anthropic client for agent inference."""
    
    def __init__(self, config: Optional[AnthropicConfig] = None):
        if not AsyncAnthropic:
            raise ImportError("Anthropic SDK not available. Install with: pip install anthropic")
        
        if config is None:
            config = self._load_config_from_env()
        
        self.config = config
        self.client = AsyncAnthropic(
            api_key=config.api_key,
            timeout=config.timeout,
            max_retries=config.max_retries
        )
    
    def _load_config_from_env(self) -> AnthropicConfig:
        """Load configuration from environment variables."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        
        return AnthropicConfig(
            api_key=api_key,
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
            max_tokens=int(os.getenv("ANTHROPIC_MAX_TOKENS", "4096")),
            temperature=float(os.getenv("ANTHROPIC_TEMPERATURE", "0.7")),
            timeout=float(os.getenv("ANTHROPIC_TIMEOUT", "30.0")),
            max_retries=int(os.getenv("ANTHROPIC_MAX_RETRIES", "3"))
        )
    
    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a response using the Anthropic API."""
        try:
            messages = [
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
            
            # Add context if provided
            if context:
                context_str = f"\n\nContext: {context}"
                messages[0]["content"] += context_str
            
            response = await self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=messages
            )
            
            return {
                'success': True,
                'content': response.content[0].text if response.content else '',
                'model': response.model,
                'usage': {
                    'input_tokens': response.usage.input_tokens if response.usage else 0,
                    'output_tokens': response.usage.output_tokens if response.usage else 0
                },
                'stop_reason': response.stop_reason
            }
            
        except Exception as e:
            logger.error(f"Error generating response with Anthropic: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': '',
                'usage': {'input_tokens': 0, 'output_tokens': 0}
            }
    
    async def analyze_camera_frame(
        self,
        frame_data: Dict[str, Any],
        system_prompt: str,
        user_prompt_template: str
    ) -> Dict[str, Any]:
        """Analyze a camera frame using Anthropic."""
        try:
            # Format the user prompt with frame data
            user_prompt = user_prompt_template.format(
                frame_id=frame_data.get('frame_id', 'unknown'),
                timestamp=frame_data.get('timestamp', 'unknown'),
                segment_count=len(frame_data.get('segments', [])),
                segments_json=str(frame_data.get('segments', [])),
                metadata_json=str(frame_data.get('metadata', {}))
            )
            
            # Generate analysis
            response = await self.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                context={'frame_data': frame_data}
            )
            
            if response['success']:
                # Parse the response content for structured analysis
                analysis = self._parse_analysis_response(response['content'])
                analysis['raw_response'] = response['content']
                analysis['usage'] = response['usage']
                return analysis
            else:
                return {
                    'success': False,
                    'error': response.get('error', 'Unknown error'),
                    'analysis': None
                }
                
        except Exception as e:
            logger.error(f"Error analyzing camera frame: {e}")
            return {
                'success': False,
                'error': str(e),
                'analysis': None
            }
    
    def _parse_analysis_response(self, content: str) -> Dict[str, Any]:
        """Parse the analysis response from Anthropic."""
        # This is a simple parser - you can enhance it based on your prompt design
        # For now, return the raw content with some basic structure
        
        analysis = {
            'success': True,
            'scene_description': '',
            'objects_detected': [],
            'recommended_actions': [],
            'alerts': [],
            'confidence_score': 0.0
        }
        
        try:
            # Try to extract structured information from the response
            lines = content.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for section headers
                if 'scene description' in line.lower() or 'analysis' in line.lower():
                    current_section = 'description'
                elif 'objects' in line.lower() and 'detected' in line.lower():
                    current_section = 'objects'
                elif 'actions' in line.lower() or 'recommendations' in line.lower():
                    current_section = 'actions'
                elif 'alerts' in line.lower() or 'warnings' in line.lower():
                    current_section = 'alerts'
                else:
                    # Add content to current section
                    if current_section == 'description':
                        analysis['scene_description'] += line + ' '
                    elif current_section == 'objects' and line.startswith('-'):
                        analysis['objects_detected'].append(line[1:].strip())
                    elif current_section == 'actions' and line.startswith('-'):
                        analysis['recommended_actions'].append(line[1:].strip())
                    elif current_section == 'alerts' and line.startswith('-'):
                        analysis['alerts'].append(line[1:].strip())
            
            # Clean up descriptions
            analysis['scene_description'] = analysis['scene_description'].strip()
            
            # Set confidence based on content quality
            analysis['confidence_score'] = min(1.0, len(analysis['scene_description']) / 100.0)
            
        except Exception as e:
            logger.warning(f"Could not parse structured analysis: {e}")
            # Fallback to raw content
            analysis['scene_description'] = content[:500]  # Truncate if too long
        
        return analysis
    
    async def make_decision(
        self,
        analysis: Dict[str, Any],
        system_prompt: str,
        decision_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make a decision based on analysis results."""
        try:
            # Create decision prompt
            user_prompt = f"""Based on the following analysis, what actions should be taken?

Analysis Results:
- Scene Description: {analysis.get('scene_description', 'N/A')}
- Objects Detected: {', '.join(analysis.get('objects_detected', []))}
- Current Alerts: {', '.join(analysis.get('alerts', []))}

{decision_context or 'Provide a clear action recommendation with reasoning.'}
"""
            
            response = await self.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                context={'analysis': analysis}
            )
            
            if response['success']:
                decision = self._parse_decision_response(response['content'])
                decision['raw_response'] = response['content']
                decision['usage'] = response['usage']
                return decision
            else:
                return {
                    'success': False,
                    'error': response.get('error', 'Unknown error'),
                    'decision': None
                }
                
        except Exception as e:
            logger.error(f"Error making decision: {e}")
            return {
                'success': False,
                'error': str(e),
                'decision': None
            }
    
    def _parse_decision_response(self, content: str) -> Dict[str, Any]:
        """Parse the decision response from Anthropic."""
        decision = {
            'success': True,
            'action_type': 'monitor',  # default
            'priority': 'normal',
            'reasoning': '',
            'specific_actions': [],
            'confidence': 0.0
        }
        
        try:
            # Simple parsing logic - enhance based on your needs
            content_lower = content.lower()
            
            # Determine action type
            if 'alert' in content_lower or 'warning' in content_lower or 'urgent' in content_lower:
                decision['action_type'] = 'alert'
                decision['priority'] = 'high'
            elif 'monitor' in content_lower or 'observe' in content_lower or 'watch' in content_lower:
                decision['action_type'] = 'monitor'
                decision['priority'] = 'normal'
            elif 'wait' in content_lower or 'no action' in content_lower:
                decision['action_type'] = 'wait'
                decision['priority'] = 'low'
            else:
                decision['action_type'] = 'analyze'
                decision['priority'] = 'normal'
            
            # Extract reasoning
            decision['reasoning'] = content[:200].strip()  # First 200 chars as reasoning
            
            # Extract specific actions (lines starting with -)
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('-') and len(line) > 2:
                    decision['specific_actions'].append(line[1:].strip())
            
            # Set confidence based on content length and specificity
            decision['confidence'] = min(1.0, (len(content) + len(decision['specific_actions']) * 20) / 300.0)
            
        except Exception as e:
            logger.warning(f"Could not parse structured decision: {e}")
            decision['reasoning'] = content[:100]  # Fallback to raw content
        
        return decision


# Global client instance
_anthropic_client: Optional[AnthropicClient] = None

async def get_anthropic_client() -> AnthropicClient:
    """Get the global Anthropic client."""
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = AnthropicClient()
    return _anthropic_client

def create_anthropic_client(config: Optional[AnthropicConfig] = None) -> AnthropicClient:
    """Create a new Anthropic client with optional custom configuration."""
    return AnthropicClient(config)
