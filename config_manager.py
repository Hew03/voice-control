import json
from pathlib import Path
import pyaudio

class ConfigManager:
    CONFIG_FILE = "config.json"
    
    def __init__(self):
        self.default_config = {
            'mic_index': 4,
            'rate': 48000,
            'chunk': 4096,
            'channels': 1,
            'model_name': 'base',
            'hotkey': 'f2',
            'translation_trigger': 'start translation',
            'stop_translation': 'stop translation',
            'roblox_window_title': 'Roblox',
            'enable_chinese_autocorrect': False
        }
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from file, falling back to defaults if needed"""
        try:
            if Path(self.CONFIG_FILE).exists():
                with open(self.CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    return {**self.default_config, **config}
        except Exception as e:
            print(f"Error loading config: {e}")
        return self.default_config.copy()
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get(self, key, default=None):
        """Get a configuration value"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set a configuration value"""
        self.config[key] = value
    
    def update(self, updates):
        """Update multiple configuration values"""
        self.config.update(updates)
    
    def get_all(self):
        """Get all configuration values"""
        return self.config.copy()