import json
import os
import platform
import shutil
import subprocess
from typing import Dict, List, Any, Optional


class CallikinoEngine:
    def __init__(self, resolution: str = "1920x1080", fps: int = 30):
        """
        Initializes the state management engine with global render configurations
        and maps out the empty structured state according to schema.json.
        Runs hardware auto-detection to select the optimal video encoder.
        """
        self.resolution = resolution
        self.fps = fps

        # Detect hardware before building state so we can record it
        hw_info = self._detect_hardware()
        self.encoder: str = hw_info["encoder"]
        self.hwaccel: Optional[str] = hw_info["hwaccel"]
        self.gpu_name: Optional[str] = hw_info["gpu_name"]

        self.state: Dict[str, Any] = {
            "meta": {
                "resolution": self.resolution,
                "fps": self.fps,
                "sample_rate": 48000,
                "encoder": self.encoder,
                "hwaccel": self.hwaccel,
                "gpu_name": self.gpu_name
            },
            "assets": {},
            "timeline": {
                "video_layers": [],
                "audio_layers": [],
                "text_layers": []
            },
            "filters": {
                "color": [],
                "lut": [],
                "volume": [],
                "audio_duck": [],
                "zoom": [],
                "speed": []
            }
        }

    # ------------------------------------------------------------------
    # Hardware Detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_hardware() -> Dict[str, Optional[str]]:
        """
        Probes the host system for GPU hardware and returns the optimal
        FFmpeg encoder, hwaccel flag, and a human-readable GPU name.

        Detection order:
          1. NVIDIA (nvidia-smi)  -> h264_nvenc  / hwaccel cuda
          2. Apple Silicon        -> h264_videotoolbox / hwaccel videotoolbox
          3. Intel QSV            -> h264_qsv   / hwaccel qsv
          4. Fallback             -> libx264    / no hwaccel (CPU-only)
        """
        result: Dict[str, Optional[str]] = {
            "encoder": "libx264",
            "hwaccel": None,
            "gpu_name": None,
        }

        system = platform.system()  # 'Windows', 'Linux', 'Darwin'

        # --- NVIDIA check ---
        nvidia_smi = shutil.which("nvidia-smi")
        if nvidia_smi:
            try:
                proc = subprocess.run(
                    [nvidia_smi, "--query-gpu=name", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    result["gpu_name"] = proc.stdout.strip().splitlines()[0]
                    result["encoder"] = "h264_nvenc"
                    result["hwaccel"] = "cuda"
                    return result
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                pass

        # --- Apple Silicon / VideoToolbox check ---
        if system == "Darwin":
            try:
                proc = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True, text=True, timeout=5,
                )
                if proc.returncode == 0:
                    cpu_brand = proc.stdout.strip()
                    if "Apple" in cpu_brand:
                        result["gpu_name"] = cpu_brand
                        result["encoder"] = "h264_videotoolbox"
                        result["hwaccel"] = "videotoolbox"
                        return result
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                pass

        # --- Intel QSV check (Windows / Linux) ---
        if system in ("Windows", "Linux"):
            try:
                # Quick check: see if FFmpeg itself reports qsv support
                ffmpeg_bin = shutil.which("ffmpeg")
                if ffmpeg_bin:
                    proc = subprocess.run(
                        [ffmpeg_bin, "-hide_banner", "-encoders"],
                        capture_output=True, text=True, timeout=5,
                    )
                    if proc.returncode == 0 and "h264_qsv" in proc.stdout:
                        result["gpu_name"] = "Intel QSV"
                        result["encoder"] = "h264_qsv"
                        result["hwaccel"] = "qsv"
                        return result
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                pass

        # --- CPU-only fallback ---
        return result

    # ------------------------------------------------------------------
    # Asset Management
    # ------------------------------------------------------------------

    def import_asset(self, file_path: str, alias: str) -> str:
        """
        Registers a raw media file path into the memory asset dictionary using a custom unique alias.
        Raises FileNotFoundError if the path does not exist. Returns the string alias.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Source asset not found at tracking path: {file_path}")

        self.state["assets"][alias] = os.path.abspath(file_path)
        return alias

    # ------------------------------------------------------------------
    # Timeline State Mutators — Video
    # ------------------------------------------------------------------

    def add_cut_clip(self, alias: str, layer_index: int, timeline_start: float, src_in: float, src_out: float) -> None:
        """
        Appends a slice event block directly into the 'video_layers' state tracking list.
        Validation Rules:
        - alias must exist within self.state['assets']
        - src_out must be strictly greater than src_in
        - timeline_start, src_in, src_out must be non-negative floats
        """
        if alias not in self.state["assets"]:
            raise ValueError(f"Asset alias '{alias}' is unregistered. Run import_asset first.")
        if src_out <= src_in:
            raise ValueError("Source out-point (src_out) must be greater than source in-point (src_in).")
        if timeline_start < 0 or src_in < 0:
            raise ValueError("Timestamps cannot be negative values.")

        clip_data = {
            "asset_alias": alias,
            "layer_index": layer_index,
            "timeline_start": float(timeline_start),
            "src_in": float(src_in),
            "src_out": float(src_out),
            "duration": float(src_out - src_in)
        }
        self.state["timeline"]["video_layers"].append(clip_data)

    # ------------------------------------------------------------------
    # Timeline State Mutators — Audio
    # ------------------------------------------------------------------

    def add_audio_clip(self, alias: str, timeline_start: float, src_in: float, src_out: float) -> None:
        """
        Appends an audio clip reference into the 'audio_layers' state tracking list.
        Validation Rules:
        - alias must exist within self.state['assets']
        - src_out must be strictly greater than src_in
        - timeline_start, src_in must be non-negative
        """
        if alias not in self.state["assets"]:
            raise ValueError(f"Asset alias '{alias}' is unregistered. Run import_asset first.")
        if src_out <= src_in:
            raise ValueError("Source out-point (src_out) must be greater than source in-point (src_in).")
        if timeline_start < 0 or src_in < 0:
            raise ValueError("Timestamps cannot be negative values.")

        audio_data = {
            "asset_alias": alias,
            "timeline_start": float(timeline_start),
            "src_in": float(src_in),
            "src_out": float(src_out),
            "duration": float(src_out - src_in)
        }
        self.state["timeline"]["audio_layers"].append(audio_data)

    # ------------------------------------------------------------------
    # Filter State Mutators — Color Grading
    # ------------------------------------------------------------------

    def adjust_color(
        self,
        saturation: float = 1.0,
        contrast: float = 1.0,
        brightness: float = 0.0,
        gamma: float = 1.0
    ) -> None:
        """
        Pushes a color correction filter block into the state.
        Maps to FFmpeg's `eq` filter at render time.

        Parameters:
          saturation : float  — 0.0 = greyscale, 1.0 = original, 2.0 = double (range 0.0–3.0)
          contrast   : float  — 1.0 = original (range -1000.0–1000.0, practical 0.5–2.0)
          brightness : float  — 0.0 = original (range -1.0–1.0)
          gamma      : float  — 1.0 = original (range 0.1–10.0)
        """
        if not (0.0 <= saturation <= 3.0):
            raise ValueError(f"Saturation must be between 0.0 and 3.0, got {saturation}")
        if not (0.5 <= contrast <= 2.0):
            raise ValueError(f"Contrast must be between 0.5 and 2.0, got {contrast}")
        if not (-1.0 <= brightness <= 1.0):
            raise ValueError(f"Brightness must be between -1.0 and 1.0, got {brightness}")
        if not (0.1 <= gamma <= 10.0):
            raise ValueError(f"Gamma must be between 0.1 and 10.0, got {gamma}")

        color_filter = {
            "type": "eq",
            "saturation": float(saturation),
            "contrast": float(contrast),
            "brightness": float(brightness),
            "gamma": float(gamma)
        }
        self.state["filters"]["color"].append(color_filter)

    def apply_lut(self, lut_path: str) -> None:
        """
        Registers a .cube LUT file for cinematic color grading.
        Maps to FFmpeg's `lut3d` filter at render time.

        Parameters:
          lut_path : str — Absolute or relative path to a .cube LUT file.
        """
        if not os.path.exists(lut_path):
            raise FileNotFoundError(f"LUT file not found: {lut_path}")
        if not lut_path.lower().endswith(".cube"):
            raise ValueError(f"LUT file must be a .cube file, got: {lut_path}")

        lut_filter = {
            "type": "lut3d",
            "path": os.path.abspath(lut_path)
        }
        self.state["filters"]["lut"].append(lut_filter)

    # ------------------------------------------------------------------
    # Filter State Mutators — Audio Mixing (Week 6)
    # ------------------------------------------------------------------

    def set_volume(self, alias: str, level_db: float) -> None:
        """
        Sets the volume adjustment for a specific audio asset on the timeline.
        Maps to FFmpeg's `volume` filter at render time.

        Parameters:
          alias    : str   — Must be a registered asset alias.
          level_db : float — Volume change in decibels. 0 = unchanged,
                             negative = quieter, positive = louder.
                             Clamped to range -60.0 to +24.0 dB.
        """
        if alias not in self.state["assets"]:
            raise ValueError(f"Asset alias '{alias}' is unregistered. Run import_asset first.")
        if not (-60.0 <= level_db <= 24.0):
            raise ValueError(f"Volume level must be between -60.0 and 24.0 dB, got {level_db}")

        volume_filter = {
            "type": "volume",
            "asset_alias": alias,
            "level_db": float(level_db)
        }
        self.state["filters"]["volume"].append(volume_filter)

    def audio_duck(
        self,
        music_alias: str,
        voice_alias: str,
        duck_db: float = -14.0,
        threshold: float = 0.02,
        attack: float = 200.0,
        release: float = 1000.0
    ) -> None:
        """
        Configures automatic audio ducking: lowers the music track when
        the voice track is active.
        Maps to FFmpeg's `sidechaincompress` filter at render time.

        Parameters:
          music_alias : str   — Alias of the background music asset.
          voice_alias : str   — Alias of the voice/narration asset.
          duck_db     : float — Amount to reduce music volume in dB (negative, range -40 to 0).
          threshold   : float — Voice detection threshold (0.0–1.0).
          attack      : float — Attack time in milliseconds (1–2000).
          release     : float — Release time in milliseconds (1–9000).
        """
        if music_alias not in self.state["assets"]:
            raise ValueError(f"Music alias '{music_alias}' is unregistered.")
        if voice_alias not in self.state["assets"]:
            raise ValueError(f"Voice alias '{voice_alias}' is unregistered.")
        if not (-40.0 <= duck_db <= 0.0):
            raise ValueError(f"Duck level must be between -40.0 and 0.0 dB, got {duck_db}")
        if not (0.0 <= threshold <= 1.0):
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {threshold}")
        if not (1.0 <= attack <= 2000.0):
            raise ValueError(f"Attack must be between 1 and 2000 ms, got {attack}")
        if not (1.0 <= release <= 9000.0):
            raise ValueError(f"Release must be between 1 and 9000 ms, got {release}")

        duck_filter = {
            "type": "sidechaincompress",
            "music_alias": music_alias,
            "voice_alias": voice_alias,
            "duck_db": float(duck_db),
            "threshold": float(threshold),
            "attack": float(attack),
            "release": float(release)
        }
        self.state["filters"]["audio_duck"].append(duck_filter)

    # ------------------------------------------------------------------
    # Filter State Mutators — Kinetic & Text (Week 7)
    # ------------------------------------------------------------------

    def add_subtitle(
        self,
        text: str,
        start_time: float,
        end_time: float,
        fontsize: int = 48,
        fontcolor: str = "white",
        borderw: int = 2,
        x: str = "(w-text_w)/2",
        y: str = "h-th-40"
    ) -> None:
        """
        Pushes a text overlay block into the 'text_layers' timeline.
        Maps to FFmpeg's `drawtext` filter at render time.

        Parameters:
          text       : str   — The text string to burn onto the video.
          start_time : float — When the text appears (seconds).
          end_time   : float — When the text disappears (seconds).
          fontsize   : int   — Font size in pixels (8–200).
          fontcolor  : str   — FFmpeg color name or hex (e.g. 'white', '0xFFFFFF').
          borderw    : int   — Border/shadow thickness in pixels (0–10).
          x, y       : str   — Position expressions (FFmpeg-style, supports math).
        """
        if not text or not text.strip():
            raise ValueError("Subtitle text cannot be empty.")
        if end_time <= start_time:
            raise ValueError("end_time must be greater than start_time.")
        if start_time < 0:
            raise ValueError("start_time cannot be negative.")
        if not (8 <= fontsize <= 200):
            raise ValueError(f"Font size must be between 8 and 200, got {fontsize}")
        if not (0 <= borderw <= 10):
            raise ValueError(f"Border width must be between 0 and 10, got {borderw}")

        text_data = {
            "type": "drawtext",
            "text": text,
            "start_time": float(start_time),
            "end_time": float(end_time),
            "fontsize": fontsize,
            "fontcolor": fontcolor,
            "borderw": borderw,
            "x": x,
            "y": y
        }
        self.state["timeline"]["text_layers"].append(text_data)

    def kinetic_zoom(
        self,
        start_time: float,
        end_time: float,
        scale: float = 1.2,
        target_x: str = "iw/2",
        target_y: str = "ih/2"
    ) -> None:
        """
        Pushes a kinetic zoom effect into the filter state.
        Maps to FFmpeg's `zoompan` filter at render time.

        Creates a smooth zoom-in effect that holds for the specified
        duration, commonly used for emphasis on punchlines.

        Parameters:
          start_time : float — When the zoom begins (seconds).
          end_time   : float — When the zoom ends (seconds).
          scale      : float — Zoom magnification (1.0 = none, 1.5 = 50% closer). Range 1.0–3.0.
          target_x   : str   — Horizontal zoom center (FFmpeg expression).
          target_y   : str   — Vertical zoom center (FFmpeg expression).
        """
        if end_time <= start_time:
            raise ValueError("end_time must be greater than start_time.")
        if start_time < 0:
            raise ValueError("start_time cannot be negative.")
        if not (1.0 <= scale <= 3.0):
            raise ValueError(f"Scale must be between 1.0 and 3.0, got {scale}")

        zoom_filter = {
            "type": "zoompan",
            "start_time": float(start_time),
            "end_time": float(end_time),
            "scale": float(scale),
            "target_x": target_x,
            "target_y": target_y,
            "duration_frames": int((end_time - start_time) * self.fps)
        }
        self.state["filters"]["zoom"].append(zoom_filter)

    def speed_ramp(
        self,
        alias: str,
        speed_factor: float,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> None:
        """
        Pushes a speed change filter into the state.
        Maps to FFmpeg's `setpts` (video) and `atempo` (audio) at render time.

        Parameters:
          alias        : str   — Must be a registered asset alias.
          speed_factor : float — Playback speed multiplier.
                                 0.5 = half speed, 2.0 = double speed.
                                 Range 0.25–4.0.
          start_time   : float — Optional. If provided, speed ramp applies only
                                 to this segment (seconds).
          end_time     : float — Optional. End of the speed ramp segment.
        """
        if alias not in self.state["assets"]:
            raise ValueError(f"Asset alias '{alias}' is unregistered. Run import_asset first.")
        if not (0.25 <= speed_factor <= 4.0):
            raise ValueError(f"Speed factor must be between 0.25 and 4.0, got {speed_factor}")
        if start_time is not None and start_time < 0:
            raise ValueError("start_time cannot be negative.")
        if start_time is not None and end_time is not None and end_time <= start_time:
            raise ValueError("end_time must be greater than start_time.")

        speed_filter = {
            "type": "speed",
            "asset_alias": alias,
            "speed_factor": float(speed_factor),
            "start_time": float(start_time) if start_time is not None else None,
            "end_time": float(end_time) if end_time is not None else None
        }
        self.state["filters"]["speed"].append(speed_filter)

    # ------------------------------------------------------------------
    # Blueprint Serializer
    # ------------------------------------------------------------------

    def compile_blueprint(self, pretty: bool = True) -> str:
        """
        Serializes the active runtime memory tracking state into a valid JSON string object.
        If pretty=True, output with clean indent tracking.
        """
        indent = 4 if pretty else None
        return json.dumps(self.state, indent=indent)

    # ------------------------------------------------------------------
    # FFmpeg Command Compiler
    # ------------------------------------------------------------------

    def _has_filters(self) -> bool:
        """Returns True if any filter state mutators have been called."""
        f = self.state["filters"]
        return any([
            f["color"], f["lut"], f["volume"],
            f["audio_duck"], f["zoom"], f["speed"]
        ])

    def _needs_reencoding(self) -> bool:
        """
        Inspect the current timeline state and determine whether
        stream-copy is viable or if we must re-encode.

        Stream copy is possible when:
          - There are no text_layers (no burn-in overlays).
          - There are no active filters (color, zoom, speed, etc.).
          - There is only a single video layer clip.

        Everything else requires a full re-encode pass.
        """
        video_layers = self.state["timeline"]["video_layers"]
        text_layers = self.state["timeline"]["text_layers"]

        if text_layers:
            return True
        if self._has_filters():
            return True
        if len(video_layers) == 0:
            return False  # nothing to render
        if len(video_layers) == 1:
            return False  # single trim -> stream copy

        # Multiple clips -> need concat demuxer or filter graph -> re-encode
        return True

    def _build_video_filter_chain(self) -> List[str]:
        """
        Compiles all video filter state entries into FFmpeg filter string
        fragments that will be chained together in the filter_complex graph.
        """
        filters: List[str] = []

        # Color grading (eq filter)
        for cf in self.state["filters"]["color"]:
            eq_parts = []
            if cf["saturation"] != 1.0:
                eq_parts.append(f"saturation={cf['saturation']}")
            if cf["contrast"] != 1.0:
                eq_parts.append(f"contrast={cf['contrast']}")
            if cf["brightness"] != 0.0:
                eq_parts.append(f"brightness={cf['brightness']}")
            if cf["gamma"] != 1.0:
                eq_parts.append(f"gamma={cf['gamma']}")
            if eq_parts:
                filters.append("eq=" + ":".join(eq_parts))

        # LUT grading (lut3d filter)
        for lf in self.state["filters"]["lut"]:
            filters.append(f"lut3d=file='{lf['path']}'")

        # Kinetic zoom (zoompan filter)
        for zf in self.state["filters"]["zoom"]:
            w, h = self.resolution.split("x")
            # zoompan with smooth ramp from 1.0 to scale
            filters.append(
                f"zoompan=z='min(zoom+{(zf['scale'] - 1.0) / max(zf['duration_frames'], 1):.6f},{zf['scale']})'"
                f":x='{zf['target_x']}-(iw/zoom/2)'"
                f":y='{zf['target_y']}-(ih/zoom/2)'"
                f":d={zf['duration_frames']}"
                f":s={w}x{h}"
                f":fps={self.fps}"
            )

        # Speed ramp (setpts filter)
        for sf in self.state["filters"]["speed"]:
            pts_factor = 1.0 / sf["speed_factor"]
            filters.append(f"setpts={pts_factor:.4f}*PTS")

        return filters

    def _build_audio_filter_chain(self) -> List[str]:
        """
        Compiles all audio filter state entries into FFmpeg audio filter
        string fragments.
        """
        filters: List[str] = []

        # Volume adjustments
        for vf in self.state["filters"]["volume"]:
            filters.append(f"volume={vf['level_db']}dB")

        # Speed (atempo) — must chain multiple atempo for extreme values
        for sf in self.state["filters"]["speed"]:
            factor = sf["speed_factor"]
            # atempo only accepts 0.5–100.0, so chain for extremes
            while factor < 0.5:
                filters.append("atempo=0.5")
                factor /= 0.5
            while factor > 2.0:
                filters.append("atempo=2.0")
                factor /= 2.0
            filters.append(f"atempo={factor:.4f}")

        return filters

    def _build_text_overlay_filters(self) -> List[str]:
        """
        Compiles text_layers into FFmpeg drawtext filter strings.
        """
        filters: List[str] = []

        for tl in self.state["timeline"]["text_layers"]:
            # Escape special characters for drawtext
            escaped_text = tl["text"].replace("'", "\\'").replace(":", "\\:")
            dt = (
                f"drawtext=text='{escaped_text}'"
                f":fontsize={tl['fontsize']}"
                f":fontcolor={tl['fontcolor']}"
                f":borderw={tl['borderw']}"
                f":x={tl['x']}"
                f":y={tl['y']}"
                f":enable='between(t,{tl['start_time']},{tl['end_time']})'"
            )
            filters.append(dt)

        return filters

    def generate_ffmpeg_command(self, output_path: str) -> str:
        """
        Parses the current timeline blueprint and compiles it into a single,
        optimized FFmpeg command string.

        Strategy:
          - Single clip, no filters  -> stream-copy trim (lightning fast).
          - Multiple clips, no filters -> concat demuxer with stream copy.
          - Any filters / text layers -> full re-encode with hwaccel.

        Returns the complete FFmpeg command as a string.
        Raises ValueError if the timeline is empty.
        """
        video_layers = self.state["timeline"]["video_layers"]
        if not video_layers:
            raise ValueError("Timeline has no video layers. Nothing to render.")

        ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"

        # --- SINGLE CLIP: stream-copy trim ---
        if len(video_layers) == 1 and not self._needs_reencoding():
            clip = video_layers[0]
            asset_path = self.state["assets"][clip["asset_alias"]]
            ss = clip["src_in"]
            duration = clip["duration"]

            cmd = (
                f'"{ffmpeg_bin}" -y'
                f' -ss {ss}'
                f' -i "{asset_path}"'
                f' -t {duration}'
                f' -c copy'
                f' "{output_path}"'
            )
            return cmd

        # --- FULL RE-ENCODE with filter_complex ---
        # Sort clips by timeline_start for sequential ordering
        sorted_clips = sorted(video_layers, key=lambda c: c["timeline_start"])

        # Build hwaccel flags
        hwaccel_flags = ""
        if self.hwaccel:
            hwaccel_flags = f" -hwaccel {self.hwaccel}"

        # Build input list and trim filter segments
        input_flags: List[str] = []
        filter_segments: List[str] = []
        seen_assets: Dict[str, int] = {}  # alias -> input index
        input_index = 0

        for i, clip in enumerate(sorted_clips):
            alias = clip["asset_alias"]
            asset_path = self.state["assets"][alias]

            # De-duplicate inputs: reuse the same -i for clips from the same file
            if alias not in seen_assets:
                input_flags.append(f'-i "{asset_path}"')
                seen_assets[alias] = input_index
                input_index += 1

            idx = seen_assets[alias]
            ss = clip["src_in"]
            dur = clip["duration"]

            # Trim each segment in the filter graph
            filter_segments.append(
                f"[{idx}:v]trim=start={ss}:duration={dur},setpts=PTS-STARTPTS[v{i}];"
                f"[{idx}:a]atrim=start={ss}:duration={dur},asetpts=PTS-STARTPTS[a{i}]"
            )

        # Concat all trimmed segments
        n = len(sorted_clips)
        v_labels = "".join(f"[v{i}]" for i in range(n))
        a_labels = "".join(f"[a{i}]" for i in range(n))
        concat_filter = f"{v_labels}{a_labels}concat=n={n}:v=1:a=1[outv][outa]"

        full_filter = ";".join(filter_segments) + ";" + concat_filter

        # --- Append post-processing video filters ---
        video_post = self._build_video_filter_chain()
        text_post = self._build_text_overlay_filters()
        all_video_post = video_post + text_post

        if all_video_post:
            chain = ",".join(all_video_post)
            full_filter += f";[outv]{chain}[outv_final]"
            video_map = "[outv_final]"
        else:
            video_map = "[outv]"

        # --- Append post-processing audio filters ---
        audio_post = self._build_audio_filter_chain()
        if audio_post:
            chain = ",".join(audio_post)
            full_filter += f";[outa]{chain}[outa_final]"
            audio_map = "[outa_final]"
        else:
            audio_map = "[outa]"

        # Resolution and fps
        w, h = self.resolution.split("x")

        cmd = (
            f'"{ffmpeg_bin}" -y{hwaccel_flags}'
            f' {" ".join(input_flags)}'
            f' -filter_complex "{full_filter}"'
            f' -map "{video_map}" -map "{audio_map}"'
            f' -c:v {self.encoder} -c:a aac'
            f' -r {self.fps} -s {self.resolution}'
            f' "{output_path}"'
        )
        return cmd
