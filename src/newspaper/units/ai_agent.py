"""AI Agent：让 claude 读取已排序的 JSON 文件，整理成 HTML 并保存到本地。

为避免命令行参数过长（rerank 后的 JSON 仍可能较大），prompt 中只传文件路径，
由 claude 自行读取该文件内容。
"""
import datetime
import os
import re
import subprocess

from .base import Unit

PROMPT_TEMPLATE = """你是一个新闻摘要助手。

我的兴趣关键词：{keywords}

请读取本地 JSON 文件：{json_path}
该文件是按分组整理、并已按我的兴趣相关度排序的新闻数据，结构为 {{ "组名": [ {{title, contentSnippet, relevance_score}}, ... ] }}。

请完成以下任务：
1. 将其整理成一份**完整的中文 HTML 页面**（含 <html><head><style>...</style></head><body>），排版美观，适合邮件阅读；
2. 每个分组用标题分区，每条新闻展示标题与简介，保持文件中已有的排序；
3. 只输出 HTML 源码本身，不要任何额外解释、不要使用 markdown 代码块包裹。

请将最终 HTML 写入文件：{html_path}
"""


class AIAgent(Unit):
    name = "AIAgent"

    def __init__(self, config: dict, logger):
        super().__init__(config, logger)
        agent_cfg = config.get("ai_agent", {})
        self.claude_bin: str = agent_cfg.get("claude_bin", "claude")
        self.timeout: int = agent_cfg.get("timeout", 300)
        self.keywords: list = config.get("keywords", [])
        self.output_dir: str = config.get("output", {}).get("dir", "./output")
        self._html_path = None

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        text = text.strip()
        m = re.match(r"^```[a-zA-Z]*\n(.*)\n```$", text, re.DOTALL)
        return m.group(1).strip() if m else text

    def run(self, input_data: dict) -> dict:
        json_path = input_data.get("json_path") if isinstance(input_data, dict) else None
        if not json_path or not os.path.isfile(json_path):
            raise RuntimeError(f"AIAgent 未收到有效的排序 JSON 文件：{json_path}")

        os.makedirs(self.output_dir, exist_ok=True)
        date_str = datetime.date.today().isoformat()
        html_path = os.path.abspath(os.path.join(self.output_dir, f"digest_{date_str}.html"))
        json_abs = os.path.abspath(json_path)

        prompt = PROMPT_TEMPLATE.format(
            keywords="、".join(self.keywords) if self.keywords else "（无特别偏好）",
            json_path=json_abs,
            html_path=html_path,
        )

        self.logger.info("调用 claude 整理新闻（读取 %s）……", json_abs)
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

        # 优先使用 claude 写入的文件；若未写入，则回退到 stdout
        if os.path.isfile(html_path):
            with open(html_path, "r", encoding="utf-8") as f:
                html = f.read()
        else:
            html = self._strip_code_fence(proc.stdout)
            if not html:
                raise RuntimeError("claude 既未写入 HTML 文件，stdout 也为空")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)

        self.logger.info("HTML 已保存：%s", html_path)
        self._html_path = html_path
        return {"html_path": html_path, "html": html}

    def output(self):
        return {"html_path": self._html_path}
