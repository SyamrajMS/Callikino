import os
import json
from core import CallikinoEngine


def run_tests():
    print("=" * 60)
    print("  CALLIKINO -- PHASE 2 TOOL ABSTRACTIONS TEST SUITE")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    mock_video = "mock_footage.mp4"
    mock_music = "mock_music.mp3"
    mock_voice = "mock_voice.wav"
    mock_lut = "cinematic.cube"

    for f in [mock_video, mock_music, mock_voice]:
        with open(f, "w") as fh:
            fh.write("mock data")

    # Create a fake .cube LUT file (minimal valid header)
    with open(mock_lut, "w") as fh:
        fh.write("LUT_3D_SIZE 2\n0 0 0\n1 0 0\n0 1 0\n1 1 0\n0 0 1\n1 0 1\n0 1 1\n1 1 1\n")

    try:
        engine = CallikinoEngine(resolution="1920x1080", fps=30)

        # Import all assets
        engine.import_asset(mock_video, "raw_vlog")
        engine.import_asset(mock_music, "bgm")
        engine.import_asset(mock_voice, "voiceover")

        # ==============================================================
        # TEST 1: adjust_color — valid input
        # ==============================================================
        engine.adjust_color(saturation=1.3, contrast=1.1, brightness=0.05, gamma=1.2)
        assert len(engine.state["filters"]["color"]) == 1
        cf = engine.state["filters"]["color"][0]
        assert cf["saturation"] == 1.3
        assert cf["contrast"] == 1.1
        assert cf["brightness"] == 0.05
        assert cf["gamma"] == 1.2
        print("\n[PASS] adjust_color: valid parameters stored in state")

        # TEST 1b: adjust_color — validation errors
        try:
            engine.adjust_color(saturation=5.0)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        try:
            engine.adjust_color(brightness=2.0)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        print("[PASS] adjust_color: validation rejects out-of-range values")

        # ==============================================================
        # TEST 2: apply_lut — valid .cube file
        # ==============================================================
        engine.apply_lut(mock_lut)
        assert len(engine.state["filters"]["lut"]) == 1
        assert engine.state["filters"]["lut"][0]["path"] == os.path.abspath(mock_lut)
        print("[PASS] apply_lut: .cube LUT path registered")

        # TEST 2b: apply_lut — validation errors
        try:
            engine.apply_lut("nonexistent.cube")
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            pass
        try:
            engine.apply_lut(mock_video)  # not a .cube file
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        print("[PASS] apply_lut: validation rejects bad paths and extensions")

        # ==============================================================
        # TEST 3: add_audio_clip
        # ==============================================================
        engine.add_audio_clip("bgm", timeline_start=0.0, src_in=0.0, src_out=30.0)
        assert len(engine.state["timeline"]["audio_layers"]) == 1
        al = engine.state["timeline"]["audio_layers"][0]
        assert al["asset_alias"] == "bgm"
        assert al["duration"] == 30.0
        print("[PASS] add_audio_clip: audio layer appended to state")

        # TEST 3b: validation
        try:
            engine.add_audio_clip("nonexistent", 0.0, 0.0, 10.0)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        try:
            engine.add_audio_clip("bgm", 0.0, 10.0, 5.0)  # src_out < src_in
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        print("[PASS] add_audio_clip: validation catches invalid params")

        # ==============================================================
        # TEST 4: set_volume
        # ==============================================================
        engine.set_volume("bgm", level_db=-6.0)
        assert len(engine.state["filters"]["volume"]) == 1
        assert engine.state["filters"]["volume"][0]["level_db"] == -6.0
        print("[PASS] set_volume: volume filter stored in state")

        # TEST 4b: validation
        try:
            engine.set_volume("bgm", level_db=50.0)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        print("[PASS] set_volume: validation rejects out-of-range dB")

        # ==============================================================
        # TEST 5: audio_duck
        # ==============================================================
        engine.audio_duck("bgm", "voiceover", duck_db=-14.0, threshold=0.02)
        assert len(engine.state["filters"]["audio_duck"]) == 1
        duck = engine.state["filters"]["audio_duck"][0]
        assert duck["music_alias"] == "bgm"
        assert duck["voice_alias"] == "voiceover"
        assert duck["duck_db"] == -14.0
        print("[PASS] audio_duck: sidechain config stored in state")

        # TEST 5b: validation
        try:
            engine.audio_duck("nonexistent", "voiceover")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        try:
            engine.audio_duck("bgm", "voiceover", duck_db=5.0)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        print("[PASS] audio_duck: validation catches invalid params")

        # ==============================================================
        # TEST 6: add_subtitle
        # ==============================================================
        engine.add_subtitle("Hello World!", start_time=2.0, end_time=5.0, fontsize=64)
        assert len(engine.state["timeline"]["text_layers"]) == 1
        tl = engine.state["timeline"]["text_layers"][0]
        assert tl["text"] == "Hello World!"
        assert tl["start_time"] == 2.0
        assert tl["end_time"] == 5.0
        assert tl["fontsize"] == 64
        print("[PASS] add_subtitle: text layer appended to state")

        # TEST 6b: validation
        try:
            engine.add_subtitle("", 0.0, 5.0)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        try:
            engine.add_subtitle("Test", 5.0, 2.0)  # end < start
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        print("[PASS] add_subtitle: validation catches empty text and bad times")

        # ==============================================================
        # TEST 7: kinetic_zoom
        # ==============================================================
        engine.kinetic_zoom(start_time=4.0, end_time=6.0, scale=1.3)
        assert len(engine.state["filters"]["zoom"]) == 1
        zf = engine.state["filters"]["zoom"][0]
        assert zf["scale"] == 1.3
        assert zf["duration_frames"] == int((6.0 - 4.0) * 30)
        print("[PASS] kinetic_zoom: zoom filter stored with correct frame count")

        # TEST 7b: validation
        try:
            engine.kinetic_zoom(0.0, 5.0, scale=5.0)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        print("[PASS] kinetic_zoom: validation rejects out-of-range scale")

        # ==============================================================
        # TEST 8: speed_ramp
        # ==============================================================
        engine.speed_ramp("raw_vlog", speed_factor=2.0)
        assert len(engine.state["filters"]["speed"]) == 1
        sf = engine.state["filters"]["speed"][0]
        assert sf["speed_factor"] == 2.0
        assert sf["asset_alias"] == "raw_vlog"
        print("[PASS] speed_ramp: speed filter stored in state")

        # TEST 8b: validation
        try:
            engine.speed_ramp("raw_vlog", speed_factor=10.0)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        try:
            engine.speed_ramp("nonexistent", speed_factor=1.5)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        print("[PASS] speed_ramp: validation catches bad values")

        # ==============================================================
        # TEST 9: _has_filters reflects active state
        # ==============================================================
        assert engine._has_filters() is True
        empty_engine = CallikinoEngine()
        assert empty_engine._has_filters() is False
        print("[PASS] _has_filters: correctly reports filter presence")

        # ==============================================================
        # TEST 10: _needs_reencoding with filters active
        # ==============================================================
        filter_engine = CallikinoEngine()
        filter_engine.import_asset(mock_video, "clip")
        filter_engine.add_cut_clip("clip", 0, 0.0, 1.0, 5.0)
        assert filter_engine._needs_reencoding() is False  # single clip, no filters

        filter_engine.adjust_color(saturation=1.5)
        assert filter_engine._needs_reencoding() is True  # now has filters
        print("[PASS] _needs_reencoding: filters trigger re-encode path")

        # ==============================================================
        # TEST 11: Full compile with filters produces valid filter_complex
        # ==============================================================
        engine.add_cut_clip("raw_vlog", 0, 0.0, 5.0, 12.0)
        engine.add_cut_clip("raw_vlog", 0, 7.0, 20.0, 25.0)

        cmd = engine.generate_ffmpeg_command("output_full.mp4")

        assert "-filter_complex" in cmd
        assert "eq=" in cmd, "Color grading filter missing from command"
        assert "lut3d=" in cmd, "LUT filter missing from command"
        assert "drawtext=" in cmd, "Text overlay filter missing from command"
        assert "setpts=" in cmd, "Speed ramp filter missing from command"
        assert f"-c:v {engine.encoder}" in cmd
        assert "-c:a aac" in cmd
        print("[PASS] generate_ffmpeg_command: full pipeline with all filters compiled")

        # ==============================================================
        # TEST 12: Blueprint serialization includes new structures
        # ==============================================================
        blueprint = json.loads(engine.compile_blueprint())
        assert "filters" in blueprint
        assert len(blueprint["filters"]["color"]) == 1
        assert len(blueprint["filters"]["lut"]) == 1
        assert len(blueprint["filters"]["volume"]) == 1
        assert len(blueprint["filters"]["audio_duck"]) == 1
        assert len(blueprint["filters"]["zoom"]) == 1
        assert len(blueprint["filters"]["speed"]) == 1
        assert len(blueprint["timeline"]["text_layers"]) == 1
        assert len(blueprint["timeline"]["audio_layers"]) == 1
        print("[PASS] compile_blueprint: all new state structures serialize correctly")

        # ==============================================================
        # TEST 13: Original test_setup checks still pass
        # ==============================================================
        fresh = CallikinoEngine(resolution="1920x1080", fps=30)
        fresh.import_asset(mock_video, "raw_vlog")
        assert "raw_vlog" in fresh.state["assets"]
        fresh.add_cut_clip("raw_vlog", 0, 0.0, 5.5, 12.0)
        fresh.add_cut_clip("raw_vlog", 0, 6.5, 20.0, 25.5)
        assert len(fresh.state["timeline"]["video_layers"]) == 2
        assert fresh.state["timeline"]["video_layers"][0]["duration"] == 6.5
        assert fresh.state["timeline"]["video_layers"][1]["duration"] == 5.5
        print("[PASS] Backward compatibility: original Week 1 assertions hold")

        # ==============================================================
        print("\n" + "=" * 60)
        print("  ALL 13 TESTS PASSED SUCCESSFULLY")
        print("=" * 60)

    finally:
        for f in [mock_video, mock_music, mock_voice, mock_lut]:
            if os.path.exists(f):
                os.remove(f)


if __name__ == "__main__":
    run_tests()
