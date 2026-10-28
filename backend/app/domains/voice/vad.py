"""
CogniCompanion — Real-Time Voice Activity Detector (VAD) & Barge-In Engine
===========================================================================
Pure Python, zero-dependency, sub-millisecond audio frame analyzer.
Detects:
  1. Speech Onset: user began talking (used for instantaneous barge-in interruption).
  2. Speech Cessation: user finished talking (used for turn-taking completion).
"""

import math
import struct


class FrameVAD:
    """
    Analyzes 16kHz, 16-bit mono PCM audio frames for voice energy.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        energy_threshold: float = 450.0,
        silence_duration_sec: float = 0.85,
    ) -> None:
        self.sample_rate = sample_rate
        self.energy_threshold = energy_threshold
        self.silence_duration_sec = silence_duration_sec

        self._consecutive_speech_frames = 0
        self._consecutive_silence_frames = 0
        self._speech_active = False

    def reset(self) -> None:
        """Reset internal frame counters."""
        self._consecutive_speech_frames = 0
        self._consecutive_silence_frames = 0
        self._speech_active = False

    def calculate_rms(self, pcm_bytes: bytes) -> float:
        """Calculate Root Mean Square (RMS) energy of 16-bit PCM samples."""
        num_samples = len(pcm_bytes) // 2
        if num_samples == 0:
            return 0.0

        fmt = f"<{num_samples}h"
        try:
            samples = struct.unpack(fmt, pcm_bytes[: num_samples * 2])
        except struct.error:
            return 0.0

        sum_squares = sum(s * s for s in samples)
        return math.sqrt(sum_squares / num_samples)

    def process_frame(self, pcm_bytes: bytes) -> tuple[bool, bool]:
        """
        Processes a raw PCM frame.

        Returns:
            (is_speaking, turn_completed)
            - is_speaking: True if active voice is detected in this frame.
            - turn_completed: True if user finished speaking and pause duration exceeded.
        """
        rms = self.calculate_rms(pcm_bytes)
        is_frame_voiced = rms >= self.energy_threshold

        frame_duration = len(pcm_bytes) / (self.sample_rate * 2)

        if is_frame_voiced:
            self._consecutive_speech_frames += 1
            self._consecutive_silence_frames = 0

            # 2 consecutive voiced frames confirms speech onset
            if self._consecutive_speech_frames >= 2:
                self._speech_active = True

            return True, False
        else:
            self._consecutive_speech_frames = 0
            if self._speech_active:
                self._consecutive_silence_frames += 1
                silence_elapsed = self._consecutive_silence_frames * frame_duration

                if silence_elapsed >= self.silence_duration_sec:
                    # User was speaking and has now paused long enough -> turn complete
                    self._speech_active = False
                    self._consecutive_silence_frames = 0
                    return False, True

            return False, False
