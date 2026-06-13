"""Reranker：用 qwen3-rerank 按兴趣关键词对每组新闻排序，取 top_n，保存为单个 JSON。"""
import datetime
import json
import os
from http import HTTPStatus

import dashscope

from .base import Unit


class Reranker(Unit):
    name = "Reranker"

    def __init__(self, config: dict, logger):
        super().__init__(config, logger)
        rerank_cfg = config.get("rerank", {})
        self.api_key: str = rerank_cfg.get("api_key", "")
        self.model: str = rerank_cfg.get("model", "qwen3-rerank")
        self.top_n: int = rerank_cfg.get("top_n", 10)
        self.instruct: str = rerank_cfg.get("instruct", "")
        self.keywords: list = config.get("keywords", [])
        self.output_dir: str = config.get("output", {}).get("dir", "./output")
        self._json_path = None

    def _query(self) -> str:
        return "、".join(self.keywords) if self.keywords else "AI 新闻"

    def _rerank_group(self, items: list) -> list:
        """对单组新闻按关键词相关度排序，返回 top_n 条（保留原字段）。"""
        if not items:
            return []
        # 用 title + contentSnippet 拼成待排序文本
        documents = [
            f"{it.get('title', '')}。{it.get('contentSnippet', '')}".strip("。")
            for it in items
        ]
        resp = dashscope.TextReRank.call(
            api_key=self.api_key,
            model=self.model,
            query=self._query(),
            documents=documents,
            top_n=min(self.top_n, len(documents)),
            return_documents=False,
            instruct=self.instruct or None,
        )
        if resp.status_code != HTTPStatus.OK:
            raise RuntimeError(
                f"rerank 调用失败（code={resp.status_code}）：{resp.message}"
            )
        ranked = []
        for r in resp.output["results"]:
            idx = r["index"]
            item = dict(items[idx])
            item["relevance_score"] = r.get("relevance_score")
            ranked.append(item)
        return ranked

    def run(self, input_data: dict) -> dict:
        result: dict = {}
        for group, items in (input_data or {}).items():
            ranked = self._rerank_group(items)
            self.logger.info("分组「%s」rerank 后取前 %d 条", group, len(ranked))
            result[group] = ranked

        os.makedirs(self.output_dir, exist_ok=True)
        date_str = datetime.date.today().isoformat()
        path = os.path.join(self.output_dir, f"ranked_{date_str}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        self.logger.info("排序结果已保存：%s", path)

        self._json_path = path
        self._output = result
        # 传给下游：分组数据 + JSON 文件路径
        return {"ranked": result, "json_path": path}

    def output(self):
        return self._output
