import sys
from loguru import logger


def setup_logger():
    logger.remove()
    logger.add(
        sys.stdout,
        format="{time} {level} {message}",
        serialize=True,  # For Loki/JSON format
    )
    return logger
