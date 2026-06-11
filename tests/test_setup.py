import os
from core import CallikinoEngine

def run_tests():
    # Setup mock file
    mock_file = "mock_footage.mp4"
    with open(mock_file, "w") as f:
        f.write("mock data")

    try:
        # Instantiate engine
        engine = CallikinoEngine(resolution="1920x1080", fps=30)

        # Import asset
        engine.import_asset(mock_file, "raw_vlog")

        # Assert asset mapping
        assert "raw_vlog" in engine.state["assets"]
        assert engine.state["assets"]["raw_vlog"] == os.path.abspath(mock_file)

        # Add clips
        engine.add_cut_clip("raw_vlog", layer_index=0, timeline_start=0.0, src_in=5.5, src_out=12.0)
        engine.add_cut_clip("raw_vlog", layer_index=0, timeline_start=6.5, src_in=20.0, src_out=25.5)

        # Compile
        json_output = engine.compile_blueprint()

        # Assertions
        video_layers = engine.state["timeline"]["video_layers"]
        assert len(video_layers) == 2
        assert video_layers[0]["duration"] == 12.0 - 5.5
        assert video_layers[1]["duration"] == 25.5 - 20.0

        print("All assertions passed successfully!")
        print("Final Blueprint Output:")
        print(json_output)

    finally:
        # Cleanup
        if os.path.exists(mock_file):
            os.remove(mock_file)

if __name__ == "__main__":
    run_tests()
