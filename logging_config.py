import logging
import os
import sys

# Create a custom logger
logger = logging.getLogger()

# Prevent logs from being propagated to the root logger
logger.propagate = False

# Set the default log level from environment variable or use DEBUG
log_level = os.getenv('LOG_LEVEL', 'DEBUG').upper()
logger.setLevel(getattr(logging, log_level, logging.DEBUG))

# Create handlers
stdout_handler = logging.StreamHandler(sys.stdout)

# Set log levels for handlers
stdout_handler.setLevel(logging.DEBUG)

# Create formatters and add it to handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stdout_handler.setFormatter(formatter)

# Clear existing handlers, and add our handler
if logger.hasHandlers():
    logger.handlers.clear()

logger.addHandler(stdout_handler)
