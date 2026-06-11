"""主入口：解析配置、加载单元、组装并运行流水线。"""
from .config_loader import load_config
from .logger import setup_logger
from .pipeline import Pipeline
from .units.rss_reader import RSSReader
from .units.filter import Filter
from .units.ai_agent import AIAgent
from .units.email_sender import EmailSender

# 单元加载顺序（头 -> 尾）
UNIT_CLASSES = [RSSReader, Filter, AIAgent, EmailSender]


def run(verbose: bool = False, config_path: str | None = None) -> int:
    config = load_config(config_path)
    logger = setup_logger(config.get("log", {}).get("level", "INFO"), verbose=verbose)
    logger.info("已加载配置：%s", config.get("_config_path"))

    units = [cls(config, logger) for cls in UNIT_CLASSES]
    logger.info("已加载单元：%s", " -> ".join(u.name for u in units))

    pipeline = Pipeline(units, logger, verbose=verbose)
    try:
        pipeline.run()
    except Exception as e:
        logger.error("流水线执行失败：%s", e)
        return 1
    return 0
