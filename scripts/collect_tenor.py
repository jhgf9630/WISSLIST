# =============================================
# WISSLIST - Tenor GIF 수집기
# 실행: python collect_tenor.py
#       python collect_tenor.py "surprised reaction" --count 10
#
# Tenor API 키 발급:
#   https://developers.google.com/tenor/guides/quickstart
#   (Google 계정으로 무료 발급, 하루 쿼리 제한 없음)
#
# config.py에 TENOR_API_KEY 추가 필요
# =============================================

import sys
import time
import requests
import argparse
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))
from config import BASE_DIR
from library import get_existing_sources, add_entry

BASE    = Path(BASE_DIR)
GIF_DIR = BASE / "media_library" / "gif"

# Tenor에서 리액션 GIF 검색어 목록 (연예인 얼굴 없는 익명 리액션)
TENOR_QUERIES = {
    "reaction_gif": [
        "funny reaction",
        "shocked reaction",
        "excited reaction",
        "satisfied eating",
        "delicious food reaction",
        "wow amazing reaction",
        "happy surprised",
        "thumbs up reaction",
        "mind blown",
        "person eating noodles",
        "eating delicious",
        "nodding yes",
        "clapping reaction",
        "omg no way",
    ],
    "food_gif": [
        "cooking noodles",
        "ramen eating",
        "food delicious",
        "cheese pull",
        "steaming food",
    ],
}

# visual_tag 매핑
QUERY_TAG_MAP = {
    "funny reaction":        ["인물리액션", "유머러스한", "훅배경"],
    "shocked reaction":      ["놀란표정", "황당한", "인물리액션"],
    "excited reaction":      ["기쁜표정", "신나는", "인물리액션"],
    "satisfied eating":      ["만족표정", "혼자식사", "만족스러운"],
    "delicious food reaction":["인물리액션", "유머러스한", "음식클로즈업"],
    "wow amazing reaction":  ["놀란표정", "황당한", "역동적인"],
    "happy surprised":       ["기쁜표정", "황당한", "인물리액션"],
    "thumbs up reaction":    ["기쁜표정", "뿌듯한", "해결완료"],
    "mind blown":            ["놀란표정", "황당한", "어이없는"],
    "person eating noodles": ["혼자식사", "유머러스한", "라면"],
    "eating delicious":      ["혼자식사", "만족스러운", "음식클로즈업"],
    "nodding yes":           ["인물리액션", "공감가는", "만족스러운"],
    "clapping reaction":     ["기쁜표정", "신나는", "인물리액션"],
    "omg no way":            ["놀란표정", "황당한", "어이없는"],
    "cooking noodles":       ["라면조리", "조리과정", "주방조리"],
    "ramen eating":          ["혼자식사", "라면", "만족스러운"],
    "food delicious":        ["음식클로즈업", "만족스러운", "음식풍부한색감"],
    "cheese pull":           ["음식클로즈업", "음식풍부한색감", "신나는"],
    "steaming food":         ["음식클로즈업", "따뜻한계열", "음식완성샷"],
}


def get_api_key():
    try:
        from config import TENOR_API_KEY
        return TENOR_API_KEY
    except ImportError:
        return None


def collect_tenor(query: str, category: str,
                  count: int = 5, api_key: str = None) -> int:
    if not api_key:
        print("  ⚠️  TENOR_API_KEY 미설정 → config.py에 추가 필요")
        print("      https://developers.google.com/tenor/guides/quickstart")
        return 0

    url = (
        f"https://tenor.googleapis.com/v2/search"
        f"?q={quote(query)}"
        f"&key={api_key}"
        f"&limit={count}"
        f"&media_filter=gif"
        f"&contentfilter=medium"
    )
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            print(f"  ⚠️  Tenor API 오류: {resp.status_code}")
            return 0
        data = resp.json()
    except Exception as e:
        print(f"  ⚠️  Tenor 요청 실패: {e}")
        return 0

    save_dir = GIF_DIR / category
    save_dir.mkdir(parents=True, exist_ok=True)
    existing = get_existing_sources()

    saved = 0
    for item in data.get("results", []):
        src_url = item.get("url", "")
        if src_url in existing:
            print(f"  ↩️  중복: {item['id']}")
            continue

        # 최적 GIF URL 선택 (mediumgif 또는 gif)
        formats = item.get("media_formats", {})
        gif_info = formats.get("mediumgif") or formats.get("gif") or {}
        gif_url  = gif_info.get("url", "")
        if not gif_url:
            continue

        file_name = f"tenor_{item['id']}.gif"
        file_path = save_dir / file_name
        if file_path.exists():
            print(f"  ↩️  파일 중복: {file_name}")
            continue

        try:
            data_bytes = requests.get(gif_url, timeout=20).content
            file_path.write_bytes(data_bytes)
        except Exception as e:
            print(f"  ⚠️  다운로드 실패: {e}")
            continue

        tags = QUERY_TAG_MAP.get(query, [category, "인물리액션"])
        entry = {
            "file":          str(file_path),
            "category":      "gif_" + category,
            "source":        src_url,
            "query":         query,
            "provider":      "tenor",
            "all_tags":      list(set(["gif", "유머러스한"] + tags)),
            "clip_verified": False,
        }
        add_entry(entry)
        print(f"  ✅  Tenor GIF 저장: {file_name}")
        saved += 1
        time.sleep(0.3)

    return saved


def run(queries: dict = None, count: int = 5):
    api_key = get_api_key()
    if not api_key:
        print("\n⚠️  Tenor API 키가 없습니다.")
        print("   1. https://developers.google.com/tenor/guides/quickstart 접속")
        print("   2. Google 계정으로 API 키 발급 (무료)")
        print("   3. config.py에 TENOR_API_KEY = '발급받은키' 추가")
        return

    if queries is None:
        queries = TENOR_QUERIES

    total = 0
    for category, query_list in queries.items():
        print(f"\n  📂 gif/{category}")
        for q in query_list:
            print(f"    🔍 {q}")
            total += collect_tenor(q, category, count=count, api_key=api_key)

    print(f"\n✅ Tenor 수집 완료: {total}개")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tenor GIF 수집")
    parser.add_argument("query", nargs="?", help="검색어 (없으면 전체 쿼리 실행)")
    parser.add_argument("--count", "-c", type=int, default=5)
    parser.add_argument("--category", default="reaction_gif")
    args = parser.parse_args()

    if not BASE.exists():
        print("❌ D드라이브(USB) 연결 확인")
        sys.exit(1)

    if args.query:
        api_key = get_api_key()
        collect_tenor(args.query, args.category, args.count, api_key)
    else:
        run(count=args.count)
