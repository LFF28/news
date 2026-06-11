"""AI Agent：调用 claude CLI，按兴趣关键词选出每组前 N 条并整理成 HTML，保存到本地。"""
import datetime
import json
import os
import re
import subprocess

from .base import Unit

PROMPT_TEMPLATE = """你是一个新闻摘要助手。下面是按分组整理的新闻 JSON 数据。

我的兴趣关键词：{keywords}

请完成以下任务：
1. 对每个分组，按照与我兴趣关键词的相关度，挑选最相关的前 {top_n} 条新闻；
2. 将结果整理成一份**完整的中文 HTML 页面**（含 <html><head><style>...</style></head><body>），排版美观，适合邮件阅读；
3. 每个分组用标题分区，每条新闻展示标题与简介；
4. 只输出 HTML 源码本身，不要任何额外解释、不要使用 markdown 代码块包裹。

新闻数据（JSON）：
{data}
"""


class AIAgent(Unit):
    name = "AIAgent"

    def __init__(self, config: dict, logger):
        super().__init__(config, logger)
        agent_cfg = config.get("ai_agent", {})
        self.claude_bin: str = agent_cfg.get("claude_bin", "claude")
        self.top_n: int = agent_cfg.get("top_n", 10)
        self.timeout: int = agent_cfg.get("timeout", 300)
        self.keywords: list = agent_cfg.get("keywords", [])
        self.output_dir: str = config.get("output", {}).get("dir", "./output")
        self._html_path = None

    def _build_prompt(self, data: dict) -> str:
        return PROMPT_TEMPLATE.format(
            keywords="、".join(self.keywords) if self.keywords else "（无特别偏好）",
            top_n=self.top_n,
            data=json.dumps(data, ensure_ascii=False, indent=2),
        )

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        """去掉可能存在的 ```html ... ``` 包裹。"""
        text = text.strip()
        m = re.match(r"^```[a-zA-Z]*\n(.*)\n```$", text, re.DOTALL)
        return m.group(1).strip() if m else text

    def run(self, input_data: dict) -> str:
        prompt = self._build_prompt(input_data)
        self.logger.info("调用 claude 整理新闻（top_n=%d）……", self.top_n)
        self.logger.debug("claude 命令：%s --dangerously-skip-permissions -p", self.claude_bin)

        try:
            proc = subprocess.run(
                [self.claude_bin, "--dangerously-skip-permissions", "-p", prompt],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except FileNotFoundError:
            raise RuntimeError(f"未找到 claude 可执行文件：{self.claude_bin}")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"claude 调用超时（>{self.timeout}s）")

        if proc.returncode != 0:
            raise RuntimeError(f"claude 调用失败（code={proc.returncode}）：{proc.stderr.strip()}")

        html = self._strip_code_fence(proc.stdout)
        if not html:
            raise RuntimeError("claude 返回空内容")

        os.makedirs(self.output_dir, exist_ok=True)
        date_str = datetime.date.today().isoformat()
        path = os.path.join(self.output_dir, f"digest_{date_str}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

        self.logger.info("HTML 已保存：%s", path)
        self._html_path = path
        self._output = {"html_path": path, "html": html}
        return {"html_path": path, "html": html}

    def output(self):
        # 输出路径而非全文，避免 -v 刷屏
        return {"html_path": self._html_path}
