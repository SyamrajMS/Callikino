"""
Callikino Tool Schemas — Week 8
================================
Exports every CallikinoEngine method as a structured JSON function-calling
schema compatible with OpenAI, Anthropic, and Gemini tool-use APIs.

An LLM agent can import TOOL_SCHEMAS and pass them directly as the `tools`
parameter when making chat completions. When the model emits a tool_call,
the AgentExecutor (agent_executor.py) routes it into the live engine.
"""

from typing import List, Dict, Any


# ---------------------------------------------------------------------------
# Individual tool definitions (OpenAI function-calling format)
# ---------------------------------------------------------------------------

IMPORT_ASSET = {
    "type": "function",
    "function": {
        "name": "import_asset",
        "description": (
            "Register a media file (video, audio, image) into the project "
            "asset library under a unique alias. Must be called before the "
            "asset can be placed on the timeline."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute or relative path to the media file on disk."
                },
                "alias": {
                    "type": "string",
                    "description": (
                        "A short, unique alphanumeric identifier for this asset "
                        "(e.g. 'raw_vlog', 'bgm', 'intro_clip')."
                    )
                }
            },
            "required": ["file_path", "alias"]
        }
    }
}

ADD_CUT_CLIP = {
    "type": "function",
    "function": {
        "name": "add_cut_clip",
        "description": (
            "Place a trimmed video segment onto the timeline. Specify which "
            "portion of the source file to use (src_in/src_out) and where it "
            "starts on the output timeline (timeline_start)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "alias": {
                    "type": "string",
                    "description": "Asset alias (must be previously imported)."
                },
                "layer_index": {
                    "type": "integer",
                    "description": "Video layer/track index (0 = primary track)."
                },
                "timeline_start": {
                    "type": "number",
                    "description": "Position on the output timeline where this clip begins (seconds)."
                },
                "src_in": {
                    "type": "number",
                    "description": "Start timestamp within the source file (seconds)."
                },
                "src_out": {
                    "type": "number",
                    "description": "End timestamp within the source file (seconds). Must be > src_in."
                }
            },
            "required": ["alias", "layer_index", "timeline_start", "src_in", "src_out"]
        }
    }
}

ADD_AUDIO_CLIP = {
    "type": "function",
    "function": {
        "name": "add_audio_clip",
        "description": (
            "Place a trimmed audio segment onto the audio timeline layer."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "alias": {
                    "type": "string",
                    "description": "Asset alias (must be previously imported)."
                },
                "timeline_start": {
                    "type": "number",
                    "description": "Position on the output timeline (seconds)."
                },
                "src_in": {
                    "type": "number",
                    "description": "Start timestamp within the source audio (seconds)."
                },
                "src_out": {
                    "type": "number",
                    "description": "End timestamp within the source audio (seconds)."
                }
            },
            "required": ["alias", "timeline_start", "src_in", "src_out"]
        }
    }
}

ADJUST_COLOR = {
    "type": "function",
    "function": {
        "name": "adjust_color",
        "description": (
            "Apply color correction to the video output. Adjusts saturation, "
            "contrast, brightness, and gamma globally. Maps to FFmpeg eq filter."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "saturation": {
                    "type": "number",
                    "description": "Color saturation (0.0=greyscale, 1.0=original, 3.0=max). Default 1.0."
                },
                "contrast": {
                    "type": "number",
                    "description": "Contrast level (0.5-2.0, 1.0=original). Default 1.0."
                },
                "brightness": {
                    "type": "number",
                    "description": "Brightness offset (-1.0 to 1.0, 0.0=original). Default 0.0."
                },
                "gamma": {
                    "type": "number",
                    "description": "Gamma correction (0.1-10.0, 1.0=original). Default 1.0."
                }
            },
            "required": []
        }
    }
}

APPLY_LUT = {
    "type": "function",
    "function": {
        "name": "apply_lut",
        "description": (
            "Apply a cinematic .cube LUT color grade to the entire video. "
            "Maps to FFmpeg lut3d filter."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "lut_path": {
                    "type": "string",
                    "description": "Path to a .cube LUT file on disk."
                }
            },
            "required": ["lut_path"]
        }
    }
}

SET_VOLUME = {
    "type": "function",
    "function": {
        "name": "set_volume",
        "description": (
            "Adjust the volume of a specific audio asset in decibels. "
            "0 = unchanged, negative = quieter, positive = louder."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "alias": {
                    "type": "string",
                    "description": "Asset alias of the audio track to adjust."
                },
                "level_db": {
                    "type": "number",
                    "description": "Volume adjustment in dB (-60.0 to +24.0)."
                }
            },
            "required": ["alias", "level_db"]
        }
    }
}

AUDIO_DUCK = {
    "type": "function",
    "function": {
        "name": "audio_duck",
        "description": (
            "Automatically lower background music volume when voice/narration "
            "is detected. Creates a professional podcast/vlog mix."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "music_alias": {
                    "type": "string",
                    "description": "Asset alias of the background music track."
                },
                "voice_alias": {
                    "type": "string",
                    "description": "Asset alias of the voice/narration track."
                },
                "duck_db": {
                    "type": "number",
                    "description": "Amount to reduce music in dB (-40 to 0). Default -14.0."
                },
                "threshold": {
                    "type": "number",
                    "description": "Voice detection threshold (0.0-1.0). Default 0.02."
                },
                "attack": {
                    "type": "number",
                    "description": "Attack time in ms (1-2000). Default 200."
                },
                "release": {
                    "type": "number",
                    "description": "Release time in ms (1-9000). Default 1000."
                }
            },
            "required": ["music_alias", "voice_alias"]
        }
    }
}

ADD_SUBTITLE = {
    "type": "function",
    "function": {
        "name": "add_subtitle",
        "description": (
            "Burn a text overlay onto the video at a specific time range. "
            "Supports custom font size, color, position, and border width."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text string to display on screen."
                },
                "start_time": {
                    "type": "number",
                    "description": "When the text appears (seconds)."
                },
                "end_time": {
                    "type": "number",
                    "description": "When the text disappears (seconds)."
                },
                "fontsize": {
                    "type": "integer",
                    "description": "Font size in pixels (8-200). Default 48."
                },
                "fontcolor": {
                    "type": "string",
                    "description": "FFmpeg color name or hex (e.g. 'white'). Default 'white'."
                },
                "borderw": {
                    "type": "integer",
                    "description": "Border/shadow thickness (0-10). Default 2."
                },
                "x": {
                    "type": "string",
                    "description": "Horizontal position expression. Default '(w-text_w)/2' (centered)."
                },
                "y": {
                    "type": "string",
                    "description": "Vertical position expression. Default 'h-th-40' (bottom)."
                }
            },
            "required": ["text", "start_time", "end_time"]
        }
    }
}

KINETIC_ZOOM = {
    "type": "function",
    "function": {
        "name": "kinetic_zoom",
        "description": (
            "Apply a smooth zoom-in effect during a specific time range. "
            "Commonly used for emphasis on punchlines or key moments."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "start_time": {
                    "type": "number",
                    "description": "When the zoom begins (seconds)."
                },
                "end_time": {
                    "type": "number",
                    "description": "When the zoom ends (seconds)."
                },
                "scale": {
                    "type": "number",
                    "description": "Zoom magnification (1.0=none, 1.5=50% closer). Range 1.0-3.0. Default 1.2."
                },
                "target_x": {
                    "type": "string",
                    "description": "Horizontal zoom center (FFmpeg expression). Default 'iw/2'."
                },
                "target_y": {
                    "type": "string",
                    "description": "Vertical zoom center (FFmpeg expression). Default 'ih/2'."
                }
            },
            "required": ["start_time", "end_time"]
        }
    }
}

SPEED_RAMP = {
    "type": "function",
    "function": {
        "name": "speed_ramp",
        "description": (
            "Change the playback speed of a clip. 0.5 = half speed (slow-mo), "
            "2.0 = double speed (fast forward)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "alias": {
                    "type": "string",
                    "description": "Asset alias of the clip to speed-ramp."
                },
                "speed_factor": {
                    "type": "number",
                    "description": "Speed multiplier (0.25-4.0). 1.0 = normal."
                },
                "start_time": {
                    "type": "number",
                    "description": "Optional start of the speed-ramp segment (seconds)."
                },
                "end_time": {
                    "type": "number",
                    "description": "Optional end of the speed-ramp segment (seconds)."
                }
            },
            "required": ["alias", "speed_factor"]
        }
    }
}

COMPILE_BLUEPRINT = {
    "type": "function",
    "function": {
        "name": "compile_blueprint",
        "description": (
            "Serialize the current project state (timeline, assets, filters) "
            "into a JSON string for inspection or storage."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pretty": {
                    "type": "boolean",
                    "description": "If true, output indented JSON. Default true."
                }
            },
            "required": []
        }
    }
}

GENERATE_FFMPEG_COMMAND = {
    "type": "function",
    "function": {
        "name": "generate_ffmpeg_command",
        "description": (
            "Compile the entire timeline into a single, optimized FFmpeg "
            "command string. Uses stream-copy when possible, otherwise "
            "builds a hardware-accelerated filter_complex graph."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "output_path": {
                    "type": "string",
                    "description": "File path for the rendered output video."
                }
            },
            "required": ["output_path"]
        }
    }
}


# ---------------------------------------------------------------------------
# Aggregated schema list — pass this directly to your LLM API as `tools`
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: List[Dict[str, Any]] = [
    IMPORT_ASSET,
    ADD_CUT_CLIP,
    ADD_AUDIO_CLIP,
    ADJUST_COLOR,
    APPLY_LUT,
    SET_VOLUME,
    AUDIO_DUCK,
    ADD_SUBTITLE,
    KINETIC_ZOOM,
    SPEED_RAMP,
    COMPILE_BLUEPRINT,
    GENERATE_FFMPEG_COMMAND,
]


def get_tool_schemas() -> List[Dict[str, Any]]:
    """Returns a deep copy of all tool schemas for safe mutation."""
    import copy
    return copy.deepcopy(TOOL_SCHEMAS)


def get_tool_names() -> List[str]:
    """Returns a flat list of all available tool function names."""
    return [t["function"]["name"] for t in TOOL_SCHEMAS]
