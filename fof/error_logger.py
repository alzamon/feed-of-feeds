import logging

# Configure the logger
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Utility Function
def log_error_with_readkey(message: str):
    logger.error(message)
    input("Press Enter to continue...")
