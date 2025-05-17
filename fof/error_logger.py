import logging

# Configure the logger
logger = logging.getLogger(__name__)

# Utility Function
def log_error_with_readkey(message: str):
    logger.error(message)
    input("Press Enter to continue...")
