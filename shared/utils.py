"""
Shared Utilities for Osiris Team Project
Common functions and classes used across team member modules.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path


class OsirisConfig:
    """Configuration manager for Osiris shell."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration from file."""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            return {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot notation key."""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    def get_env(self, key: str, default: str = "") -> str:
        """Get environment variable."""
        return os.getenv(key, default)


def setup_logging(log_level: str = "INFO", log_file: str = "osiris.log") -> logging.Logger:
    """Setup logging configuration for Osiris."""
    
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_path = log_dir / log_file
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger("Osiris")


class CommandHistory:
    """Manage command history for Osiris shell."""
    
    def __init__(self, history_file: str = ".osiris_history", max_history: int = 1000):
        """Initialize command history."""
        self.history_file = Path.home() / history_file
        self.max_history = max_history
        self.commands = self._load_history()
    
    def _load_history(self) -> list:
        """Load command history from file."""
        if not self.history_file.exists():
            return []
        
        try:
            with open(self.history_file, 'r') as f:
                return f.read().splitlines()[-self.max_history:]
        except Exception as e:
            logging.error(f"Failed to load history: {e}")
            return []
    
    def add(self, command: str):
        """Add command to history."""
        self.commands.append(command)
        
        # Keep only max_history items
        if len(self.commands) > self.max_history:
            self.commands = self.commands[-self.max_history:]
        
        # Save to file
        self._save_history()
    
    def _save_history(self):
        """Save history to file."""
        try:
            with open(self.history_file, 'w') as f:
                f.write('\n'.join(self.commands))
        except Exception as e:
            logging.error(f"Failed to save history: {e}")
    
    def get_recent(self, count: int = 10) -> list:
        """Get most recent commands."""
        return self.commands[-count:] if self.commands else []
    
    def search(self, pattern: str) -> list:
        """Search history for pattern."""
        return [cmd for cmd in self.commands if pattern in cmd]
    
    def clear(self):
        """Clear command history."""
        self.commands = []
        self._save_history()


# Module exports
__all__ = ['OsirisConfig', 'setup_logging', 'CommandHistory']
