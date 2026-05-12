"""Video metadata yardımcıları (ffprobe sarmalayıcısı)."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


def probe_duration_seconds(data: bytes, suffix: str = "") -> int | None:
    """Video byte'larından süreyi (saniye, int) tespit eder.

    ffprobe yoksa veya parse edemezse `None` döner. Çağıran taraf bu
    durumda video'yu reddetmek yerine duration'ı NULL bırakabilir.
    """
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_entries",
                "format=duration",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        payload = json.loads(result.stdout or "{}")
        dur = payload.get("format", {}).get("duration")
        if dur is None:
            return None
        return int(round(float(dur)))
    except (
        FileNotFoundError,
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
        ValueError,
    ):
        return None
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass
