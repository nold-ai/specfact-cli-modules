import logging


LOGGER = logging.getLogger(__name__)


def debug_value(value: object) -> None:
    LOGGER.info("value=%s", value)
