"""
Callikino CLI — Command-Line Interface
========================================
Usage:
    callikino init                          Create a new project blueprint
    callikino import <file> <alias>         Register a media asset
    callikino cut <alias> <start> <end>     Add a trim to the timeline
    callikino color --saturation 1.2        Apply color grading
    callikino subtitle <text> <start> <end> Add text overlay
    callikino zoom <start> <end> [--scale]  Add kinetic zoom
    callikino blueprint                     Print current project state as JSON
    callikino render <output>               Generate the FFmpeg command
    callikino run <output>                  Generate AND execute the FFmpeg command
    callikino tools                         Print all tool schemas for LLM agents
    callikino info                          Show detected hardware & engine config
"""

import argparse
import json
import os
import subprocess
import sys

from callikino import __version__
from callikino.core import CallikinoEngine
from callikino.tool_schemas import TOOL_SCHEMAS, get_tool_names


# ---------------------------------------------------------------------------
# State Persistence
# ---------------------------------------------------------------------------

STATE_FILE = "callikino_project.json"


def _load_engine() -> CallikinoEngine:
    """Load engine state from the project file, or create a new one."""
    engine = CallikinoEngine()
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            engine.state = json.load(f)
        # Restore instance attributes from loaded state
        meta = engine.state.get("meta", {})
        engine.resolution = meta.get("resolution", "1920x1080")
        engine.fps = meta.get("fps", 30)
        engine.encoder = meta.get("encoder", "libx264")
        engine.hwaccel = meta.get("hwaccel")
        engine.gpu_name = meta.get("gpu_name")
    return engine


def _save_engine(engine: CallikinoEngine) -> None:
    """Persist engine state to the project file."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(engine.compile_blueprint(pretty=True))


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------

def cmd_init(args):
    """Initialize a new Callikino project."""
    engine = CallikinoEngine(resolution=args.resolution, fps=args.fps)
    _save_engine(engine)
    print(f"[callikino] Project initialized: {args.resolution} @ {args.fps}fps")
    print(f"[callikino] Encoder: {engine.encoder} | HWAccel: {engine.hwaccel or 'CPU'}")
    print(f"[callikino] GPU: {engine.gpu_name or 'Not detected'}")
    print(f"[callikino] State saved to {STATE_FILE}")


def cmd_import(args):
    """Import a media asset."""
    engine = _load_engine()
    alias = engine.import_asset(args.file, args.alias)
    _save_engine(engine)
    print(f"[callikino] Imported '{args.file}' as '{alias}'")


def cmd_cut(args):
    """Add a video cut to the timeline."""
    engine = _load_engine()
    engine.add_cut_clip(
        alias=args.alias,
        layer_index=args.layer,
        timeline_start=args.timeline_start,
        src_in=args.start,
        src_out=args.end,
    )
    _save_engine(engine)
    duration = args.end - args.start
    print(f"[callikino] Cut added: '{args.alias}' [{args.start}s -> {args.end}s] ({duration:.1f}s)")


def cmd_color(args):
    """Apply color grading."""
    engine = _load_engine()
    engine.adjust_color(
        saturation=args.saturation,
        contrast=args.contrast,
        brightness=args.brightness,
        gamma=args.gamma,
    )
    _save_engine(engine)
    print(f"[callikino] Color grade applied: sat={args.saturation} con={args.contrast} "
          f"bri={args.brightness} gamma={args.gamma}")


def cmd_subtitle(args):
    """Add a text overlay."""
    engine = _load_engine()
    engine.add_subtitle(
        text=args.text,
        start_time=args.start,
        end_time=args.end,
        fontsize=args.fontsize,
        fontcolor=args.fontcolor,
    )
    _save_engine(engine)
    print(f"[callikino] Subtitle added: \"{args.text}\" [{args.start}s -> {args.end}s]")


def cmd_zoom(args):
    """Add a kinetic zoom effect."""
    engine = _load_engine()
    engine.kinetic_zoom(
        start_time=args.start,
        end_time=args.end,
        scale=args.scale,
    )
    _save_engine(engine)
    print(f"[callikino] Zoom added: [{args.start}s -> {args.end}s] scale={args.scale}")


def cmd_speed(args):
    """Apply speed ramp to a clip."""
    engine = _load_engine()
    engine.speed_ramp(alias=args.alias, speed_factor=args.factor)
    _save_engine(engine)
    print(f"[callikino] Speed ramp: '{args.alias}' x{args.factor}")


def cmd_volume(args):
    """Set audio volume."""
    engine = _load_engine()
    engine.set_volume(alias=args.alias, level_db=args.db)
    _save_engine(engine)
    print(f"[callikino] Volume set: '{args.alias}' {args.db:+.1f}dB")


def cmd_blueprint(args):
    """Print the current project state."""
    engine = _load_engine()
    print(engine.compile_blueprint(pretty=True))


def cmd_render(args):
    """Generate the FFmpeg command."""
    engine = _load_engine()
    cmd = engine.generate_ffmpeg_command(args.output)
    print(f"[callikino] FFmpeg command generated:\n")
    print(cmd)


def cmd_run(args):
    """Generate AND execute the FFmpeg command."""
    engine = _load_engine()
    cmd = engine.generate_ffmpeg_command(args.output)
    print(f"[callikino] Executing render pipeline...")
    print(f"[callikino] Command: {cmd}\n")

    result = subprocess.run(cmd, shell=True)
    if result.returncode == 0:
        print(f"\n[callikino] Render complete: {args.output}")
    else:
        print(f"\n[callikino] Render failed with exit code {result.returncode}")
        sys.exit(result.returncode)


def cmd_tools(args):
    """Print tool schemas for LLM agents."""
    if args.names_only:
        for name in get_tool_names():
            print(f"  - {name}")
    else:
        print(json.dumps(TOOL_SCHEMAS, indent=2))


def cmd_info(args):
    """Show hardware and engine info."""
    engine = _load_engine()
    meta = engine.state["meta"]
    print(f"  Callikino v{__version__}")
    print(f"  Resolution : {meta['resolution']}")
    print(f"  FPS        : {meta['fps']}")
    print(f"  Sample Rate: {meta['sample_rate']}")
    print(f"  Encoder    : {meta['encoder']}")
    print(f"  HW Accel   : {meta.get('hwaccel') or 'None (CPU)'}")
    print(f"  GPU        : {meta.get('gpu_name') or 'Not detected'}")
    print(f"  Assets     : {len(engine.state['assets'])}")
    print(f"  Video Clips: {len(engine.state['timeline']['video_layers'])}")
    print(f"  Audio Clips: {len(engine.state['timeline']['audio_layers'])}")
    print(f"  Text Layers: {len(engine.state['timeline']['text_layers'])}")


# ---------------------------------------------------------------------------
# Argument Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="callikino",
        description="Callikino - The Headless Video Editing Framework for AI Agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"callikino {__version__}")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- init ---
    p_init = subparsers.add_parser("init", help="Initialize a new project")
    p_init.add_argument("--resolution", default="1920x1080", help="Video resolution (default: 1920x1080)")
    p_init.add_argument("--fps", type=int, default=30, help="Frames per second (default: 30)")
    p_init.set_defaults(func=cmd_init)

    # --- import ---
    p_import = subparsers.add_parser("import", help="Import a media asset")
    p_import.add_argument("file", help="Path to media file")
    p_import.add_argument("alias", help="Unique alias for the asset")
    p_import.set_defaults(func=cmd_import)

    # --- cut ---
    p_cut = subparsers.add_parser("cut", help="Add a video cut to the timeline")
    p_cut.add_argument("alias", help="Asset alias")
    p_cut.add_argument("start", type=float, help="Source in-point (seconds)")
    p_cut.add_argument("end", type=float, help="Source out-point (seconds)")
    p_cut.add_argument("--layer", type=int, default=0, help="Video layer index (default: 0)")
    p_cut.add_argument("--timeline-start", type=float, default=0.0, help="Timeline position (seconds)")
    p_cut.set_defaults(func=cmd_cut)

    # --- color ---
    p_color = subparsers.add_parser("color", help="Apply color grading")
    p_color.add_argument("--saturation", type=float, default=1.0)
    p_color.add_argument("--contrast", type=float, default=1.0)
    p_color.add_argument("--brightness", type=float, default=0.0)
    p_color.add_argument("--gamma", type=float, default=1.0)
    p_color.set_defaults(func=cmd_color)

    # --- subtitle ---
    p_sub = subparsers.add_parser("subtitle", help="Add text overlay")
    p_sub.add_argument("text", help="Text to display")
    p_sub.add_argument("start", type=float, help="Start time (seconds)")
    p_sub.add_argument("end", type=float, help="End time (seconds)")
    p_sub.add_argument("--fontsize", type=int, default=48)
    p_sub.add_argument("--fontcolor", default="white")
    p_sub.set_defaults(func=cmd_subtitle)

    # --- zoom ---
    p_zoom = subparsers.add_parser("zoom", help="Add kinetic zoom")
    p_zoom.add_argument("start", type=float, help="Start time (seconds)")
    p_zoom.add_argument("end", type=float, help="End time (seconds)")
    p_zoom.add_argument("--scale", type=float, default=1.2, help="Zoom scale (default: 1.2)")
    p_zoom.set_defaults(func=cmd_zoom)

    # --- speed ---
    p_speed = subparsers.add_parser("speed", help="Apply speed ramp")
    p_speed.add_argument("alias", help="Asset alias")
    p_speed.add_argument("factor", type=float, help="Speed multiplier (0.25-4.0)")
    p_speed.set_defaults(func=cmd_speed)

    # --- volume ---
    p_vol = subparsers.add_parser("volume", help="Set audio volume")
    p_vol.add_argument("alias", help="Asset alias")
    p_vol.add_argument("db", type=float, help="Volume in dB (-60 to +24)")
    p_vol.set_defaults(func=cmd_volume)

    # --- blueprint ---
    p_bp = subparsers.add_parser("blueprint", help="Print project state as JSON")
    p_bp.set_defaults(func=cmd_blueprint)

    # --- render ---
    p_render = subparsers.add_parser("render", help="Generate FFmpeg command")
    p_render.add_argument("output", help="Output file path")
    p_render.set_defaults(func=cmd_render)

    # --- run ---
    p_run = subparsers.add_parser("run", help="Generate and execute FFmpeg command")
    p_run.add_argument("output", help="Output file path")
    p_run.set_defaults(func=cmd_run)

    # --- tools ---
    p_tools = subparsers.add_parser("tools", help="Print tool schemas for LLM agents")
    p_tools.add_argument("--names-only", action="store_true", help="List tool names only")
    p_tools.set_defaults(func=cmd_tools)

    # --- info ---
    p_info = subparsers.add_parser("info", help="Show engine configuration")
    p_info.set_defaults(func=cmd_info)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    try:
        args.func(args)
    except (FileNotFoundError, ValueError) as e:
        print(f"[callikino] Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[callikino] Unexpected error: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
