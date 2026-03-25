# =============================================
# WISSLIST - 미디어 매칭
# =============================================

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import BASE_DIR, PEXELS_API_KEY
from library import load_library, add_entry

BASE = Path(BASE_DIR)


def find_best_media(visual_tags: list, exclude_files: set = None) -> dict | None:
    if exclude_files is None:
        exclude_files = set()

    library = load_library()
    scored  = []

    for item in library:
        if item["file"] in exclude_files:
            continue
        if not Path(item["file"]).exists():
            continue
        score = len(set(visual_tags) & set(item["all_tags"]))
        if score > 0:
            scored.append((score, item))

    if not scored:
        print(f"  ⚠️  태그 매칭 없음 → Pexels 실시간 검색: {visual_tags[0]}")
        return _fallback_pexels(visual_tags[0])

    max_score    = max(s for s, _ in scored)
    top_matches  = [item for score, item in scored if score == max_score]
    chosen       = random.choice(top_matches)
    print(f"  🎯 매칭: {Path(chosen['file']).name} (점수:{max_score})")
    return chosen


def _fallback_pexels(query: str) -> dict | None:
    import requests
    headers   = {"Authorization": PEXELS_API_KEY}
    url       = f"https://api.pexels.com/v1/search?query={query}&per_page=1"
    fallback_dir = BASE / "media_library" / "fallback"
    fallback_dir.mkdir(parents=True, exist_ok=True)
    try:
        res   = requests.get(url, headers=headers, timeout=10).json()
        photo = res["photos"][0]
        path  = fallback_dir / f"pxl_{photo['id']}.jpg"
        data  = requests.get(photo["src"]["large"], timeout=15).content
        with open(path, "wb") as f:
            f.write(data)
        entry = {
            "file": str(path), "category": "fallback",
            "source": photo.get("url",""), "query": query,
            "provider": "pexels", "all_tags": [query],
            "clip_verified": False,
        }
        add_entry(entry)
        print(f"  📥 폴백 저장: {path.name}")
        return entry
    except Exception as e:
        print(f"  ❌ 폴백 실패: {e}")
        return None
