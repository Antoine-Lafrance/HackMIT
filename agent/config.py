"""Configuration management for the Camera Feed Agent."""

import os
import json
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class AnthropicAPIConfig:
    """Configuration for Anthropic API."""
    api_key: str = ""
    model: str = "claude-3-sonnet-20240229"
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: float = 30.0
    max_retries: int = 3


@dataclass
class PromptSystemConfig:
    """Configuration for prompt system."""
    use_custom_prompts: bool = True
    prompt_directory: str = "./prompts"
    default_scenario: str = "general"
    enable_prompt_caching: bool = True


@dataclass
class AgentRuntimeConfig:
    """Runtime configuration for the agent."""
    feed_interval_ms: int = 100
    max_queue_size: int = 1000
    processing_timeout: float = 5.0
    enable_logging: bool = True
    log_level: str = "INFO"
    
    def __post_init__(self):
        """Validate configuration values."""
        if self.feed_interval_ms <= 0:
            raise ValueError("feed_interval_ms must be positive")
        if self.max_queue_size <= 0:
            raise ValueError("max_queue_size must be positive")
        if self.processing_timeout <= 0:
            raise ValueError("processing_timeout must be positive")
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError("log_level must be a valid logging level")


@dataclass
class MCPToolConfig:
    """Configuration for MCP tools."""
    default_timeout: float = 10.0
    max_retries: int = 3
    enable_caching: bool = True
    custom_tools: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CameraConfig:
    """Configuration for camera input."""
    expected_fps: int = 30
    frame_buffer_size: int = 10
    segment_validation: bool = True
    min_confidence_threshold: float = 0.5
    max_segments_per_frame: int = 100


@dataclass
class ModalConfig:
    """Configuration for Modal deployment."""
    cpu_count: int = 2
    memory_mb: int = 2048
    timeout_seconds: int = 300
    max_concurrent: int = 10
    scale_down_delay: float = 60.0


@dataclass
class SystemConfig:
    """Complete system configuration."""
    agent: AgentRuntimeConfig = field(default_factory=AgentRuntimeConfig)
    mcp: MCPToolConfig = field(default_factory=MCPToolConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    modal: ModalConfig = field(default_factory=ModalConfig)
    anthropic: AnthropicAPIConfig = field(default_factory=AnthropicAPIConfig)
    prompts: PromptSystemConfig = field(default_factory=PromptSystemConfig)
    
    # Environment settings
    environment: str = "development"
    debug_mode: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemConfig':
        """Create from dictionary."""
        return cls(
            agent=AgentRuntimeConfig(**data.get('agent', {})),
            mcp=MCPToolConfig(**data.get('mcp', {})),
            camera=CameraConfig(**data.get('camera', {})),
            modal=ModalConfig(**data.get('modal', {})),
            anthropic=AnthropicAPIConfig(**data.get('anthropic', {})),
            prompts=PromptSystemConfig(**data.get('prompts', {})),
            environment=data.get('environment', 'development'),
            debug_mode=data.get('debug_mode', False)
        )
    
    def save_to_file(self, filepath: Union[str, Path]):
        """Save configuration to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: Union[str, Path]) -> 'SystemConfig':
        """Load configuration from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


class ConfigManager:
    """Manages configuration loading and validation."""
    
    def __init__(self, config_dir: Optional[Union[str, Path]] = None):
        self.config_dir = Path(config_dir) if config_dir else Path.cwd()
        self._config: Optional[SystemConfig] = None
    
    def get_config(self, reload: bool = False) -> SystemConfig:
        """Get the current configuration."""
        if self._config is None or reload:
            self._config = self._load_config()
        return self._config
    
    def _load_config(self) -> SystemConfig:
        """Load configuration from various sources."""
        config = SystemConfig()
        
        # 1. Load from default config file if exists
        default_config_path = self.config_dir / "config.json"
        if default_config_path.exists():
            try:
                file_config = SystemConfig.load_from_file(default_config_path)
                config = file_config
            except Exception as e:
                print(f"Warning: Could not load config from {default_config_path}: {e}")
        
        # 2. Override with environment-specific config
        env_config_path = self.config_dir / f"config.{config.environment}.json"
        if env_config_path.exists():
            try:
                env_config = SystemConfig.load_from_file(env_config_path)
                config = self._merge_configs(config, env_config)
            except Exception as e:
                print(f"Warning: Could not load environment config from {env_config_path}: {e}")
        
        # 3. Override with environment variables
        config = self._apply_env_overrides(config)
        
        return config
    
    def _merge_configs(self, base: SystemConfig, override: SystemConfig) -> SystemConfig:
        """Merge two configurations, with override taking precedence."""
        base_dict = base.to_dict()
        override_dict = override.to_dict()
        
        # Deep merge dictionaries
        merged = self._deep_merge_dict(base_dict, override_dict)
        
        return SystemConfig.from_dict(merged)
    
    def _deep_merge_dict(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_dict(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _apply_env_overrides(self, config: SystemConfig) -> SystemConfig:
        """Apply environment variable overrides."""
        env_mappings = {
            'AGENT_FEED_INTERVAL_MS': ('agent', 'feed_interval_ms', int),
            'AGENT_MAX_QUEUE_SIZE': ('agent', 'max_queue_size', int),
            'AGENT_PROCESSING_TIMEOUT': ('agent', 'processing_timeout', float),
            'AGENT_ENABLE_LOGGING': ('agent', 'enable_logging', self._str_to_bool),
            'AGENT_LOG_LEVEL': ('agent', 'log_level', str),
            
            'MCP_DEFAULT_TIMEOUT': ('mcp', 'default_timeout', float),
            'MCP_MAX_RETRIES': ('mcp', 'max_retries', int),
            'MCP_ENABLE_CACHING': ('mcp', 'enable_caching', self._str_to_bool),
            
            'CAMERA_EXPECTED_FPS': ('camera', 'expected_fps', int),
            'CAMERA_FRAME_BUFFER_SIZE': ('camera', 'frame_buffer_size', int),
            'CAMERA_MIN_CONFIDENCE': ('camera', 'min_confidence_threshold', float),
            
            'MODAL_CPU_COUNT': ('modal', 'cpu_count', int),
            'MODAL_MEMORY_MB': ('modal', 'memory_mb', int),
            'MODAL_TIMEOUT_SECONDS': ('modal', 'timeout_seconds', int),
            
            'ANTHROPIC_API_KEY': ('anthropic', 'api_key', str),
            'ANTHROPIC_MODEL': ('anthropic', 'model', str),
            'ANTHROPIC_MAX_TOKENS': ('anthropic', 'max_tokens', int),
            'ANTHROPIC_TEMPERATURE': ('anthropic', 'temperature', float),
            'ANTHROPIC_TIMEOUT': ('anthropic', 'timeout', float),
            'ANTHROPIC_MAX_RETRIES': ('anthropic', 'max_retries', int),
            
            'PROMPTS_USE_CUSTOM': ('prompts', 'use_custom_prompts', self._str_to_bool),
            'PROMPTS_DIRECTORY': ('prompts', 'prompt_directory', str),
            'PROMPTS_DEFAULT_SCENARIO': ('prompts', 'default_scenario', str),
            
            'ENVIRONMENT': (None, 'environment', str),
            'DEBUG_MODE': (None, 'debug_mode', self._str_to_bool),
        }
        
        config_dict = config.to_dict()
        
        for env_var, (section, key, converter) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    converted_value = converter(env_value)
                    if section:
                        config_dict[section][key] = converted_value
                    else:
                        config_dict[key] = converted_value
                except (ValueError, TypeError) as e:
                    print(f"Warning: Invalid value for {env_var}: {env_value} ({e})")
        
        return SystemConfig.from_dict(config_dict)
    
    def _str_to_bool(self, value: str) -> bool:
        """Convert string to boolean."""
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
    
    def create_default_config_file(self, filename: str = "config.json"):
        """Create a default configuration file."""
        config = SystemConfig()
        config_path = self.config_dir / filename
        config.save_to_file(config_path)
        return config_path
    
    def validate_config(self, config: Optional[SystemConfig] = None) -> Dict[str, Any]:
        """Validate configuration and return validation results."""
        if config is None:
            config = self.get_config()
        
        issues = []
        warnings = []
        
        # Validate agent config
        if config.agent.feed_interval_ms < 10:
            warnings.append("Feed interval less than 10ms may cause high CPU usage")
        if config.agent.max_queue_size > 10000:
            warnings.append("Large queue size may consume significant memory")
        
        # Validate camera config
        if config.camera.min_confidence_threshold < 0 or config.camera.min_confidence_threshold > 1:
            issues.append("Confidence threshold must be between 0 and 1")
        
        # Validate modal config
        if config.modal.memory_mb < 512:
            warnings.append("Low memory allocation may cause performance issues")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }


# Global config manager instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get the global configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def get_config() -> SystemConfig:
    """Get the current system configuration."""
    return get_config_manager().get_config()

def reload_config() -> SystemConfig:
    """Reload configuration from files and environment."""
    return get_config_manager().get_config(reload=True)
