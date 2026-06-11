import os
from core import CallikinoEngine


def run_tests():
    print("=" * 60)
    print("  CALLIKINO — COMPILER & HARDWARE DETECTION TESTS")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Setup: create a mock media file for path validation
    # ------------------------------------------------------------------
    mock_file = "mock_footage.mp4"
    with open(mock_file, "w") as f:
        f.write("mock data")

    try:
        # ==============================================================
        # TEST 1: Hardware detection produces valid encoder config
        # ==============================================================
        engine = CallikinoEngine(resolution="1920x1080", fps=30)

        assert engine.encoder is not None, "Encoder must not be None"
        assert engine.encoder in (
            "libx264", "h264_nvenc", "h264_videotoolbox", "h264_qsv"
        ), f"Unexpected encoder: {engine.encoder}"

        print(f"\n[PASS] Hardware Detection")
        print(f"       Encoder : {engine.encoder}")
        print(f"       HWAccel : {engine.hwaccel or 'None (CPU-only)'}")
        print(f"       GPU     : {engine.gpu_name or 'Not detected'}")

        # Verify state meta stores hardware info
        assert engine.state["meta"]["encoder"] == engine.encoder
        assert engine.state["meta"]["hwaccel"] == engine.hwaccel
        assert engine.state["meta"]["gpu_name"] == engine.gpu_name
        print("[PASS] Hardware info recorded in state meta")

        # ==============================================================
        # TEST 2: Single-clip stream-copy command
        # ==============================================================
        engine.import_asset(mock_file, "raw_vlog")
        engine.add_cut_clip("raw_vlog", layer_index=0,
                            timeline_start=0.0, src_in=5.5, src_out=12.0)

        cmd_single = engine.generate_ffmpeg_command("output_single.mp4")

        # Should use -c copy (stream copy) for a single clip
        assert "-c copy" in cmd_single, \
            f"Single clip should use stream copy, got: {cmd_single}"
        assert "-ss 5.5" in cmd_single
        assert "-t 6.5" in cmd_single
        assert "output_single.mp4" in cmd_single

        print(f"\n[PASS] Single-clip stream-copy command generated")
        print(f"       CMD: {cmd_single}")

        # ==============================================================
        # TEST 3: Multi-clip re-encode command with filter_complex
        # ==============================================================
        engine.add_cut_clip("raw_vlog", layer_index=0,
                            timeline_start=6.5, src_in=20.0, src_out=25.5)

        cmd_multi = engine.generate_ffmpeg_command("output_multi.mp4")

        # Multi-clip should use filter_complex with concat
        assert "-filter_complex" in cmd_multi, \
            f"Multi-clip should use filter_complex, got: {cmd_multi}"
        assert "concat=n=2" in cmd_multi
        assert f"-c:v {engine.encoder}" in cmd_multi
        assert "output_multi.mp4" in cmd_multi

        print(f"\n[PASS] Multi-clip re-encode command generated")
        print(f"       CMD: {cmd_multi}")

        # ==============================================================
        # TEST 4: Empty timeline raises ValueError
        # ==============================================================
        empty_engine = CallikinoEngine()
        try:
            empty_engine.generate_ffmpeg_command("should_fail.mp4")
            assert False, "Should have raised ValueError for empty timeline"
        except ValueError as e:
            assert "no video layers" in str(e).lower()
            print(f"\n[PASS] Empty timeline correctly raises ValueError")

        # ==============================================================
        # TEST 5: _needs_reencoding heuristic
        # ==============================================================
        single_engine = CallikinoEngine()
        single_engine.import_asset(mock_file, "clip_a")
        single_engine.add_cut_clip("clip_a", 0, 0.0, 1.0, 5.0)

        assert single_engine._needs_reencoding() is False, \
            "Single clip without text should not need re-encoding"

        single_engine.add_cut_clip("clip_a", 0, 4.0, 10.0, 15.0)
        assert single_engine._needs_reencoding() is True, \
            "Multiple clips should need re-encoding"

        print("[PASS] _needs_reencoding heuristic works correctly")

        # ==============================================================
        print("\n" + "=" * 60)
        print("  ALL TESTS PASSED SUCCESSFULLY")
        print("=" * 60)

    finally:
        # Cleanup
        if os.path.exists(mock_file):
            os.remove(mock_file)


if __name__ == "__main__":
    run_tests()
