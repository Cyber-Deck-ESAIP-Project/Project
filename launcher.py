import os
import sys

# Define project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# AUTOMATIC VIRTUAL ENVIRONMENT INJECTION
# This ensures that even if launched via 'sudo python3 launcher.py', 
# the app can find dependencies installed in the local .venv.
VENV_SITE_PACKAGES = os.path.join(PROJECT_ROOT, ".venv", "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
if os.path.exists(VENV_SITE_PACKAGES):
    sys.path.insert(0, VENV_SITE_PACKAGES)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.logger import get_logger
from utils.config_loader import load_config

def main():
    # Initialize logger
    logger = get_logger()
    logger.info("Initializing CyberDeck...")

    try:
        # Load configuration
        config = load_config()
        logger.info("Configuration loaded successfully.")
        
        # Start the MVC Event-Driven UI Framework
        from mode_select.main_window import start_ui
        logger.info("Auto-launching Event-Driven MVC Dashboard...")
        start_ui()

    except Exception as e:
        logger.critical(f"Critical error during startup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
