"""Log tailer module: tails and parses structured (JSON) log files in real time."""

import json
import os
import time
from typing import Callable, Generator, Optional


class LogTailer:
    """Tails a log file and yields parsed log entries as they are written."""

    def __init__(
        self,
        filepath: str,
        service_name: str,
        poll_interval: float = 0.2,
        seek_end: bool = True,
    ) -> None:
        self.filepath = filepath
        self.service_name = service_name
        self.poll_interval = poll_interval
        self._seek_end = seek_end

    def _open_file(self):
        f = open(self.filepath, "r", encoding="utf-8")
        if self._seek_end:
            f.seek(0, os.SEEK_END)
        return f

    def tail(self) -> Generator[dict, None, None]:
        """Generator that yields parsed log line dicts as they appear.

        Handles file rotation by reopening the file if it is replaced or
        truncated (i.e. the current seek position is beyond the file size).
        """
        with self._open_file() as f:
            while True:
                # Detect file rotation or truncation
                try:
                    current_pos = f.tell()
                    file_size = os.path.getsize(self.filepath)
                    if file_size < current_pos:
                        f.seek(0)
                except OSError:
                    pass

                line = f.readline()
                if not line:
                    time.sleep(self.poll_interval)
                    continue
                line = line.strip()
                if not line:
                    continue
                entry = self._parse_line(line)
                if entry is not None:
                    yield entry

    def _parse_line(self, line: str) -> Optional[dict]:
        try:
            entry = json.loads(line)
            entry.setdefault("service", self.service_name)
            return entry
        except json.JSONDecodeError:
            # Non-JSON lines are wrapped in a minimal structure
            return {
                "service": self.service_name,
                "level": "unknown",
                "message": line,
            }
