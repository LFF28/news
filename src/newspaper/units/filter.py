"""Filter：按时间窗口过滤新闻，只保留 title 与 contentSnippet。"""
import datetime

from .base import Unit


def _parse_iso(iso_str: str | None) -> datetime.datetime | None:
    if not iso_str:
        return None
    try:
        s = iso_str.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


class Filter(Unit):
    name = "Filter"

    def __init__(self, config: dict, logger):
        super().__init__(config, logger)
        filter_cfg = config.get("filter", {})
        self.window_hours: int = filter_cfg.get("window_hours", 24)

    def run(self, input_data: dict) -> dict:
        now = datetime.datetime.now(datetime.timezone.utc)
        cutoff = now - datetime.timedelta(hours=self.window_hours)

        result: dict = {}
        for group, items in (input_data or {}).items():
            kept = []
            for item in items:
                dt = _parse_iso(item.get("isoDate"))
                # 无法解析时间的条目保守保留
                if dt is None or dt >= cutoff:
                    kept.append(
                        {
                            "title": item.get("title", ""),
                            "contentSnippet": item.get("contentSnippet", ""),
                        }
                    )
            self.logger.info(
                "分组「%s」过滤后保留 %d/%d 条（近 %dh）",
                group, len(kept), len(items), self.window_hours,
            )
            result[group] = kept

        self._output = result
        return result

    def output(self):
        return self._output
