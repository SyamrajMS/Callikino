"""
Callikino — The Headless Video Editing Framework for AI Agents
===============================================================

A Python DSL that translates abstract video editing operations into
optimized, single-pass FFmpeg execution commands. Designed for LLM
agents to call via structured tool-use, not for humans to fight GUIs.

Quick Start:
    from callikino import CallikinoEngine

    engine = CallikinoEngine()
    engine.import_asset("video.mp4", "main")
    engine.add_cut_clip("main", layer_index=0, timeline_start=0, src_in=5, src_out=12)
    engine.adjust_color(saturation=1.2, contrast=1.1)
    engine.add_subtitle("Hello World", start_time=1.0, end_time=3.0)
    print(engine.generate_ffmpeg_command("output.mp4"))
"""

__version__ = "0.1.0"
__author__ = "Syamraj"

from callikino.core import CallikinoEngine
from callikino.agent_executor import AgentExecutor
from callikino.tool_schemas import TOOL_SCHEMAS, get_tool_schemas, get_tool_names

__all__ = [
    "CallikinoEngine",
    "AgentExecutor",
    "TOOL_SCHEMAS",
    "get_tool_schemas",
    "get_tool_names",
]
