"""进度管理模块"""

from __future__ import annotations

import json
import time
from pathlib import Path

PROGRESS_FILE = Path(__file__).parent.parent / ".sf_progress.json"
FAILED_FILE = Path(__file__).parent.parent / ".sf_failed.json"


def load_progress() -> set[str]:
    """加载已完成的单号集合。"""
    if not PROGRESS_FILE.exists():
        return set()
    try:
        data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        return set(data.get("completed", []))
    except Exception:
        return set()


def save_progress(tracking_number: str) -> None:
    """保存完成的单号到进度文件。"""
    completed = load_progress()
    completed.add(tracking_number)
    payload = {
        "completed": sorted(completed),
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    tmp = PROGRESS_FILE.with_suffix(".json.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(PROGRESS_FILE)


def save_failed(tracking_number: str, reason: str) -> None:
    """保存失败的单号到失败记录文件。"""
    entries: list[dict] = []
    if FAILED_FILE.exists():
        try:
            entries = json.loads(FAILED_FILE.read_text(encoding="utf-8"))
        except Exception:
            entries = []

    entries.append({
        "tracking_number": tracking_number,
        "reason": reason,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    })

    text = json.dumps(entries, ensure_ascii=False, indent=2)
    tmp = FAILED_FILE.with_suffix(".json.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(FAILED_FILE)