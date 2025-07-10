import logging
import json
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config:
    """Class to load configuration parameters from a JSON file."""

    def __init__(self, config_path="config/config.json"):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self):
        """Loads config parameters from the JSON configuration file."""
        try:
            with open(self.config_path) as file:
                config = json.load(file)
            logger.info("Configuration loaded successfully.")
            return config
        except FileNotFoundError:
            logger.error(f"Configuration file not found at {self.config_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from the configuration file: {e}")
            return {}
 