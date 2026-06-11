<p align="center">
  <h1 align="center">CALLIKINO</h1>
  <p align="center"><strong>The Headless Video Editing Framework for AI Agents</strong></p>
  <p align="center">
    <em>A Python DSL that compiles abstract editing operations into optimized, single-pass FFmpeg commands.</em>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue?style=flat-square" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/dependencies-zero-brightgreen?style=flat-square" alt="Zero Dependencies">
  <img src="https://img.shields.io/badge/ffmpeg-required-orange?style=flat-square" alt="FFmpeg Required">
  <img src="https://img.shields.io/badge/GPU-auto--detected-purple?style=flat-square" alt="GPU Auto-detect">
  <img src="https://img.shields.io/badge/MCP-compatible-blueviolet?style=flat-square" alt="MCP Compatible">
</p>

---

## What is Callikino?

Callikino is **not** another video editor. It's an **operational framework** — a Domain-Specific Language designed for AI agents to call via structured tool-use. Think of it as the FFmpeg compiler that sits between an LLM's reasoning and the actual render.

**Core Design Principle:** Every function call mutates an in-memory JSON state. Nothing touches the filesystem until you call `render`. This means an AI agent can plan, revise, and optimize an entire edit before a single FFmpeg process spawns.

```
LLM Agent ──> Tool Calls ──> CallikinoEngine (state mutations) ──> FFmpeg Command ──> Render
```

### Why Not Just Call FFmpeg Directly?

| Problem | Callikino Solution |
|---|---|
| FFmpeg's CLI syntax is arcane | Clean Python methods: `engine.add_cut_clip(...)` |
| Each operation spawns a subprocess | Zero subprocess calls until final render |
| No undo/preview | Full JSON state — inspect, rewind, branch |
| Hardware acceleration is manual | Auto-detected: NVIDIA, Apple Silicon, Intel QSV |
| Stream copy vs re-encode is error-prone | Automatic decision based on timeline analysis |
| Multi-clip concat requires filter_complex | Builder pattern generates optimal graphs |

---

## Installation

```bash
pip install callikino
```

> **Prerequisite:** [FFmpeg](https://ffmpeg.org/download.html) must be installed and on your `PATH`.

---

## Quick Start

### Python API

```python
from callikino import CallikinoEngine

engine = CallikinoEngine(resolution="1920x1080", fps=30)

# Import media
engine.import_asset("raw_vlog.mp4", "vlog")
engine.import_asset("bgm.mp3", "music")

# Build timeline
engine.add_cut_clip("vlog", layer_index=0, timeline_start=0, src_in=5.5, src_out=12.0)
engine.add_cut_clip("vlog", layer_index=0, timeline_start=6.5, src_in=20.0, src_out=25.5)

# Color grade
engine.adjust_color(saturation=1.2, contrast=1.05)

# Add text
engine.add_subtitle("Subscribe!", start_time=10.0, end_time=12.0, fontsize=64)

# Kinetic zoom on punchline
engine.kinetic_zoom(start_time=8.0, end_time=9.5, scale=1.3)

# Audio
engine.set_volume("music", level_db=-18.0)
engine.audio_duck("music", "vlog", duck_db=-14.0)

# Generate the single FFmpeg command
cmd = engine.generate_ffmpeg_command("output.mp4")
print(cmd)
```

### CLI

```bash
# Initialize a project
callikino init --resolution 1920x1080 --fps 30

# Import media
callikino import raw_vlog.mp4 vlog

# Build timeline
callikino cut vlog 5.5 12.0
callikino cut vlog 20.0 25.5 --timeline-start 6.5

# Add effects
callikino color --saturation 1.2 --contrast 1.05
callikino subtitle "Subscribe!" 10.0 12.0 --fontsize 64
callikino zoom 8.0 9.5 --scale 1.3

# Preview state
callikino blueprint

# Render
callikino render output.mp4  # Print FFmpeg command
callikino run output.mp4     # Execute it
```

---

## For AI Agents

### Tool-Calling Interface

Callikino ships with **12 pre-built function-calling schemas** compatible with OpenAI, Anthropic, and Gemini APIs:

```python
from callikino import TOOL_SCHEMAS, AgentExecutor

# Pass schemas to your LLM
response = openai_client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Cut out silence and add subtitles"}],
    tools=TOOL_SCHEMAS
)

# Route tool calls through the executor
executor = AgentExecutor()
for tool_call in response.choices[0].message.tool_calls:
    result = executor.dispatch({
        "name": tool_call.function.name,
        "arguments": tool_call.function.arguments
    })
    print(result)  # {"status": "success", "result": ..., "error": None}
```

### MCP Server

Connect Callikino to any MCP-compatible agent environment:

```json
{
  "mcpServers": {
    "callikino": {
      "command": "callikino-mcp",
      "args": []
    }
  }
}
```

Or run directly:

```bash
callikino-mcp
```

---

## Automated JumpCut Pipeline

A complete 5-layer automation pipeline for transforming raw talking-head footage into high-retention social media videos:

```python
from callikino.pipelines.jumpcut import JumpCutPipeline

pipeline = JumpCutPipeline("raw_footage.mp4")

# Layer 1: Strip silence (jump cuts)
pipeline.strip_silence(noise_db=-30, min_silence=0.5)

# Layer 2: Load Whisper transcript
pipeline.load_transcript(whisper_json_path="transcript.json")

# Layer 3: Auto-inject zoom on punchlines
pipeline.inject_zoom_accents(max_accents=8, zoom_scale=1.25)

# Layer 4: Burn subtitles
pipeline.burn_subtitles(fontsize=52, fontcolor="white")

# Layer 5: Color grade + BGM
pipeline.apply_color_grade(saturation=1.15, contrast=1.05)
pipeline.add_background_music("lofi_beat.mp3", volume_db=-18, duck_db=-14)

# Compile final command
cmd = pipeline.generate_render_command("final_output.mp4")
print(pipeline.get_summary())
```

---

## Available Tools (12)

| Tool | Description | FFmpeg Filter |
|---|---|---|
| `import_asset` | Register media file under an alias | — |
| `add_cut_clip` | Place trimmed video on timeline | `trim` / `concat` |
| `add_audio_clip` | Place trimmed audio on timeline | `atrim` |
| `adjust_color` | Saturation, contrast, brightness, gamma | `eq` |
| `apply_lut` | Apply .cube LUT color grade | `lut3d` |
| `set_volume` | Adjust audio volume in dB | `volume` |
| `audio_duck` | Auto-lower music during speech | `sidechaincompress` |
| `add_subtitle` | Timed text overlay | `drawtext` |
| `kinetic_zoom` | Smooth zoom-in accent | `zoompan` |
| `speed_ramp` | Speed up / slow down | `setpts` / `atempo` |
| `compile_blueprint` | Export project state as JSON | — |
| `generate_ffmpeg_command` | Compile timeline to FFmpeg command | — |

---

## Architecture

```
                    +------------------+
                    |   AI Agent / CLI  |
                    +--------+---------+
                             |
                    Tool Calls (JSON)
                             |
                    +--------v---------+
                    |  AgentExecutor    |
                    |  (dispatcher)     |
                    +--------+---------+
                             |
                    Method Invocations
                             |
                    +--------v---------+
                    | CallikinoEngine   |
                    | (state machine)   |
                    |                   |
                    | state = {         |
                    |   meta, assets,   |
                    |   timeline,       |
                    |   filters         |
                    | }                 |
                    +--------+---------+
                             |
                    generate_ffmpeg_command()
                             |
                    +--------v---------+
                    |  FFmpeg Command   |
                    |  (single string)  |
                    +--------+---------+
                             |
                    subprocess.run()
                             |
                    +--------v---------+
                    |  Rendered Video   |
                    +------------------+
```

**Key Properties:**
- **Zero runtime execution** — all methods are pure state mutators
- **Single-pass render** — the compiler generates one FFmpeg command
- **Auto hardware acceleration** — detects NVIDIA/Apple/Intel GPUs
- **Smart stream copy** — uses `-c copy` when no re-encoding needed
- **Zero dependencies** — only Python stdlib + FFmpeg binary

---

## License

Callikino is dual-licensed. It is 100% free for individuals, students, and small teams (<3 employees). 
For commercial use in larger companies or funded startups, a commercial tier license is required. 
See the [LICENSE](LICENSE) file for full details.

---

<p align="center">
  <strong>Built for agents, not for GUIs.</strong>
</p>
