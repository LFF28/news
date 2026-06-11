"""RSS Reader（头单元）：按分组抓取 RSS 源，归一化为统一字段的分组 json。"""
import datetime
import time

import feedparser

from .base import Unit


def _struct_to_iso(struct_time) -> str | None:
    """将 feedparser 的 time.struct_time（UTC）转为 ISO8601 字符串。"""
    if not struct_time:
        return None
    dt = datetime.datetime.fromtimestamp(
        time.mktime(struct_time), tz=datetime.timezone.utc
    )
    return dt.isoformat().replace("+00:00", "Z")


def _normalize_entry(entry) -> dict:
    """将单条 feed entry 归一化为统一字段结构。"""
    content = ""
    if entry.get("content"):
        content = entry["content"][0].get("value", "")
    elif entry.get("summary"):
        content = entry.get("summary", "")

    snippet = entry.get("summary", "") or content
    categories = [t.get("term", "") for t in entry.get("tags", [])] if entry.get("tags") else []

    return {
        "creator": entry.get("author", ""),
        "title": entry.get("title", ""),
        "link": entry.get("link", ""),
        "pubDate": entry.get("published", entry.get("updated", "")),
        "content": content,
        "contentSnippet": snippet,
        "guid": entry.get("id", entry.get("link", "")),
        "categories": categories,
        "isoDate": _struct_to_iso(
            entry.get("published_parsed") or entry.get("updated_parsed")
        ),
    }


class RSSReader(Unit):
    name = "RSSReader"

    def __init__(self, config: dict, logger):
        super().__init__(config, logger)
        # sources: { "组名": [url, ...], ... }
        self.sources: dict = config.get("sources", {})

    def run(self, input_data=None) -> dict:
        result: dict = {}
        for group, urls in self.sources.items():
            items = []
            for url in urls:
                try:
                    self.logger.debug("抓取 RSS：%s", url)
                    feed = feedparser.parse(url)
                    if feed.bozo and not feed.entries:
                        self.logger.warning("源解析失败：%s（%s）", url, feed.bozo_exception)
                        continue
                    for entry in feed.entries:
                        items.append(_normalize_entry(entry))
                except Exception as e:  # 单源失败不影响整体
                    self.logger.warning("抓取源出错：%s（%s）", url, e)
            self.logger.info("分组「%s」共获取 %d 条", group, len(items))
            result[group] = items

        self._output = result
        return result

    def output(self):
        return self._output
