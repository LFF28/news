"""流水线编排：按顺序串联各单元，依次传递数据。"""
import json


class Pipeline:
    def __init__(self, units: list, logger, verbose: bool = False):
        self.units = units
        self.logger = logger
        self.verbose = verbose

    def _print_output(self, unit):
        out = unit.output()
        if out is None:
            return
        self.logger.info("===== 单元 [%s] 输出 =====", unit.name)
        if isinstance(out, (dict, list)):
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            print(out)

    def run(self):
        data = None
        for unit in self.units:
            self.logger.info("运行单元：%s", unit.name)
            data = unit.run(data)
            if self.verbose:
                self._print_output(unit)
        self.logger.info("流水线执行完毕")
        return data
