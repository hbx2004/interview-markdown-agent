from __future__ import annotations

import subprocess
from pathlib import Path


class AudioProcessingError(RuntimeError):
    pass


class AudioProcessor:
    def normalize_to_wav(self, source_path: Path, target_path: Path) -> Path:
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(target_path),
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise AudioProcessingError("未检测到 ffmpeg，请先安装并加入 PATH。") from exc

        if completed.returncode != 0:
            raise AudioProcessingError(completed.stderr.strip() or "ffmpeg 音频处理失败。")
        return target_path
