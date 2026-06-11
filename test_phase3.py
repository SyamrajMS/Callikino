"""
Phase 3 Integration Tests -- Tool Schemas, Agent Executor, and JumpCut Pipeline
"""

import os
import sys
import json

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import CallikinoEngine
from tool_schemas import TOOL_SCHEMAS, get_tool_schemas, get_tool_names
from agent_executor import AgentExecutor
from pipelines.jumpcut import (
    SilenceRegion, WordTimestamp, TranscriptSegment,
    compute_speech_segments, parse_whisper_json,
    identify_emphasis_words, JumpCutPipeline
)


def run_tests():
    print("=" * 60)
    print("  CALLIKINO -- PHASE 3 AGENTIC AUTOMATION TESTS")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Setup mock files
    # ------------------------------------------------------------------
    mock_video = "mock_footage.mp4"
    mock_music = "mock_music.mp3"
    for f in [mock_video, mock_music]:
        with open(f, "w") as fh:
            fh.write("mock data")

    # Mock Whisper JSON transcript
    mock_whisper = {
        "segments": [
            {
                "text": "This is an incredible technology demonstration",
                "start": 0.0,
                "end": 4.5,
                "words": [
                    {"word": "This", "start": 0.0, "end": 0.5},
                    {"word": "is", "start": 0.6, "end": 0.8},
                    {"word": "an", "start": 0.9, "end": 1.0},
                    {"word": "incredible", "start": 1.1, "end": 2.0},
                    {"word": "technology", "start": 2.1, "end": 3.0},
                    {"word": "demonstration", "start": 3.1, "end": 4.5},
                ]
            },
            {
                "text": "The REVOLUTION is here!",
                "start": 5.0,
                "end": 7.0,
                "words": [
                    {"word": "The", "start": 5.0, "end": 5.3},
                    {"word": "REVOLUTION", "start": 5.4, "end": 6.2},
                    {"word": "is", "start": 6.3, "end": 6.5},
                    {"word": "here!", "start": 6.6, "end": 7.0},
                ]
            },
            {
                "text": "Subscribe for more updates",
                "start": 8.0,
                "end": 10.0,
                "words": [
                    {"word": "Subscribe", "start": 8.0, "end": 8.8},
                    {"word": "for", "start": 8.9, "end": 9.1},
                    {"word": "more", "start": 9.2, "end": 9.5},
                    {"word": "updates", "start": 9.6, "end": 10.0},
                ]
            }
        ]
    }

    try:
        # ==============================================================
        # TEST 1: Tool Schema Structure
        # ==============================================================
        assert len(TOOL_SCHEMAS) == 22, f"Expected 22 tools, got {len(TOOL_SCHEMAS)}"

        for schema in TOOL_SCHEMAS:
            assert "type" in schema
            assert schema["type"] == "function"
            assert "function" in schema
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]
            assert schema["function"]["parameters"]["type"] == "object"

        print("\n[PASS] Tool schemas: all 22 schemas are structurally valid")

        # ==============================================================
        # TEST 2: Tool Names List
        # ==============================================================
        names = get_tool_names()
        core_names = [
            "import_asset", "add_cut_clip", "add_audio_clip",
            "adjust_color", "apply_lut", "set_volume", "audio_duck",
            "add_subtitle", "kinetic_zoom", "speed_ramp",
            "compile_blueprint", "generate_ffmpeg_command"
        ]
        for cn in core_names:
            assert cn in names, f"Missing core tool: {cn}"
        assert len(names) == 22, f"Expected 22 tool names, got {len(names)}"
        print("[PASS] Tool names: all 22 names present including 12 core")

        # ==============================================================
        # TEST 3: get_tool_schemas returns deep copy
        # ==============================================================
        copy1 = get_tool_schemas()
        copy1[0]["function"]["name"] = "MUTATED"
        assert TOOL_SCHEMAS[0]["function"]["name"] == "import_asset", \
            "get_tool_schemas should return a deep copy"
        print("[PASS] Tool schemas: deep copy isolation works")

        # ==============================================================
        # TEST 4: AgentExecutor — successful dispatch
        # ==============================================================
        executor = AgentExecutor()
        result = executor.dispatch({
            "name": "import_asset",
            "arguments": {"file_path": mock_video, "alias": "raw_vlog"}
        })
        assert result["status"] == "success"
        assert result["result"] == "raw_vlog"
        assert result["error"] is None
        print("[PASS] AgentExecutor: dispatch import_asset succeeds")

        # ==============================================================
        # TEST 5: AgentExecutor — dispatch with JSON string arguments
        # ==============================================================
        result = executor.dispatch({
            "name": "add_cut_clip",
            "arguments": json.dumps({
                "alias": "raw_vlog",
                "layer_index": 0,
                "timeline_start": 0.0,
                "src_in": 2.0,
                "src_out": 8.0
            })
        })
        assert result["status"] == "success"
        print("[PASS] AgentExecutor: dispatch with JSON string arguments")

        # ==============================================================
        # TEST 6: AgentExecutor — error handling (unknown tool)
        # ==============================================================
        result = executor.dispatch({
            "name": "nonexistent_tool",
            "arguments": {}
        })
        assert result["status"] == "error"
        assert "Unknown tool" in result["error"]
        print("[PASS] AgentExecutor: unknown tool returns clean error")

        # ==============================================================
        # TEST 7: AgentExecutor — error handling (bad arguments)
        # ==============================================================
        result = executor.dispatch({
            "name": "add_cut_clip",
            "arguments": {"alias": "nonexistent", "layer_index": 0,
                          "timeline_start": 0, "src_in": 0, "src_out": 5}
        })
        assert result["status"] == "error"
        assert "unregistered" in result["error"].lower()
        print("[PASS] AgentExecutor: validation error returns clean error")

        # ==============================================================
        # TEST 8: AgentExecutor — batch execution
        # ==============================================================
        executor.reset()
        results = executor.batch([
            {"name": "import_asset", "arguments": {"file_path": mock_video, "alias": "clip_a"}},
            {"name": "add_cut_clip", "arguments": {
                "alias": "clip_a", "layer_index": 0,
                "timeline_start": 0.0, "src_in": 1.0, "src_out": 5.0
            }},
            {"name": "adjust_color", "arguments": {"saturation": 1.3}},
            {"name": "add_subtitle", "arguments": {
                "text": "Hello!", "start_time": 1.0, "end_time": 3.0
            }},
        ])
        assert len(results) == 4
        assert all(r["status"] == "success" for r in results)
        print("[PASS] AgentExecutor: batch of 4 tool calls all succeed")

        # ==============================================================
        # TEST 9: AgentExecutor — batch fail-fast
        # ==============================================================
        executor.reset()
        results = executor.batch([
            {"name": "import_asset", "arguments": {"file_path": mock_video, "alias": "clip_b"}},
            {"name": "add_cut_clip", "arguments": {
                "alias": "NONEXISTENT", "layer_index": 0,
                "timeline_start": 0.0, "src_in": 1.0, "src_out": 5.0
            }},
            {"name": "adjust_color", "arguments": {"saturation": 1.3}},  # should not run
        ])
        assert len(results) == 2  # stopped after error
        assert results[0]["status"] == "success"
        assert results[1]["status"] == "error"
        print("[PASS] AgentExecutor: batch fail-fast stops on first error")

        # ==============================================================
        # TEST 10: AgentExecutor — execution history
        # ==============================================================
        history = executor.get_history()
        assert len(history) == 2
        assert history[0]["tool_name"] == "import_asset"
        assert history[1]["tool_name"] == "add_cut_clip"
        print("[PASS] AgentExecutor: execution history correctly logged")

        # ==============================================================
        # TEST 11: Whisper JSON parsing
        # ==============================================================
        segments = parse_whisper_json(mock_whisper)
        assert len(segments) == 3
        assert segments[0].text == "This is an incredible technology demonstration"
        assert len(segments[0].words) == 6
        assert segments[0].words[3].word == "incredible"
        assert segments[0].words[3].start == 1.1
        print("[PASS] Whisper parser: segments and word timestamps extracted")

        # ==============================================================
        # TEST 12: Emphasis word identification
        # ==============================================================
        emphasis = identify_emphasis_words(segments)
        # Should pick up: "incredible" (10 chars), "technology" (10 chars),
        # "demonstration" (13 chars), "REVOLUTION" (all caps), "Subscribe" (9 chars)
        assert len(emphasis) >= 2, f"Expected at least 2 emphasis words, got {len(emphasis)}"

        # Check that "REVOLUTION" was caught (all caps heuristic)
        rev_words = [w.word for w in emphasis]
        assert any("REVOLUTION" in w for w in rev_words), \
            f"Expected REVOLUTION in emphasis, got {rev_words}"
        print(f"[PASS] Emphasis detection: found {len(emphasis)} words: {rev_words}")

        # ==============================================================
        # TEST 13: Emphasis with custom keywords
        # ==============================================================
        custom = identify_emphasis_words(segments, emphasis_keywords=["subscribe", "here"])
        custom_words = [w.word for w in custom]
        assert len(custom) >= 1
        print(f"[PASS] Emphasis custom keywords: found {custom_words}")

        # ==============================================================
        # TEST 14: Speech segment computation
        # ==============================================================
        silence_regions = [
            SilenceRegion(start=3.0, end=5.0, duration=2.0),
            SilenceRegion(start=8.0, end=9.0, duration=1.0),
        ]
        speech = compute_speech_segments(12.0, silence_regions, padding=0.05)
        assert len(speech) == 3  # 0-2.95, 5.05-7.95, 9.05-12.0
        assert speech[0][0] == 0.0
        assert abs(speech[0][1] - 2.95) < 0.01
        print(f"[PASS] Speech segments: {len(speech)} segments computed from silence gaps")

        # ==============================================================
        # TEST 15: JumpCutPipeline -- initialization
        # ==============================================================
        pipeline = JumpCutPipeline(mock_video, resolution="1920x1080", fps=30)
        assert pipeline.source_video == os.path.abspath(mock_video)
        assert "main_footage" in pipeline.engine.state["assets"]
        print("[PASS] JumpCutPipeline: initialized with source asset")

        # ==============================================================
        # TEST 16: Pipeline — load transcript and inject zooms
        # ==============================================================
        pipeline.load_transcript(whisper_json_data=mock_whisper)
        assert len(pipeline.transcript_segments) == 3
        print("[PASS] Pipeline: transcript loaded")

        zoomed = pipeline.inject_zoom_accents(max_accents=5, zoom_scale=1.3)
        assert len(zoomed) >= 2
        assert len(pipeline.engine.state["filters"]["zoom"]) == len(zoomed)
        print(f"[PASS] Pipeline: {len(zoomed)} zoom accents injected")

        # ==============================================================
        # TEST 17: Pipeline — burn subtitles
        # ==============================================================
        sub_count = pipeline.burn_subtitles(fontsize=52)
        assert sub_count == 3
        assert len(pipeline.engine.state["timeline"]["text_layers"]) == 3
        print(f"[PASS] Pipeline: {sub_count} subtitle segments burned")

        # ==============================================================
        # TEST 18: Pipeline — color grade
        # ==============================================================
        pipeline.apply_color_grade(saturation=1.15, contrast=1.05)
        assert len(pipeline.engine.state["filters"]["color"]) == 1
        print("[PASS] Pipeline: color grade applied")

        # ==============================================================
        # TEST 19: Pipeline — summary
        # ==============================================================
        summary = pipeline.get_summary()
        assert summary["transcript_segments"] == 3
        assert summary["emphasis_zooms"] >= 2
        assert summary["text_overlays"] == 3
        assert summary["filters_active"] is True
        print(f"[PASS] Pipeline summary: {json.dumps(summary, indent=2)}")

        # ==============================================================
        # TEST 20: Pipeline — blueprint serialization
        # ==============================================================
        blueprint = json.loads(pipeline.get_blueprint())
        assert "filters" in blueprint
        assert "timeline" in blueprint
        assert len(blueprint["timeline"]["text_layers"]) == 3
        print("[PASS] Pipeline: full blueprint serializes correctly")

        # ==============================================================
        print("\n" + "=" * 60)
        print("  ALL 20 TESTS PASSED SUCCESSFULLY")
        print("=" * 60)

    finally:
        for f in [mock_video, mock_music]:
            if os.path.exists(f):
                os.remove(f)


if __name__ == "__main__":
    run_tests()
