"""Agent prompt configuration and management."""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class PromptConfig:
    """Configuration for agent prompts."""
    
    # Default system prompt for the agent
    system_prompt: str = """add default prompt here

You are an intelligent camera feed analysis agent with access to MCP (Model Context Protocol) tools. Your role is to process real-time camera feeds that have been pre-segmented using SAM (Segment Anything Model) and make intelligent decisions based on what you observe.

## Available MCP Tools:
- `analyze_camera_feed`: Analyzes SAM segments and extracts insights about objects, scene composition, and context
- `decide_action`: Makes decisions about what actions to take based on analysis results
- `custom_tools`: Additional tools may be available depending on your configuration

## Your Objectives:
1. **Real-time Analysis**: Process camera frames efficiently and accurately
2. **Object Recognition**: Identify and classify objects in the segmented data
3. **Scene Understanding**: Understand spatial relationships and context
4. **Decision Making**: Determine appropriate actions based on observations
5. **Alert Generation**: Identify situations requiring attention or action

## Processing Guidelines:
- Analyze each frame's segments for object types, confidence levels, and spatial distribution
- Consider temporal context when available (previous frames, trends)
- Prioritize safety-critical observations (people, vehicles, unusual activities)
- Generate clear, actionable insights and recommendations
- Maintain situational awareness across multiple frames

## Response Format:
Always provide structured analysis including:
- Object counts and types
- Confidence assessments
- Spatial analysis
- Recommended actions
- Any alerts or warnings

Remember: You are processing real-time data, so be efficient and focus on the most important observations for decision-making."""

    # User prompt template for specific analysis requests
    user_prompt_template: str = """Analyze this camera frame data:

Frame ID: {frame_id}
Timestamp: {timestamp}
Number of segments: {segment_count}

Segments data:
{segments_json}

Metadata:
{metadata_json}

Please provide a comprehensive analysis and recommend appropriate actions."""

    # Prompt for tool calling context
    tool_context_prompt: str = """Use the available MCP tools to analyze this camera feed data. Follow this workflow:

1. First, call `analyze_camera_feed` with the segment data
2. Based on the analysis, call `decide_action` to determine what actions to take
3. Provide a summary of findings and actions taken

Be thorough but efficient in your analysis."""

    # Custom prompts for different scenarios
    scenario_prompts: Optional[Dict[str, str]] = None

    def __post_init__(self):
        """Initialize scenario prompts."""
        if self.scenario_prompts is None:
            self.scenario_prompts = {
                "security": "Focus on security-related observations: unauthorized access, suspicious behavior, safety hazards.",
                "traffic": "Analyze traffic patterns, vehicle counts, pedestrian activity, and traffic violations.",
                "retail": "Monitor customer behavior, product interactions, queue lengths, and store activities.",
                "general": "Provide general scene analysis covering all visible objects and activities."
            }


class PromptManager:
    """Manages agent prompts and templates."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.cwd() / "prompts"
        self.config_path.mkdir(exist_ok=True)
        self._prompt_config: Optional[PromptConfig] = None
        self._custom_prompts: Dict[str, str] = {}
    
    def get_prompt_config(self) -> PromptConfig:
        """Get the current prompt configuration."""
        if self._prompt_config is None:
            self._prompt_config = self._load_prompt_config()
        return self._prompt_config
    
    def _load_prompt_config(self) -> PromptConfig:
        """Load prompt configuration from files and environment."""
        config = PromptConfig()
        
        # Load system prompt from file if exists
        system_prompt_file = self.config_path / "system_prompt.txt"
        if system_prompt_file.exists():
            config.system_prompt = system_prompt_file.read_text(encoding='utf-8').strip()
        
        # Load user prompt template from file if exists
        user_prompt_file = self.config_path / "user_prompt_template.txt"
        if user_prompt_file.exists():
            config.user_prompt_template = user_prompt_file.read_text(encoding='utf-8').strip()
        
        # Load tool context prompt from file if exists
        tool_context_file = self.config_path / "tool_context_prompt.txt"
        if tool_context_file.exists():
            config.tool_context_prompt = tool_context_file.read_text(encoding='utf-8').strip()
        
        # Load scenario prompts from files
        scenario_dir = self.config_path / "scenarios"
        if scenario_dir.exists():
            if config.scenario_prompts is None:
                config.scenario_prompts = {}
            for scenario_file in scenario_dir.glob("*.txt"):
                scenario_name = scenario_file.stem
                scenario_prompt = scenario_file.read_text(encoding='utf-8').strip()
                config.scenario_prompts[scenario_name] = scenario_prompt
        
        # Load custom prompts
        self._load_custom_prompts()
        
        return config
    
    def _load_custom_prompts(self):
        """Load custom prompts from files."""
        custom_dir = self.config_path / "custom"
        if custom_dir.exists():
            for prompt_file in custom_dir.glob("*.txt"):
                prompt_name = prompt_file.stem
                prompt_content = prompt_file.read_text(encoding='utf-8').strip()
                self._custom_prompts[prompt_name] = prompt_content
    
    def get_system_prompt(self, scenario: Optional[str] = None) -> str:
        """Get the system prompt, optionally enhanced with scenario context."""
        config = self.get_prompt_config()
        base_prompt = config.system_prompt
        
        if scenario and config.scenario_prompts and scenario in config.scenario_prompts:
            scenario_context = config.scenario_prompts[scenario]
            base_prompt += f"\n\n## Scenario-Specific Instructions:\n{scenario_context}"
        
        return base_prompt
    
    def get_user_prompt(self, frame_data: Dict[str, Any]) -> str:
        """Generate user prompt for a specific frame."""
        config = self.get_prompt_config()
        
        return config.user_prompt_template.format(
            frame_id=frame_data.get('frame_id', 'unknown'),
            timestamp=frame_data.get('timestamp', 'unknown'),
            segment_count=len(frame_data.get('segments', [])),
            segments_json=self._format_segments(frame_data.get('segments', [])),
            metadata_json=self._format_metadata(frame_data.get('metadata', {}))
        )
    
    def get_tool_context_prompt(self) -> str:
        """Get the tool context prompt for MCP tool usage."""
        config = self.get_prompt_config()
        return config.tool_context_prompt
    
    def get_custom_prompt(self, name: str) -> Optional[str]:
        """Get a custom prompt by name."""
        return self._custom_prompts.get(name)
    
    def _format_segments(self, segments: List[Dict[str, Any]]) -> str:
        """Format segments data for prompt."""
        if not segments:
            return "No segments detected"
        
        formatted = []
        for i, segment in enumerate(segments):
            formatted.append(f"Segment {i+1}: {segment}")
        
        return "\n".join(formatted)
    
    def _format_metadata(self, metadata: Dict[str, Any]) -> str:
        """Format metadata for prompt."""
        if not metadata:
            return "No metadata available"
        
        formatted = []
        for key, value in metadata.items():
            formatted.append(f"{key}: {value}")
        
        return "\n".join(formatted)
    
    def create_prompt_files(self):
        """Create default prompt files for customization."""
        config = PromptConfig()
        
        # Create directories
        self.config_path.mkdir(exist_ok=True)
        (self.config_path / "scenarios").mkdir(exist_ok=True)
        (self.config_path / "custom").mkdir(exist_ok=True)
        
        # Create system prompt file
        system_file = self.config_path / "system_prompt.txt"
        if not system_file.exists():
            system_file.write_text(config.system_prompt, encoding='utf-8')
        
        # Create user prompt template file
        user_file = self.config_path / "user_prompt_template.txt"
        if not user_file.exists():
            user_file.write_text(config.user_prompt_template, encoding='utf-8')
        
        # Create tool context prompt file
        tool_file = self.config_path / "tool_context_prompt.txt"
        if not tool_file.exists():
            tool_file.write_text(config.tool_context_prompt, encoding='utf-8')
        
        # Create scenario prompt files
        scenario_dir = self.config_path / "scenarios"
        if config.scenario_prompts:
            for scenario_name, scenario_prompt in config.scenario_prompts.items():
                scenario_file = scenario_dir / f"{scenario_name}.txt"
                if not scenario_file.exists():
                    scenario_file.write_text(scenario_prompt, encoding='utf-8')
        
        return {
            'system_prompt': system_file,
            'user_prompt_template': user_file,
            'tool_context_prompt': tool_file,
            'scenarios_dir': scenario_dir,
            'custom_dir': self.config_path / "custom"
        }
    
    def update_prompt(self, prompt_type: str, content: str):
        """Update a specific prompt type."""
        if prompt_type == "system":
            file_path = self.config_path / "system_prompt.txt"
        elif prompt_type == "user_template":
            file_path = self.config_path / "user_prompt_template.txt"
        elif prompt_type == "tool_context":
            file_path = self.config_path / "tool_context_prompt.txt"
        else:
            # Custom prompt
            file_path = self.config_path / "custom" / f"{prompt_type}.txt"
        
        file_path.parent.mkdir(exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        
        # Reload configuration
        self._prompt_config = None


# Global prompt manager instance
_prompt_manager = None

def get_prompt_manager() -> PromptManager:
    """Get the global prompt manager."""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager

def get_system_prompt(scenario: Optional[str] = None) -> str:
    """Get the system prompt."""
    return get_prompt_manager().get_system_prompt(scenario)

def get_user_prompt(frame_data: Dict[str, Any]) -> str:
    """Get user prompt for frame data."""
    return get_prompt_manager().get_user_prompt(frame_data)

def get_tool_context_prompt() -> str:
    """Get tool context prompt."""
    return get_prompt_manager().get_tool_context_prompt()
