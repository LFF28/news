"""AI Agent：让本地 AI Agent 读取已排序的 JSON 文件，整理成 HTML 并保存到本地。

为避免命令行参数过长（rerank 后的 JSON 仍可能较大），prompt 中只传文件路径，
由 Agent 自行读取该文件内容。
"""
import datetime
import os
import re
import subprocess

from .base import Unit

PROMPT_TEMPLATE = """你是一个新闻简报编辑和 HTML 渲染助手。

请读取本地 JSON 文件：{json_path}
该文件是按分组整理、并已由 reranker 排序完成的新闻数据，结构为 {{ "组名": [ {{title, contentSnippet}}, ... ] }}。

请完成以下任务：
1. 严格基于下面的 HTML 模版生成一份完整 HTML 页面，风格保持简约、科技、适合邮件阅读；
2. 每个分组生成一个 section，按 JSON 中分组出现顺序使用 group-theme-0 到 group-theme-5 循环套用预设配色，便于分辨；
3. 对每条新闻输出统一的中文简报风格：标题保留原意，正文用 1 到 2 句中文概括，长度尽量稳定在 80 到 140 个中文字符；
4. 如果 contentSnippet 很短、缺少上下文或只有标题信息，请检索公开相关信息进行补全，只加入能合理确认的背景、产品、公司、影响或进展；
5. 如果 contentSnippet 很长，请压缩为简洁简报，保留最关键事实、变化和影响，删除细枝末节；
6. 不要重新排序、合并、删除或新增新闻；JSON 已经排好序，只按文件中的分组和新闻顺序渲染；
7. 每条新闻只展示 title 和统一后的 brief，不展示原始 contentSnippet、不展示关键词、不展示排序分数、不展示 relevance_score；
8. 不要在 HTML 中展示来源链接、检索过程、引用脚注或“据检索”等说明；
9. 只输出 HTML 源码本身，不要任何额外解释、不要使用 markdown 代码块包裹。

HTML 模版如下：
{html_template}

请将最终 HTML 写入文件：{html_path}
"""


class AIAgent(Unit):
    name = "AIAgent"

    def __init__(self, config: dict, logger):
        super().__init__(config, logger)
        agent_cfg = config.get("ai_agent", {})
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.backend: str = agent_cfg.get("backend", "claude").lower()
        self.claude_bin: str = agent_cfg.get("claude_bin", "claude")
        self.codex_bin: str = agent_cfg.get("codex_bin", "codex")
        self.codex_model: str | None = agent_cfg.get("codex_model")
        self.codex_profile: str | None = agent_cfg.get("codex_profile")
        self.enable_web_search: bool = agent_cfg.get("enable_web_search", True)
        self.template_path: str = agent_cfg.get(
            "template_path",
            os.path.join(root, "config", "news_template.html"),
        )
        self.save_run_output: bool = agent_cfg.get("save_run_output", True)
        self.timeout: int = agent_cfg.get("timeout", 300)
        self.output_dir: str = config.get("output", {}).get("dir", "./output")
        self._html_path = None
        self._stdout_path = None
        self._stderr_path = None

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        text = text.strip()
        m = re.match(r"^```[a-zA-Z]*\n(.*)\n```$", text, re.DOTALL)
        return m.group(1).strip() if m else text

    def _load_html_template(self) -> str:
        template_path = os.path.abspath(os.path.expanduser(self.template_path))
        if not os.path.isfile(template_path):
            raise RuntimeError(f"未找到 HTML 模版文件：{template_path}")
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()

    def _command(self, prompt: str) -> list[str]:
        if self.backend == "claude":
            self.logger.debug("claude 命令：%s --dangerously-skip-permissions -p", self.claude_bin)
            return [self.claude_bin, "--dangerously-skip-permissions", "-p", prompt]

        if self.backend == "codex":
            cmd = [
                self.codex_bin,
                "-a",
                "never",
            ]
            if self.enable_web_search:
                cmd.append("--search")
            cmd.extend([
                "exec",
                "--dangerously-bypass-approvals-and-sandbox",
                "--color",
                "never",
                "-C",
                os.getcwd(),
            ])
            if self.codex_model:
                cmd.extend(["-m", self.codex_model])
            if self.codex_profile:
                cmd.extend(["-p", self.codex_profile])
            cmd.append(prompt)
            self.logger.debug("codex 命令：%s exec ...", self.codex_bin)
            return cmd

        raise RuntimeError(f"不支持的 AI Agent 后端：{self.backend}（可选：claude/codex）")

    def _save_run_output(self, run_stamp: str, stdout: str, stderr: str):
        if not self.save_run_output:
            return
        stdout_path = os.path.abspath(os.path.join(self.output_dir, f"{self.backend}_{run_stamp}.stdout.txt"))
        stderr_path = os.path.abspath(os.path.join(self.output_dir, f"{self.backend}_{run_stamp}.stderr.txt"))
        with open(stdout_path, "w", encoding="utf-8") as f:
            f.write(stdout or "")
        with open(stderr_path, "w", encoding="utf-8") as f:
            f.write(stderr or "")
        self._stdout_path = stdout_path
        self._stderr_path = stderr_path
        self.logger.info("Agent stdout/stderr 已保存：%s / %s", stdout_path, stderr_path)

    def run(self, input_data: dict) -> dict:
        json_path = input_data.get("json_path") if isinstance(input_data, dict) else None
        if not json_path or not os.path.isfile(json_path):
            raise RuntimeError(f"AIAgent 未收到有效的排序 JSON 文件：{json_path}")

        os.makedirs(self.output_dir, exist_ok=True)
        date_str = datetime.date.today().isoformat()
        run_stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        html_path = os.path.abspath(os.path.join(self.output_dir, f"digest_{date_str}.html"))
        json_abs = os.path.abspath(json_path)
        html_template = self._load_html_template()

        prompt = PROMPT_TEMPLATE.format(
            json_path=json_abs,
            html_template=html_template,
            html_path=html_path,
        )

        cmd = self._command(prompt)
        self.logger.info("调用 %s 整理新闻（读取 %s）……", self.backend, json_abs)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except FileNotFoundError:
            bin_path = self.claude_bin if self.backend == "claude" else self.codex_bin
            raise RuntimeError(f"未找到 {self.backend} 可执行文件：{bin_path}")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"{self.backend} 调用超时（>{self.timeout}s）")

        self._save_run_output(run_stamp, proc.stdout, proc.stderr)

        if proc.returncode != 0:
            raise RuntimeError(f"{self.backend} 调用失败（code={proc.returncode}）：{proc.stderr.strip()}")

        # 优先使用 Agent 写入的文件；若未写入，则回退到 stdout
        if os.path.isfile(html_path):
            with open(html_path, "r", encoding="utf-8") as f:
                html = f.read()
        else:
            html = self._strip_code_fence(proc.stdout)
            if not html:
                raise RuntimeError(f"{self.backend} 既未写入 HTML 文件，stdout 也为空")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)

        self.logger.info("HTML 已保存：%s", html_path)
        self._html_path = html_path
        return {"html_path": html_path, "html": html}

    def output(self):
        return {
            "html_path": self._html_path,
            "stdout_path": self._stdout_path,
            "stderr_path": self._stderr_path,
        }
