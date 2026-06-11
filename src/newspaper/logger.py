"""日志与 -v 输出控制。"""
import logging
import sys

_LOGGER_NAME = "newspaper"


def setup_logger(level: str = "INFO", verbose: bool = False) -> logging.Logger:
    """初始化全局 logger。verbose 为 True 时强制 DEBUG 级别。"""
    logger = logging.getLogger(_LOGGER_NAME)
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
    )
    logger.addHandler(handler)

    resolved = logging.DEBUG if verbose else getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(resolved)
    logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)
