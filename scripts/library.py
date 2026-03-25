# =============================================
# WISSLIST - library.json 읽기/쓰기 공통 모듈
# =============================================

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from config import BASE_DIR

LIBRARY_JSON = Path(BASE_DIR) / "media_library" / "library.json"


def load_library() -> list:
    if LIBRARY_JSON.exists():
        with open(LIBRARY_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_library(library: list):
    LIBRARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(LIBRARY_JSON, "w", encoding="utf-8") as f:
        json.dump(library, f, ensure_ascii=False, indent=2)


def get_existing_sources() -> set:
    """중복 방지용 — 이미 저장된 source URL 집합 반환"""
    return {item.get("source", "") for item in load_library()}


def get_existing_files() -> set:
    """중복 방지용 — 이미 저장된 파일 경로 집합 반환"""
    return {item.get("file", "") for item in load_library()}


def add_entry(entry: dict):
    """항목 1개 추가 후 즉시 저장"""
    library = load_library()
    library.append(entry)
    save_library(library)


def stats() -> dict:
    library = load_library()
    providers = {}
    for item in library:
        p = item.get("provider", "unknown")
        providers[p] = providers.get(p, 0) + 1
    return {"total": len(library), "by_provider": providers}
