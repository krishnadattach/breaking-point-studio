"""The LangGraph workflow: connects the 8 nodes.

   research -> write_script -> fact_check --(failed claims, max 2x)--> write_script
                                   |
                                   v
                             review_script  (STOP: human approves or sends notes)
                                   |  notes -> write_script
                                   v
        voiceover -> render -> assemble -> review_video  (STOP: human final approval)
                                              |  notes -> write_script
                                              v
                                             END
"""
from contextlib import contextmanager

from langgraph.checkpoint.mysql.pymysql import PyMySQLSaver
from langgraph.graph import END, START, StateGraph

from . import config
from .nodes.assemble import assemble
from .nodes.fact_check import fact_check, route_after_fact_check
from .nodes.render import render
from .nodes.research import research
from .nodes.review import (review_script, review_video, route_after_review_script,
                           route_after_review_video)
from .nodes.voiceover import voiceover
from .nodes.write_script import write_script
from .state import State


def build_graph(checkpointer):
    g = StateGraph(State)
    for name, fn in [("research", research), ("write_script", write_script), ("fact_check", fact_check),
                     ("review_script", review_script), ("voiceover", voiceover), ("render", render),
                     ("assemble", assemble), ("review_video", review_video)]:
        g.add_node(name, fn)

    g.add_edge(START, "research")
    g.add_edge("research", "write_script")
    g.add_edge("write_script", "fact_check")
    g.add_conditional_edges("fact_check", route_after_fact_check, ["write_script", "review_script"])
    g.add_conditional_edges("review_script", route_after_review_script, ["voiceover", "write_script"])
    g.add_edge("voiceover", "render")
    g.add_edge("render", "assemble")
    g.add_edge("assemble", "review_video")
    g.add_conditional_edges("review_video", route_after_review_video, [END, "write_script"])
    return g.compile(checkpointer=checkpointer)


@contextmanager
def mysql_checkpointer():
    """Durable memory for the graph: every step is saved in MySQL (tables created on first use)."""
    with PyMySQLSaver.from_conn_string(config.mysql_conn_string()) as saver:
        saver.setup()
        yield saver
