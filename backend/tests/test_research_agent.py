"""Free test of the research agent loop (no API calls, no Tavily).

A scripted FAKE chat model plays Claude: it asks for searches, reads the results, and finally answers.
It tries to search 6 times to prove the hard limit of 5 holds. Uses the real LangChain agent + the real MySQL tables.
Run from the backend folder:  ..\\.venv\\Scripts\\python -m tests.test_research_agent
"""
import uuid

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from bp import db
from bp.nodes.research import run_research_agent


class ScriptedModel(BaseChatModel):
    turns: list            # each turn = list of queries to search, or a final-answer string
    seen_tool_messages: list = []
    step: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted-fake"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen_tool_messages[:] = [m.content for m in messages if isinstance(m, ToolMessage)]
        turn = self.turns[self.step]
        self.step += 1
        if isinstance(turn, str):
            msg = AIMessage(content=turn)
        else:
            msg = AIMessage(content="", tool_calls=[
                {"name": "web_search", "args": {"query": q}, "id": f"call_{self.step}_{i}"} for i, q in enumerate(turn)])
        return ChatResult(generations=[ChatGeneration(message=msg)])


def fake_search(query: str) -> list[dict]:
    return [{"url": f"https://example.com/{abs(hash(query)) % 1000}/{i}", "title": f"Result {i} for {query}",
             "snippet": f"text about {query}"} for i in range(2)]


def main():
    ep = "test-" + uuid.uuid4().hex[:8]
    db.init_db()
    db.create_episode(ep, "A grain of sand vs 10 levels of speed")
    try:
        model = ScriptedModel(turns=[
            ["sand grain wind speed harmless"],                  # turn 1: one search
            ["sand grain impact 100 m/s", "sand grain 3000 m/s"],  # turn 2: two parallel searches
            ["q4", "q5", "q6 (over the limit)"],                 # turn 3: three at once -> the 6th must be refused
            "FINDINGS:\n- 1 m/s | fine | https://example.com/x\nTWIST FACT: none | none\nGAPS: none",
        ])
        sources, notes = run_research_agent(model, fake_search, ep, "A grain of sand vs 10 levels of speed")
        rows = db.get_episode(ep)["research"]["queries"]
        queries = [r["query"] for r in rows]
        print("queries saved:", queries)
        assert len(queries) == 5, f"expected exactly 5 searches, got {len(queries)}"
        assert [r["seq"] for r in rows] == [1, 2, 3, 4, 5]
        assert "q6 (over the limit)" not in queries
        assert any("SEARCH LIMIT REACHED" in m for m in model.seen_tool_messages), "6th search was not refused"
        assert notes.startswith("FINDINGS"), notes
        assert len(sources) == 10, len(sources)
        print("OK: limit of 5 held, 6th search refused, notes + sources returned")

        # an agent that stops early (cheap and fine): 1 search only
        db.reset_research(ep)
        model2 = ScriptedModel(turns=[["only query"], "FINDINGS:\n- a | b | c\nTWIST FACT: x | y\nGAPS: none"])
        run_research_agent(model2, fake_search, ep, "t")
        assert len(db.get_episode(ep)["research"]["queries"]) == 1
        print("OK: agent may stop early")

        # an agent that never searches: the safety fallback does one plain search
        db.reset_research(ep)
        model3 = ScriptedModel(turns=["I already know everything."])
        sources3, _ = run_research_agent(model3, fake_search, ep, "t")
        q3 = db.get_episode(ep)["research"]["queries"]
        assert len(q3) == 1 and "fallback" in q3[0]["query"] and sources3
        print("OK: fallback search when the agent does not search")
    finally:
        with db.connect() as c, c.cursor() as cur:
            cur.execute("DELETE FROM episodes WHERE id=%s", (ep,))   # cascades to research_queries


if __name__ == "__main__":
    main()
