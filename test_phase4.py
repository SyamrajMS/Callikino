"""
Phase 4 Test Suite — Social Media Editing Features (10 New Tools)
Tests: add_transition, crop_resize, add_overlay, audio_fade,
       add_pip, apply_blur, rotate_flip, reverse_clip, chroma_key, audio_normalize
"""

import os
import sys
import json
import tempfile

# Ensure root is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import CallikinoEngine
from tool_schemas import TOOL_SCHEMAS, get_tool_names
from agent_executor import AgentExecutor


def run_tests():
    print("=" * 60)
    print("  CALLIKINO -- PHASE 4 SOCIAL MEDIA FEATURES TEST SUITE")
    print("=" * 60)
    print()

    # Create mock files for tests requiring file existence
    mock_video = os.path.join(os.path.dirname(__file__), "mock_footage.mp4")
    mock_image = os.path.join(os.path.dirname(__file__), "mock_logo.png")
    if not os.path.exists(mock_video):
        with open(mock_video, "w") as f:
            f.write("mock")
    if not os.path.exists(mock_image):
        with open(mock_image, "w") as f:
            f.write("mock_png")

    # =============================================================
    # TEST 1: add_transition — valid params
    # =============================================================
    engine = CallikinoEngine()
    engine.add_transition(transition_type="fade", duration=1.5, offset=5.0)
    assert len(engine.state["filters"]["transition"]) == 1
    t = engine.state["filters"]["transition"][0]
    assert t["type"] == "xfade"
    assert t["transition"] == "fade"
    assert t["duration"] == 1.5
    assert t["offset"] == 5.0
    print("[PASS] add_transition: fade transition stored correctly")

    # TEST 1b: add_transition — multiple types
    engine.add_transition(transition_type="dissolve", duration=0.5)
    engine.add_transition(transition_type="wipeleft", duration=2.0)
    assert len(engine.state["filters"]["transition"]) == 3
    print("[PASS] add_transition: multiple transitions accumulated")

    # TEST 1c: add_transition — validation
    try:
        engine.add_transition(transition_type="invalid_type")
        assert False, "Should have raised"
    except ValueError:
        pass
    try:
        engine.add_transition(duration=10.0)
        assert False, "Should have raised"
    except ValueError:
        pass
    print("[PASS] add_transition: validation rejects bad inputs")

    # =============================================================
    # TEST 2: crop_resize — aspect ratio conversion
    # =============================================================
    engine = CallikinoEngine()
    engine.crop_resize(aspect_ratio="9:16")
    assert len(engine.state["filters"]["overlay"]) == 1
    cr = engine.state["filters"]["overlay"][0]
    assert cr["type"] == "crop_resize"
    assert cr["aspect_ratio"] == "9:16"
    print("[PASS] crop_resize: aspect ratio 9:16 stored")

    # TEST 2b: crop_resize — manual crop
    engine2 = CallikinoEngine()
    engine2.crop_resize(crop_x=100, crop_y=50, crop_w=1280, crop_h=720,
                        target_width=1080, target_height=1920)
    cr2 = engine2.state["filters"]["overlay"][0]
    assert cr2["crop_x"] == 100
    assert cr2["target_width"] == 1080
    print("[PASS] crop_resize: manual crop dimensions stored")

    # TEST 2c: crop_resize — validation
    try:
        engine.crop_resize(crop_x=-1)
        assert False, "Should have raised"
    except ValueError:
        pass
    try:
        engine.crop_resize(aspect_ratio="bad")
        assert False, "Should have raised"
    except ValueError:
        pass
    print("[PASS] crop_resize: validation rejects bad inputs")

    # =============================================================
    # TEST 3: add_overlay — logo watermark
    # =============================================================
    engine = CallikinoEngine()
    engine.import_asset(mock_image, "logo")
    engine.add_overlay("logo", x="W-w-20", y="H-h-20", opacity=0.8,
                       start_time=0.0, end_time=30.0)
    ovl = engine.state["filters"]["overlay"][0]
    assert ovl["type"] == "overlay"
    assert ovl["image_alias"] == "logo"
    assert ovl["opacity"] == 0.8
    print("[PASS] add_overlay: logo overlay stored with opacity")

    # TEST 3b: add_overlay — validation
    try:
        engine.add_overlay("nonexistent")
        assert False, "Should have raised"
    except ValueError:
        pass
    try:
        engine.add_overlay("logo", opacity=1.5)
        assert False, "Should have raised"
    except ValueError:
        pass
    print("[PASS] add_overlay: validation rejects bad inputs")

    # =============================================================
    # TEST 4: audio_fade — in/out
    # =============================================================
    engine = CallikinoEngine()
    engine.audio_fade(fade_type="in", start_time=0.0, duration=3.0)
    engine.audio_fade(fade_type="out", start_time=25.0, duration=2.0)
    assert len(engine.state["filters"]["audio_fade"]) == 2
    af_in = engine.state["filters"]["audio_fade"][0]
    af_out = engine.state["filters"]["audio_fade"][1]
    assert af_in["fade_type"] == "in"
    assert af_out["fade_type"] == "out"
    assert af_out["start_time"] == 25.0
    print("[PASS] audio_fade: in/out fades stored correctly")

    # TEST 4b: audio_fade — validation
    try:
        engine.audio_fade(fade_type="sideways")
        assert False, "Should have raised"
    except ValueError:
        pass
    try:
        engine.audio_fade(duration=50.0)
        assert False, "Should have raised"
    except ValueError:
        pass
    print("[PASS] audio_fade: validation rejects bad inputs")

    # =============================================================
    # TEST 5: add_pip — picture-in-picture
    # =============================================================
    engine = CallikinoEngine()
    engine.import_asset(mock_video, "webcam")
    engine.add_pip("webcam", x="W-w-20", y="H-h-20", scale=0.3,
                   start_time=5.0, end_time=60.0, border_width=2)
    pip = engine.state["filters"]["overlay"][0]
    assert pip["type"] == "pip"
    assert pip["pip_alias"] == "webcam"
    assert pip["scale"] == 0.3
    assert pip["border_width"] == 2
    print("[PASS] add_pip: PiP overlay stored with scale and border")

    # TEST 5b: add_pip — validation
    try:
        engine.add_pip("nonexistent")
        assert False, "Should have raised"
    except ValueError:
        pass
    try:
        engine.add_pip("webcam", scale=5.0)
        assert False, "Should have raised"
    except ValueError:
        pass
    print("[PASS] add_pip: validation rejects bad inputs")

    # =============================================================
    # TEST 6: apply_blur — gaussian and box
    # =============================================================
    engine = CallikinoEngine()
    engine.apply_blur(blur_type="gaussian", strength=10.0)
    engine.apply_blur(blur_type="box", strength=5.0,
                      start_time=3.0, end_time=8.0)
    assert len(engine.state["filters"]["blur"]) == 2
    b1 = engine.state["filters"]["blur"][0]
    b2 = engine.state["filters"]["blur"][1]
    assert b1["blur_type"] == "gaussian"
    assert b2["start_time"] == 3.0
    print("[PASS] apply_blur: gaussian and timed box blur stored")

    # TEST 6b: apply_blur — validation
    try:
        engine.apply_blur(blur_type="motion")
        assert False, "Should have raised"
    except ValueError:
        pass
    try:
        engine.apply_blur(strength=0.0)
        assert False, "Should have raised"
    except ValueError:
        pass
    print("[PASS] apply_blur: validation rejects bad inputs")

    # =============================================================
    # TEST 7: rotate_flip — all actions
    # =============================================================
    for action in ["hflip", "vflip", "cw", "ccw", "cw_flip", "ccw_flip", "180"]:
        engine = CallikinoEngine()
        engine.rotate_flip(action=action)
        tf = engine.state["filters"]["transform"][0]
        assert tf["type"] == "transform"
        assert tf["action"] == action
    print("[PASS] rotate_flip: all 7 transform actions work")

    # TEST 7b: rotate_flip — validation
    try:
        engine.rotate_flip(action="spin")
        assert False, "Should have raised"
    except ValueError:
        pass
    print("[PASS] rotate_flip: validation rejects invalid actions")

    # =============================================================
    # TEST 8: reverse_clip
    # =============================================================
    engine = CallikinoEngine()
    engine.reverse_clip(reverse_audio=True)
    rv = engine.state["filters"]["transform"][0]
    assert rv["type"] == "reverse"
    assert rv["reverse_audio"] is True
    print("[PASS] reverse_clip: reverse with audio stored")

    engine2 = CallikinoEngine()
    engine2.reverse_clip(reverse_audio=False)
    rv2 = engine2.state["filters"]["transform"][0]
    assert rv2["reverse_audio"] is False
    print("[PASS] reverse_clip: reverse without audio stored")

    # =============================================================
    # TEST 9: chroma_key — green screen
    # =============================================================
    engine = CallikinoEngine()
    engine.chroma_key(color="0x00FF00", similarity=0.3, blend=0.1)
    ck = engine.state["filters"]["chromakey"][0]
    assert ck["type"] == "chromakey"
    assert ck["color"] == "0x00FF00"
    assert ck["similarity"] == 0.3
    print("[PASS] chroma_key: green screen config stored")

    # TEST 9b: chroma_key — with background alias
    engine.import_asset(mock_video, "bg_beach")
    engine.chroma_key(color="0x0000FF", bg_alias="bg_beach")
    ck2 = engine.state["filters"]["chromakey"][1]
    assert ck2["bg_alias"] == "bg_beach"
    print("[PASS] chroma_key: background alias reference stored")

    # TEST 9c: chroma_key — validation
    try:
        engine.chroma_key(similarity=2.0)
        assert False, "Should have raised"
    except ValueError:
        pass
    try:
        engine.chroma_key(bg_alias="nonexistent")
        assert False, "Should have raised"
    except ValueError:
        pass
    print("[PASS] chroma_key: validation rejects bad inputs")

    # =============================================================
    # TEST 10: audio_normalize
    # =============================================================
    engine = CallikinoEngine()
    engine.audio_normalize(target_loudness=-14.0, true_peak=-1.0, loudness_range=7.0)
    nm = engine.state["filters"]["loudnorm"][0]
    assert nm["type"] == "loudnorm"
    assert nm["target_loudness"] == -14.0
    assert nm["true_peak"] == -1.0
    assert nm["loudness_range"] == 7.0
    print("[PASS] audio_normalize: loudnorm config stored")

    # TEST 10b: audio_normalize — validation
    try:
        engine.audio_normalize(target_loudness=0.0)
        assert False, "Should have raised"
    except ValueError:
        pass
    try:
        engine.audio_normalize(true_peak=5.0)
        assert False, "Should have raised"
    except ValueError:
        pass
    print("[PASS] audio_normalize: validation rejects bad inputs")

    # =============================================================
    # TEST 11: Filter chain compiler — new filters compile correctly
    # =============================================================
    engine = CallikinoEngine()
    engine.import_asset(mock_video, "main")
    engine.add_cut_clip("main", 0, 0.0, 0.0, 10.0)

    engine.apply_blur(blur_type="gaussian", strength=8.0)
    engine.rotate_flip(action="hflip")
    engine.reverse_clip()
    engine.chroma_key(color="0x00FF00", similarity=0.25)
    engine.audio_fade(fade_type="in", duration=2.0)
    engine.audio_normalize(target_loudness=-14.0)

    cmd = engine.generate_ffmpeg_command("test_output.mp4")
    assert "gblur=sigma=8.0" in cmd
    assert "hflip" in cmd
    assert "reverse" in cmd
    assert "chromakey" in cmd
    assert "afade=t=in" in cmd
    assert "loudnorm" in cmd
    assert "areverse" in cmd
    print("[PASS] Compiler: all new filters compile into FFmpeg command")

    # =============================================================
    # TEST 12: _has_filters detects new filter types
    # =============================================================
    engine = CallikinoEngine()
    assert engine._has_filters() is False

    engine.apply_blur(strength=5.0)
    assert engine._has_filters() is True
    print("[PASS] _has_filters: detects blur filter")

    engine2 = CallikinoEngine()
    engine2.audio_fade()
    assert engine2._has_filters() is True
    print("[PASS] _has_filters: detects audio_fade filter")

    engine3 = CallikinoEngine()
    engine3.add_transition()
    assert engine3._has_filters() is True
    print("[PASS] _has_filters: detects transition filter")

    # =============================================================
    # TEST 13: Tool schemas — 22 total schemas valid
    # =============================================================
    assert len(TOOL_SCHEMAS) == 22, f"Expected 22 schemas, got {len(TOOL_SCHEMAS)}"
    names = get_tool_names()
    new_tools = [
        "add_transition", "crop_resize", "add_overlay", "audio_fade",
        "add_pip", "apply_blur", "rotate_flip", "reverse_clip",
        "chroma_key", "audio_normalize"
    ]
    for tool in new_tools:
        assert tool in names, f"Missing tool schema: {tool}"
    print(f"[PASS] Tool schemas: all 22 schemas present ({len(new_tools)} new)")

    # =============================================================
    # TEST 14: AgentExecutor dispatches new tools
    # =============================================================
    engine = CallikinoEngine()
    engine.import_asset(mock_video, "vid")
    engine.import_asset(mock_image, "img")
    executor = AgentExecutor(engine)

    r1 = executor.dispatch({"name": "add_transition",
                            "arguments": {"transition_type": "dissolve", "duration": 1.0}})
    assert r1["status"] == "success"

    r2 = executor.dispatch({"name": "audio_fade",
                            "arguments": {"fade_type": "out", "start_time": 10.0, "duration": 3.0}})
    assert r2["status"] == "success"

    r3 = executor.dispatch({"name": "apply_blur",
                            "arguments": {"strength": 15.0}})
    assert r3["status"] == "success"

    r4 = executor.dispatch({"name": "rotate_flip",
                            "arguments": {"action": "cw"}})
    assert r4["status"] == "success"

    r5 = executor.dispatch({"name": "reverse_clip",
                            "arguments": {}})
    assert r5["status"] == "success"

    r6 = executor.dispatch({"name": "chroma_key",
                            "arguments": {"color": "0x00FF00"}})
    assert r6["status"] == "success"

    r7 = executor.dispatch({"name": "audio_normalize",
                            "arguments": {"target_loudness": -14.0}})
    assert r7["status"] == "success"

    r8 = executor.dispatch({"name": "add_overlay",
                            "arguments": {"image_alias": "img"}})
    assert r8["status"] == "success"

    r9 = executor.dispatch({"name": "add_pip",
                            "arguments": {"pip_alias": "vid"}})
    assert r9["status"] == "success"

    r10 = executor.dispatch({"name": "crop_resize",
                             "arguments": {"aspect_ratio": "1:1"}})
    assert r10["status"] == "success"

    print("[PASS] AgentExecutor: all 10 new tools dispatch successfully")

    # =============================================================
    # TEST 15: Blueprint serializes all new state
    # =============================================================
    bp = json.loads(engine.compile_blueprint())
    assert "transition" in bp["filters"]
    assert "overlay" in bp["filters"]
    assert "blur" in bp["filters"]
    assert "transform" in bp["filters"]
    assert "chromakey" in bp["filters"]
    assert "audio_fade" in bp["filters"]
    assert "loudnorm" in bp["filters"]
    assert len(bp["filters"]["transition"]) == 1
    assert len(bp["filters"]["blur"]) == 1
    assert len(bp["filters"]["chromakey"]) == 1
    print("[PASS] Blueprint: all new filter state serializes correctly")

    # =============================================================
    # BACKWARD COMPATIBILITY — run old assertions
    # =============================================================
    engine = CallikinoEngine()
    assert engine.state["meta"]["resolution"] == "1920x1080"
    assert engine.state["meta"]["fps"] == 30
    assert len(engine.state["timeline"]["video_layers"]) == 0
    assert len(engine.state["filters"]["color"]) == 0
    assert len(engine.state["filters"]["zoom"]) == 0
    print("[PASS] Backward compatibility: original state structure intact")

    print()
    print("=" * 60)
    print("  ALL PHASE 4 TESTS PASSED SUCCESSFULLY")
    print("=" * 60)

    # Cleanup mock logo
    if os.path.exists(mock_image):
        os.remove(mock_image)


if __name__ == "__main__":
    run_tests()
