"""单元基类。每个工作流单元继承此类。"""
import logging


class Unit:
    """工作流单元基类。

    - 子类从传入的 config 字典读取自身参数。
    - 实现 run(input_data) 完成处理并返回传给下一单元的数据。
    - 中间单元应重写 output() 返回本单元结果（供 -v 打印）；尾单元保持默认 None。
    """

    name = "unit"

    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self._output = None

    def run(self, input_data=None):
        """执行单元逻辑，返回结果传递给下一单元。子类必须实现。"""
        raise NotImplementedError

    def output(self):
        """返回本单元的可读输出，供 -v 打印。中间单元应重写。"""
        return None
