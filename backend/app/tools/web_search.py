"""
博查 Web Search API 封装。
输入搜索词，返回网页摘要文本，供 LLM 参考。
"""
import requests


class WebSearchTool:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.bochaai.com/v1/web-search"

    def search(self, query: str, count: int = 5) -> list[dict]:
        """
        搜索并返回结果列表。
        返回: [{"title": ..., "snippet": ..., "url": ...}, ...]
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "query": query,
            "count": count,
            "summary": True,
        }
        try:
            resp = requests.post(self.url, headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("data", {}).get("webPages", {}).get("value", [])[:count]:
                results.append({
                    "title": item.get("name", ""),
                    "snippet": item.get("snippet", ""),
                    "url": item.get("url", ""),
                })
            return results
        except Exception as e:
            print(f"[WebSearch] 搜索失败: {e}")
            return []
