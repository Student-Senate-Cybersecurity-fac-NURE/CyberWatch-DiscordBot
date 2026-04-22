import logging
from typing import Dict, List, Any

from .public_settings import (
    ERROR_LOG_FILENAME_SUFFIX,
    INFO_LOG_FILENAME_SUFFIX,
    LOGGER_FORMAT,
    LOGS_DIRECTORY,
)

def get_missing_config_params(config: Dict[str, Any], section_name: str) -> List[str]:
    return [
        detail_name for detail_name, detail in config[section_name].items() if not detail
    ]


def verify_config_section(config: Dict[str, Any], section_name: str) -> bool:
    return section_name in config and all(
        [detail for detail_name, detail in config[section_name].items()]
    )

def configure_logger(name: str = __name__) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Define handlers with specific types to satisfy mypy
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    
    file_handler_info = logging.FileHandler(
        f"{LOGS_DIRECTORY}/{name}{INFO_LOG_FILENAME_SUFFIX}"
    )
    file_handler_info.setLevel(logging.INFO)
    
    file_handler_error = logging.FileHandler(
        f"{LOGS_DIRECTORY}/{name}{ERROR_LOG_FILENAME_SUFFIX}"
    )
    file_handler_error.setLevel(logging.ERROR)

    logger_format = logging.Formatter(LOGGER_FORMAT)

    handlers: List[logging.Handler] = [stream_handler, file_handler_info, file_handler_error]
    for handler in handlers:
        handler.setFormatter(logger_format)
        logger.addHandler(handler)

    return logger
