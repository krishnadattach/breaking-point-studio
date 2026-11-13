"""NODE 1 - research: a real tool-using AGENT (the only agent in the project).

What "agent" means here: Claude (the cheap model) is given ONE tool, `web_search`, and a goal. In a loop IT decides
what to search for, reads the results, notices what is still missing, searches again, and decides when it has enough.
The code does not choose the queries. We only enforce a hard limit of 5 searches.

Goal given to the agent: real measured values for the object across the hazard's FULL range (harmless -> destructive)
plus one surprising fact for the twist level.

Every query the agent chooses is saved to the `research_queries` table the moment it runs, so the dashboard can
show the agent's decisions. Mock mode (no keys, or MOCK_LLM/MOCK_SEARCH=1) skips the agent: free fake searches.
"""
import threading
from typing import Callable

from langchain_core.tools import tool

from .. import config, db, llm, mock
from ..state import State

MAX_SEARCHES = 5            # hard limit, enforced inside the tool (the model cannot talk its way past it)
RECURSION_LIMIT = 25        # safety net on the agent loop itself (each search = ~2 steps)

SYSTEM = """You are the research agent for the YouTube Shorts channel "The Breaking Point".
In each episode ONE object faces 10 escalating levels of ONE hazard (heat, cold, pressure, impact speed, lightning or
spin) until it fails. A writer will turn your findings into the script, so they need real facts.

YOUR GOAL
1. Find real MEASURED values (with units) for the object across the hazard's FULL range: from harmless (an ordinary
   value where the object is clearly fine) up through damaging, to extreme (where it fails or is destroyed). The
   writer needs enough to spread 10 levels across that whole range, so do not stop at one threshold or one end.
2. Find ONE genuinely surprising fact for the twist level: a documented case where the object survives when you would
   expect it to fail, or fails when you would expect it to survive.

HOW TO WORK
- You have a web_search tool and a HARD LIMIT of 5 searches in total. Choose your own queries.
- After each result, think about what is still missing (the harmless end? the extreme end? a surprise?) and search
  for exactly that, with a more specific query. Do not repeat a query.
- Stop as soon as you have enough. You do not have to use all 5 searches.
- Only report values that appear in the search results. Never invent numbers.

FINAL ANSWER (when you stop searching, reply with this and call no more tools)
FINDINGS:
- <value with unit> | <what happens to the object> | <source URL>
(one line per value, ordered from harmless to destructive, aim for 8-12 lines)
TWIST FACT: <the surprising fact> | <source URL>
GAPS: <anything you could not find, or "none">"""


def _text_of(message) -> str:
    """The text of a Claude message (content may be a string or a list of blocks, some of them 'thinking')."""
    content = message.content
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


def run_research_agent(model, search: Callable[[str], list[dict]], episode_id: str, topic: str,
                       max_searches: int = MAX_SEARCHES) -> tuple[list[dict], str]:
    """Run the agent loop. `model` is a chat model, `search(query)` returns [{url,title,snippet}].
    Both are parameters so tests can plug in fakes (free). Returns (sources, notes)."""
    from langchain.agents import create_agent
    from langgraph.errors import GraphRecursionError

    sources: dict[str, dict] = {}       # url -> source, first one wins
    lock = threading.Lock()             # the model may ask for several searches in one turn
    used = 0

    @tool
    def web_search(query: str) -> str:
        """Search the web. Returns up to 4 results (title, URL, text excerpt). Hard limit: 5 searches per episode."""
        nonlocal used
        with lock:
            if used >= max_searches:
                return (f"SEARCH LIMIT REACHED ({max_searches}/{max_searches} used). No more searches are allowed. "
                        "Write your final answer now from what you already have.")
            used += 1
            seq = used
        try:
            results = search(query)
        except Exception as e:    # a failed search still counts; tell the agent so it can adapt
            db.add_research_query(episode_id, seq, query, [])
            return f"Search failed: {e}. ({max_searches - seq} searches left)"
        db.add_research_query(episode_id, seq, query, [r["url"] for r in results])
        with lock:
            for r in results:
                sources.setdefault(r["url"], r)
        body = "\n\n".join(f"TITLE: {r['title']}\nURL: {r['url']}\nTEXT: {r['snippet'][:800]}" for r in results)
        return f"({max_searches - seq} searches left)\n\n{body or 'No results.'}"

    agent = create_agent(model, tools=[web_search], system_prompt=SYSTEM)
    notes = ""
    try:
        result = agent.invoke({"messages": [("human", f"Episode topic: {topic}")]},
                              config={"recursion_limit": RECURSION_LIMIT})
        notes = _text_of(result["messages"][-1]).strip()
    except GraphRecursionError:
        notes = "(the research agent hit its step limit before writing a summary)"

    if used == 0:    # the agent never searched: do one plain search so the writer is not left empty-handed
        with lock:
            used = 1
        results = search(topic)
        db.add_research_query(episode_id, 1, topic + "  (fallback: agent did not search)", [r["url"] for r in results])
        for r in results:
            sources.setdefault(r["url"], r)
    return list(sources.values()), notes


def _tavily_search(query: str) -> list[dict]:
    from langchain_tavily import TavilySearch
    res = TavilySearch(max_results=4).invoke({"query": query})
    return [{"url": r["url"], "title": r.get("title", ""), "snippet": r.get("content", "")[:1200]}
            for r in res.get("results", [])]


def research(state: State) -> dict:
    episode_id, topic = state["episode_id"], state["topic"]
    db.reset_research(episode_id)

    if config.mock_search() or config.mock_llm():     # the agent needs BOTH Claude and Tavily
        obj, hazard = mock.parse_topic(topic)
        for i, q in enumerate([f"MOCK query: {obj} {hazard} harmless values",
                               f"MOCK query: {obj} {hazard} destruction threshold",
                               f"MOCK query: {obj} surprising {hazard} survival"], start=1):
            db.add_research_query(episode_id, i, q, [s["url"] for s in mock.search(topic)])
        sources, notes = mock.search(topic), mock.research_notes(topic)
    else:
        sources, notes = run_research_agent(llm.cheap(), _tavily_search, episode_id, topic)

    db.save_sources(episode_id, sources)
    db.save_research_notes(episode_id, notes)
    return {"stage": "research", "sources": sources, "research_notes": notes}
