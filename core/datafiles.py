"""데이터 파일 안전 쓰기·백업·감사 로그·스냅샷 해시 (core 유틸).

- 원자적 쓰기: 임시 파일에 쓰고 os.replace 로 교체, 실패 시 원본 보존.
- 백업: data/backup/ 에 타임스탬프 사본.
- 감사 로그: data/audit_log.csv 에 (시각, 동작, key, 이전값, 새값, 파일명).
- 스냅샷 해시: 파일 SHA-256 (재현성).
"""

from __future__ import annotations

import csv
import hashlib
import os
import shutil
import tempfile
from datetime import datetime, timezone


def sha256_file(path: str) -> str:
    """파일의 SHA-256 (없으면 'FILE_NOT_FOUND')."""
    if not os.path.exists(path):
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_write(path: str, content: str) -> None:
    """임시 파일에 쓴 뒤 교체(원자적). 실패 시 예외를 올려 롤백 가능하게 한다."""
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        os.replace(tmp, path)   # 원자적 교체
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def backup_file(path: str, backup_dir: str) -> str | None:
    """path 를 backup_dir 에 타임스탬프 사본으로 저장. 반환: 백업 경로(없으면 None)."""
    if not os.path.exists(path):
        return None
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = os.path.basename(path)
    dest = os.path.join(backup_dir, f"{base}.{ts}.bak")
    shutil.copy2(path, dest)
    return dest


AUDIT_HEADER = ["timestamp", "action", "key", "old_value", "new_value", "file"]


def append_audit(audit_path: str, action: str, key: str,
                 old_value: str, new_value: str, file: str) -> None:
    """감사 로그에 한 줄 추가 (없으면 헤더 생성)."""
    os.makedirs(os.path.dirname(os.path.abspath(audit_path)), exist_ok=True)
    exists = os.path.exists(audit_path)
    ts = datetime.now(timezone.utc).isoformat()
    with open(audit_path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(AUDIT_HEADER)
        w.writerow([ts, action, key, old_value, new_value, file])
