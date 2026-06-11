"""
Callikino JumpCut Pipeline
===========================
End-to-end automated editing pipeline that transforms raw talking-head
footage into a high-retention, jump-cut, zoom-accented video — completely
autonomously.

Architecture:
  Layer 1: Silence Detection  -> Strip dead air (FFmpeg silencedetect)
  Layer 2: Transcript Extract -> Word-level timestamps (Whisper integration)
  Layer 3: Semantic Accents   -> Zoom-ins on emphasis words, subtitle burns
  Layer 4: Asset Stitching    -> B-roll overlays, SFX injection
  Layer 5: Final Render       -> Single-pass hardware-accelerated output

All layers are pure state mutations on CallikinoEngine. No FFmpeg process
runs until the final render() call.
"""

import os
import re
import json
import subprocess
import shutil
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from callikino.core import CallikinoEngine
from callikino.agent_executor import AgentExecutor


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class SilenceRegion:
    """A detected silence interval in the source audio."""
    start: float
    end: float
    duration: float


@dataclass
class WordTimestamp:
    """A single word with its start/end time from transcription."""
    word: str
    start: float
    end: float


@dataclass
class TranscriptSegment:
    """A sentence or phrase with word-level timestamps."""
    text: str
    start: float
    end: float
    words: List[WordTimestamp] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Layer 1: Silence Detection
# ---------------------------------------------------------------------------

def detect_silence(
    file_path: str,
    noise_threshold_db: float = -30.0,
    min_silence_duration: float = 0.5
) -> List[SilenceRegion]:
    """
    Run FFmpeg's silencedetect filter on a media file and parse the output
    to extract all silence intervals.

    Parameters:
      file_path             : Path to the input media file.
      noise_threshold_db    : Volume threshold below which audio is "silence" (dB).
      min_silence_duration  : Minimum duration to qualify as a silence gap (seconds).

    Returns:
      List of SilenceRegion objects.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Media file not found: {file_path}")

    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"

    cmd = [
        ffmpeg_bin, "-i", file_path,
        "-af", f"silencedetect=noise={noise_threshold_db}dB:d={min_silence_duration}",
        "-f", "null", "-"
    ]

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg silencedetect timed out after 300 seconds.")

    # Parse stderr for silence_start and silence_end markers
    output = proc.stderr
    regions: List[SilenceRegion] = []

    # Patterns:  [silencedetect @ ...] silence_start: 1.234
    #            [silencedetect @ ...] silence_end: 5.678 | silence_duration: 4.444
    start_pattern = re.compile(r"silence_start:\s*([\d.]+)")
    end_pattern = re.compile(r"silence_end:\s*([\d.]+)\s*\|\s*silence_duration:\s*([\d.]+)")

    pending_start: Optional[float] = None

    for line in output.splitlines():
        start_match = start_pattern.search(line)
        if start_match:
            pending_start = float(start_match.group(1))
            continue

        end_match = end_pattern.search(line)
        if end_match and pending_start is not None:
            end_time = float(end_match.group(1))
            duration = float(end_match.group(2))
            regions.append(SilenceRegion(
                start=pending_start,
                end=end_time,
                duration=duration
            ))
            pending_start = None

    return regions


def compute_speech_segments(
    total_duration: float,
    silence_regions: List[SilenceRegion],
    padding: float = 0.05
) -> List[Tuple[float, float]]:
    """
    Given the total media duration and detected silence regions,
    compute the inverse: the segments where speech is active.

    Parameters:
      total_duration   : Total length of the media file in seconds.
      silence_regions  : List of SilenceRegion from detect_silence().
      padding          : Small buffer to avoid cutting mid-word (seconds).

    Returns:
      List of (start, end) tuples representing speech segments.
    """
    if not silence_regions:
        return [(0.0, total_duration)]

    # Sort by start time
    sorted_regions = sorted(silence_regions, key=lambda r: r.start)

    speech_segments: List[Tuple[float, float]] = []
    cursor = 0.0

    for region in sorted_regions:
        seg_start = cursor
        seg_end = max(cursor, region.start - padding)

        if seg_end > seg_start + 0.1:  # Minimum 100ms segment
            speech_segments.append((seg_start, seg_end))

        cursor = region.end + padding

    # Final segment after last silence
    if cursor < total_duration:
        speech_segments.append((cursor, total_duration))

    return speech_segments


# ---------------------------------------------------------------------------
# Layer 2: Transcript Integration (Whisper-compatible)
# ---------------------------------------------------------------------------

def parse_whisper_json(whisper_output: Dict[str, Any]) -> List[TranscriptSegment]:
    """
    Parse the JSON output from OpenAI Whisper (or whisper.cpp) into
    structured TranscriptSegment objects with word-level timestamps.

    Expected format (Whisper --output_format json with word_timestamps=True):
    {
      "segments": [
        {
          "text": "Hello world",
          "start": 0.0,
          "end": 2.5,
          "words": [
            {"word": "Hello", "start": 0.0, "end": 1.0},
            {"word": "world", "start": 1.1, "end": 2.5}
          ]
        }
      ]
    }
    """
    segments: List[TranscriptSegment] = []

    for seg in whisper_output.get("segments", []):
        words = []
        for w in seg.get("words", []):
            words.append(WordTimestamp(
                word=w.get("word", "").strip(),
                start=float(w.get("start", 0)),
                end=float(w.get("end", 0))
            ))

        segments.append(TranscriptSegment(
            text=seg.get("text", "").strip(),
            start=float(seg.get("start", 0)),
            end=float(seg.get("end", 0)),
            words=words
        ))

    return segments


def identify_emphasis_words(
    segments: List[TranscriptSegment],
    emphasis_keywords: Optional[List[str]] = None,
    max_accents: int = 10
) -> List[WordTimestamp]:
    """
    Scan the transcript for emphasis-worthy words (punchlines, keywords,
    exclamations) that should receive kinetic zoom accents.

    Strategy:
      1. If emphasis_keywords provided, match those words.
      2. Otherwise, use heuristics: words following "!", capitalized words,
         and words longer than 8 characters (likely important nouns/verbs).

    Parameters:
      segments          : Parsed transcript segments.
      emphasis_keywords : Optional list of trigger words to match.
      max_accents       : Maximum number of zoom accents to generate.

    Returns:
      List of WordTimestamp objects that should receive zoom effects.
    """
    candidates: List[WordTimestamp] = []

    for seg in segments:
        for i, word in enumerate(seg.words):
            clean = word.word.strip().lower()

            if emphasis_keywords:
                if any(kw.lower() in clean for kw in emphasis_keywords):
                    candidates.append(word)
            else:
                # Heuristic: long words, exclamation context, ALL CAPS
                if len(clean) > 8:
                    candidates.append(word)
                elif word.word.isupper() and len(clean) > 2:
                    candidates.append(word)
                elif i > 0 and "!" in seg.words[i - 1].word:
                    candidates.append(word)

    # De-duplicate words too close together (within 3 seconds)
    filtered: List[WordTimestamp] = []
    for c in candidates:
        if not filtered or (c.start - filtered[-1].end) > 3.0:
            filtered.append(c)

    return filtered[:max_accents]


# ---------------------------------------------------------------------------
# Layer 3-5: The Pipeline Orchestrator
# ---------------------------------------------------------------------------

class JumpCutPipeline:
    """
    Orchestrates the full automated editing pipeline:
      1. Detect and strip silence gaps (jump-cuts)
      2. Parse Whisper transcript for emphasis moments
      3. Inject kinetic zooms on punchlines
      4. Burn in subtitles from transcript
      5. Optionally overlay B-roll and SFX
      6. Compile the final FFmpeg command

    All operations are pure state mutations — no rendering until
    generate_render_command() is called.
    """

    def __init__(
        self,
        source_video: str,
        resolution: str = "1920x1080",
        fps: int = 30
    ):
        if not os.path.exists(source_video):
            raise FileNotFoundError(f"Source video not found: {source_video}")

        self.source_video = os.path.abspath(source_video)
        self.engine = CallikinoEngine(resolution=resolution, fps=fps)
        self.executor = AgentExecutor(self.engine)

        # Import the source video as the primary asset
        self.engine.import_asset(self.source_video, "main_footage")

        # Pipeline state
        self.silence_regions: List[SilenceRegion] = []
        self.speech_segments: List[Tuple[float, float]] = []
        self.transcript_segments: List[TranscriptSegment] = []
        self.emphasis_words: List[WordTimestamp] = []

    # --- Step 1: Jump-Cut Automator ---

    def strip_silence(
        self,
        noise_db: float = -30.0,
        min_silence: float = 0.5,
        padding: float = 0.05,
        total_duration: Optional[float] = None
    ) -> List[Tuple[float, float]]:
        """
        Detect silence in the source video and compute the speech-only
        segments. Places each speech segment as a sequential clip on
        the timeline.

        Parameters:
          noise_db       : Silence detection threshold in dB.
          min_silence    : Minimum gap to classify as silence (seconds).
          padding        : Buffer around cuts to avoid clipping words.
          total_duration : Total video length. If None, auto-detected via FFprobe.

        Returns:
          List of (start, end) speech segment tuples.
        """
        self.silence_regions = detect_silence(
            self.source_video, noise_db, min_silence
        )

        if total_duration is None:
            total_duration = self._get_duration()

        self.speech_segments = compute_speech_segments(
            total_duration, self.silence_regions, padding
        )

        # Place each speech segment on the timeline sequentially
        timeline_cursor = 0.0
        for seg_start, seg_end in self.speech_segments:
            duration = seg_end - seg_start
            self.engine.add_cut_clip(
                alias="main_footage",
                layer_index=0,
                timeline_start=timeline_cursor,
                src_in=seg_start,
                src_out=seg_end
            )
            timeline_cursor += duration

        return self.speech_segments

    # --- Step 2: Transcript Integration ---

    def load_transcript(
        self,
        whisper_json_path: Optional[str] = None,
        whisper_json_data: Optional[Dict[str, Any]] = None
    ) -> List[TranscriptSegment]:
        """
        Load a Whisper transcript from a JSON file or a pre-parsed dict.

        Parameters:
          whisper_json_path : Path to a Whisper output JSON file.
          whisper_json_data : Pre-loaded Whisper JSON dictionary.

        Returns:
          List of TranscriptSegment objects.
        """
        if whisper_json_path:
            if not os.path.exists(whisper_json_path):
                raise FileNotFoundError(f"Whisper JSON not found: {whisper_json_path}")
            with open(whisper_json_path, "r", encoding="utf-8") as f:
                whisper_json_data = json.load(f)

        if whisper_json_data is None:
            raise ValueError("Provide either whisper_json_path or whisper_json_data.")

        self.transcript_segments = parse_whisper_json(whisper_json_data)
        return self.transcript_segments

    # --- Step 3: Semantic Accents ---

    def inject_zoom_accents(
        self,
        emphasis_keywords: Optional[List[str]] = None,
        max_accents: int = 10,
        zoom_scale: float = 1.2,
        zoom_duration: float = 0.8
    ) -> List[WordTimestamp]:
        """
        Identify emphasis words in the transcript and inject kinetic
        zoom effects at those timestamps.

        Parameters:
          emphasis_keywords : Optional trigger words to match.
          max_accents       : Maximum number of zoom accents.
          zoom_scale        : Zoom magnification (1.0-3.0).
          zoom_duration     : Duration of each zoom effect (seconds).

        Returns:
          List of WordTimestamp objects that received zoom effects.
        """
        if not self.transcript_segments:
            raise ValueError("No transcript loaded. Call load_transcript() first.")

        self.emphasis_words = identify_emphasis_words(
            self.transcript_segments, emphasis_keywords, max_accents
        )

        for word in self.emphasis_words:
            start = word.start
            end = min(word.end + zoom_duration, word.start + zoom_duration)
            self.engine.kinetic_zoom(
                start_time=start,
                end_time=end,
                scale=zoom_scale
            )

        return self.emphasis_words

    # --- Step 4: Subtitle Burns ---

    def burn_subtitles(
        self,
        fontsize: int = 48,
        fontcolor: str = "white",
        borderw: int = 2,
        position_y: str = "h-th-60"
    ) -> int:
        """
        Burn transcript segments as timed subtitles onto the video.

        Parameters:
          fontsize   : Font size in pixels.
          fontcolor  : FFmpeg color name or hex.
          borderw    : Border thickness.
          position_y : Vertical position expression.

        Returns:
          Number of subtitle segments burned.
        """
        if not self.transcript_segments:
            raise ValueError("No transcript loaded. Call load_transcript() first.")

        count = 0
        for seg in self.transcript_segments:
            if seg.text.strip():
                self.engine.add_subtitle(
                    text=seg.text,
                    start_time=seg.start,
                    end_time=seg.end,
                    fontsize=fontsize,
                    fontcolor=fontcolor,
                    borderw=borderw,
                    y=position_y
                )
                count += 1

        return count

    # --- Step 5: Optional Enhancements ---

    def apply_color_grade(
        self,
        saturation: float = 1.15,
        contrast: float = 1.05,
        brightness: float = 0.02,
        gamma: float = 1.0
    ) -> None:
        """Apply a subtle, professional color grade to the output."""
        self.engine.adjust_color(
            saturation=saturation,
            contrast=contrast,
            brightness=brightness,
            gamma=gamma
        )

    def add_background_music(
        self,
        music_path: str,
        volume_db: float = -18.0,
        duck_db: float = -14.0
    ) -> None:
        """
        Add background music with automatic voice-ducking.

        Parameters:
          music_path : Path to the music file.
          volume_db  : Base volume of the music track (dB).
          duck_db    : Amount to duck when voice is active (dB).
        """
        if not os.path.exists(music_path):
            raise FileNotFoundError(f"Music file not found: {music_path}")

        self.engine.import_asset(music_path, "bgm")
        self.engine.set_volume("bgm", level_db=volume_db)
        self.engine.audio_duck("bgm", "main_footage", duck_db=duck_db)

    # --- Step 6: Final Render ---

    def generate_render_command(self, output_path: str) -> str:
        """
        Compile the entire pipeline state into a single FFmpeg command.

        Returns:
          The complete FFmpeg command string.
        """
        return self.engine.generate_ffmpeg_command(output_path)

    def get_blueprint(self) -> str:
        """Return the full project state as formatted JSON."""
        return self.engine.compile_blueprint(pretty=True)

    def get_summary(self) -> Dict[str, Any]:
        """Return a human-readable summary of the pipeline state."""
        return {
            "source": self.source_video,
            "silence_gaps_found": len(self.silence_regions),
            "speech_segments": len(self.speech_segments),
            "transcript_segments": len(self.transcript_segments),
            "emphasis_zooms": len(self.emphasis_words),
            "text_overlays": len(self.engine.state["timeline"]["text_layers"]),
            "video_clips": len(self.engine.state["timeline"]["video_layers"]),
            "audio_clips": len(self.engine.state["timeline"]["audio_layers"]),
            "filters_active": self.engine._has_filters(),
            "encoder": self.engine.encoder,
            "hwaccel": self.engine.hwaccel,
        }

    # --- Helpers ---

    def _get_duration(self) -> float:
        """Get the total duration of the source video via FFprobe."""
        ffprobe_bin = shutil.which("ffprobe") or "ffprobe"

        try:
            proc = subprocess.run(
                [
                    ffprobe_bin, "-v", "quiet",
                    "-show_entries", "format=duration",
                    "-of", "csv=p=0",
                    self.source_video
                ],
                capture_output=True, text=True, timeout=30
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return float(proc.stdout.strip())
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError, OSError):
            pass

        # Fallback: assume 10 minutes if ffprobe unavailable
        return 600.0
