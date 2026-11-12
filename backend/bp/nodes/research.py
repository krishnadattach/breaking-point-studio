"""NODE 1 - research: web search for real facts.

Why: the script must be based on real sources, so fact_check can later link
every claim to a URL. Uses Tavily (needs TAVILY_API_KEY, free tier exists).
No key -> fake MOCK sources so the pipeline still runs.
"""
from .. import config, mock
from ..state import State


def research(state: State) -> dict:
    topic = state["topic"]
    if config.mock_search():
        return {"stage": "research", "sources": mock.search(topic)}

    from langchain_tavily import TavilySearch

    obj, hazard = mock.parse_topic(topic)
    queries = [
        f"{obj} physical properties limits",
        f"{obj} {hazard} real measured values thresholds",
        f"what happens to {obj} under extreme {hazard}",
    ]
    tool = TavilySearch(max_results=4)
    seen, sources = set(), []
    for q in queries:
        res = tool.invoke({"query": q})
        for r in res.get("results", []):
            if r["url"] not in seen:
                seen.add(r["url"])
                sources.append({"url": r["url"], "title": r.get("title", ""), "snippet": r.get("content", "")[:1200]})
    return {"stage": "research", "sources": sources}
