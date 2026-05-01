import logging
import sys

from app.core.config import settings


def setup_logging() -> logging.Logger:
    level = logging.DEBUG if settings.DEBUG else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logger = logging.getLogger("agent_chat")
    logger.setLevel(level)
    return logger


logger = setup_logging()
