import json
import os
from utils.logger import get_logger

logger = get_logger()

def load_config(config_path="config/config.json"):
    """Loads the main configuration file."""
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found at {config_path}")
        raise FileNotFoundError(f"Config file missing: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise

def save_config(config_data, config_path="config/config.json"):
    """Saves changes back to the main configuration file."""
    try:
        # Create directory if missing
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=4)
            
        logger.info(f"Configuration saved successfully to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save config to {config_path}: {e}")
        return False
