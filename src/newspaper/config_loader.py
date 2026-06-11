"""配置加载：读取 config/ 目录下的 YAML 配置文件。"""
import os

import yaml

DEFAULT_CONFIG_NAME = "config.yaml"


def find_config_path(explicit_path: str | None = None) -> str:
    """定位配置文件。优先级：显式参数 > NEWSPAPER_CONFIG 环境变量 > config/config.yaml。"""
    if explicit_path:
        path = explicit_path
    elif os.environ.get("NEWSPAPER_CONFIG"):
        path = os.environ["NEWSPAPER_CONFIG"]
    else:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(root, "config", DEFAULT_CONFIG_NAME)

    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"未找到配置文件：{path}。请复制 config/config.example.yaml 为 config/config.yaml 并填写。"
        )
    return path


def load_config(explicit_path: str | None = None) -> dict:
    """加载并返回配置字典。"""
    path = find_config_path(explicit_path)
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    config["_config_path"] = path
    return config
