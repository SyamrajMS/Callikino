"""
Callikino Agent Executor — Week 8
==================================
Routes structured tool-call dictionaries (as emitted by an LLM) into
live CallikinoEngine method invocations. This is the bridge between
an AI reasoning loop and the headless video editing engine.

Usage:
    from core import CallikinoEngine
    from agent_executor import AgentExecutor

    engine = CallikinoEngine()
    executor = AgentExecutor(engine)

    # Simulate an LLM emitting a tool call
    result = executor.dispatch({
        "name": "import_asset",
        "arguments": {"file_path": "video.mp4", "alias": "main"}
    })
"""

import json
import traceback
from typing import Dict, Any, List, Optional

from callikino.core import CallikinoEngine


class AgentExecutor:
    """
    Dispatches LLM tool-call dicts into CallikinoEngine method calls.

    The executor maintains a reference to a single engine instance and
    provides:
      - dispatch()    : execute a single tool call
      - batch()       : execute a sequence of tool calls
      - get_state()   : return current engine state as JSON
      - get_history() : return the execution log
    """

    def __init__(self, engine: Optional[CallikinoEngine] = None):
        """
        Initialize the executor with an optional pre-configured engine.
        If no engine is provided, a default 1920x1080@30fps engine is created.
        """
        self.engine = engine or CallikinoEngine()
        self.history: List[Dict[str, Any]] = []

        # Map tool names to engine methods
        self._dispatch_table: Dict[str, callable] = {
            "import_asset": self.engine.import_asset,
            "add_cut_clip": self.engine.add_cut_clip,
            "add_audio_clip": self.engine.add_audio_clip,
            "adjust_color": self.engine.adjust_color,
            "apply_lut": self.engine.apply_lut,
            "set_volume": self.engine.set_volume,
            "audio_duck": self.engine.audio_duck,
            "add_subtitle": self.engine.add_subtitle,
            "kinetic_zoom": self.engine.kinetic_zoom,
            "speed_ramp": self.engine.speed_ramp,
            "compile_blueprint": self.engine.compile_blueprint,
            "generate_ffmpeg_command": self.engine.generate_ffmpeg_command,
        }

    def dispatch(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single tool call and return a structured result.

        Parameters:
          tool_call : dict with keys:
            - "name" (str): The function name to invoke.
            - "arguments" (dict | str): The keyword arguments for the function.
              If a JSON string, it will be parsed automatically.

        Returns:
          dict with keys:
            - "tool_name" (str)
            - "status" ("success" | "error")
            - "result" (Any): Return value from the function, or None.
            - "error" (str | None): Error message if status is "error".
        """
        name = tool_call.get("name", "")
        raw_args = tool_call.get("arguments", {})

        # Handle arguments as JSON string (OpenAI format)
        if isinstance(raw_args, str):
            try:
                raw_args = json.loads(raw_args)
            except json.JSONDecodeError as e:
                entry = {
                    "tool_name": name,
                    "status": "error",
                    "result": None,
                    "error": f"Failed to parse arguments JSON: {e}"
                }
                self.history.append(entry)
                return entry

        # Validate tool name
        if name not in self._dispatch_table:
            entry = {
                "tool_name": name,
                "status": "error",
                "result": None,
                "error": (
                    f"Unknown tool '{name}'. "
                    f"Available: {list(self._dispatch_table.keys())}"
                )
            }
            self.history.append(entry)
            return entry

        # Execute
        try:
            fn = self._dispatch_table[name]
            result = fn(**raw_args)
            entry = {
                "tool_name": name,
                "status": "success",
                "result": result,
                "error": None
            }
        except Exception as e:
            entry = {
                "tool_name": name,
                "status": "error",
                "result": None,
                "error": f"{type(e).__name__}: {e}"
            }

        self.history.append(entry)
        return entry

    def batch(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute a sequence of tool calls in order. Stops on first error
        unless continue_on_error is handled by the caller.

        Parameters:
          tool_calls : List of tool call dicts (same format as dispatch).

        Returns:
          List of result dicts from each dispatch call.
        """
        results = []
        for tc in tool_calls:
            result = self.dispatch(tc)
            results.append(result)
            if result["status"] == "error":
                break  # Fail-fast: stop the chain on first error
        return results

    def get_state(self, pretty: bool = True) -> str:
        """Return the current engine state as a JSON string."""
        return self.engine.compile_blueprint(pretty=pretty)

    def get_history(self) -> List[Dict[str, Any]]:
        """Return the full execution log of all dispatched tool calls."""
        return list(self.history)

    def reset(self, resolution: str = "1920x1080", fps: int = 30) -> None:
        """
        Reset the engine and executor to a clean state.
        Useful for starting a new project without creating a new executor.
        """
        self.engine = CallikinoEngine(resolution=resolution, fps=fps)
        self.history.clear()

        # Rebuild dispatch table for new engine instance
        self._dispatch_table = {
            "import_asset": self.engine.import_asset,
            "add_cut_clip": self.engine.add_cut_clip,
            "add_audio_clip": self.engine.add_audio_clip,
            "adjust_color": self.engine.adjust_color,
            "apply_lut": self.engine.apply_lut,
            "set_volume": self.engine.set_volume,
            "audio_duck": self.engine.audio_duck,
            "add_subtitle": self.engine.add_subtitle,
            "kinetic_zoom": self.engine.kinetic_zoom,
            "speed_ramp": self.engine.speed_ramp,
            "compile_blueprint": self.engine.compile_blueprint,
            "generate_ffmpeg_command": self.engine.generate_ffmpeg_command,
        }
