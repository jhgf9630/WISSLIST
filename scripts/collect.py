# =============================================
# WISSLIST - 미디어 수집 메인 실행 파일
#
# 사용법:
#   python collect.py                    → 대화형 메뉴
#   python collect.py pexels             → Pexels만
#   python collect.py pixabay            → Pixabay만
#   python collect.py giphy              → Giphy만
#   python collect.py wikimedia          → Wikimedia만
#   python collect.py all                → 전체 소스
#   python collect.py pexels pixabay     → 여러 소스 조합
#   python collect.py giphy --count 10   → 카테고리당 10개
# =============================================

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import BASE_DIR
from tag_map import CATEGORY_QUERIES, GIF_CATEGORY_QUERIES
from collectors import collect_pexels, collect_pixabay, collect_giphy, collect_wikimedia
from library import stats

BASE = Path(BASE_DIR)

WIKIMEDIA_QUERIES = {
    "text_bg":   ["white background plain", "minimal background"],
    "food":      ["Korean cuisine dish food"],
    "kitchen":   ["kitchen cooking utensil appliance"],
    "lifestyle": ["home interior living room"],
}

SOURCES = ["pexels", "pixabay", "giphy", "wikimedia"]
SOURCE_LABELS = {
    "pexels":    "Pexels    (이미지+영상, 고품질, 무제한)",
    "pixabay":   "Pixabay   (이미지, 일러스트 포함, 100건/일)",
    "giphy":     "Giphy     (GIF 짤 특화, 42건/일) ⭐추천",
    "wikimedia": "Wikimedia (공공 이미지, API키 불필요, 무제한)",
}


def check_usb():
    if not BASE.exists():
        print("❌ D드라이브(USB)가 연결되지 않았습니다. 연결 후 다시 실행하세요.")
        sys.exit(1)


def make_folders():
    for cat in CATEGORY_QUERIES:
        (BASE / "media_library" / cat).mkdir(parents=True, exist_ok=True)
    for cat in GIF_CATEGORY_QUERIES:
        (BASE / "media_library" / "gif" / cat).mkdir(parents=True, exist_ok=True)
    for folder in ["audio", "output", "scripts_json", "logs", "scripts"]:
        (BASE / folder).mkdir(exist_ok=True)


def run_pexels(count):
    print("\n📸 [Pexels 수집 시작]")
    total = 0
    for category, queries in CATEGORY_QUERIES.items():
        print(f"  📂 {category}")
        for q in queries:
            print(f"    🔍 {q}")
            total += collect_pexels(q, category, count=count)
    print(f"  → Pexels 신규 저장: {total}개")


def run_pixabay(count):
    print("\n🖼️  [Pixabay 수집 시작]")
    total = 0
    for category, queries in CATEGORY_QUERIES.items():
        print(f"  📂 {category}")
        for q in queries[:2]:          # Pixabay는 하루 한도 고려해 쿼리당 2개
            print(f"    🔍 {q}")
            total += collect_pixabay(q, category, count=count)
    print(f"  → Pixabay 신규 저장: {total}개")


def run_giphy(count):
    print("\n🎭 [Giphy GIF 수집 시작]")
    total = 0
    for category, queries in GIF_CATEGORY_QUERIES.items():
        print(f"  📂 gif/{category}")
        for q in queries:
            print(f"    🔍 {q}")
            total += collect_giphy(q, category, count=count)
    print(f"  → Giphy 신규 저장: {total}개")


def run_wikimedia(count):
    print("\n🌐 [Wikimedia 수집 시작]")
    total = 0
    for category, queries in WIKIMEDIA_QUERIES.items():
        print(f"  📂 {category}")
        for q in queries:
            print(f"    🔍 {q}")
            total += collect_wikimedia(q, category, count=count)
    print(f"  → Wikimedia 신규 저장: {total}개")


RUNNER_MAP = {
    "pexels":    run_pexels,
    "pixabay":   run_pixabay,
    "giphy":     run_giphy,
    "wikimedia": run_wikimedia,
}


def interactive_menu(count):
    """인자 없이 실행 시 대화형 메뉴"""
    print("\n" + "=" * 52)
    print("🎬  WISSLIST — 미디어 수집 소스 선택")
    print("=" * 52)
    for i, src in enumerate(SOURCES, 1):
        print(f"  {i}. {SOURCE_LABELS[src]}")
    print(f"  5. 전체 소스 한 번에 실행")
    print(f"  0. 취소")
    print("=" * 52)

    choice = input("번호 입력 (복수 선택 예: 1 3): ").strip()

    if choice == "0":
        print("취소됨.")
        return []

    selected = []
    if choice == "5":
        selected = SOURCES[:]
    else:
        for c in choice.split():
            try:
                idx = int(c) - 1
                if 0 <= idx < len(SOURCES):
                    selected.append(SOURCES[idx])
            except ValueError:
                pass

    if not selected:
        print("⚠️  올바른 번호를 입력하세요.")
        return []

    print(f"\n선택된 소스: {', '.join(selected)}")
    confirm = input("진행할까요? (y/n): ").strip().lower()
    if confirm != "y":
        print("취소됨.")
        return []

    return selected


def main():
    parser = argparse.ArgumentParser(
        description="WISSLIST 미디어 수집기",
        add_help=True,
    )
    parser.add_argument(
        "sources", nargs="*",
        help="수집 소스: pexels pixabay giphy wikimedia all"
    )
    parser.add_argument(
        "--count", "-c", type=int, default=3,
        help="카테고리당 수집 개수 (기본값: 3)"
    )
    args = parser.parse_args()

    check_usb()
    make_folders()

    # 소스 결정
    if not args.sources:
        selected = interactive_menu(args.count)
    elif "all" in args.sources:
        selected = SOURCES[:]
    else:
        selected = []
        for s in args.sources:
            if s in SOURCES:
                selected.append(s)
            else:
                print(f"⚠️  알 수 없는 소스: {s} (무시됨)")

    if not selected:
        return

    # 수집 실행
    print(f"\n📦 수집 시작 | 소스: {', '.join(selected)} | 개수: {args.count}개/카테고리")
    print("=" * 52)

    for src in selected:
        RUNNER_MAP[src](args.count)

    # 최종 통계
    s = stats()
    print("\n" + "=" * 52)
    print(f"✅ 수집 완료!")
    print(f"   총 라이브러리: {s['total']}개")
    for provider, cnt in s["by_provider"].items():
        print(f"   {provider:12s}: {cnt}개")
    print("=" * 52)


if __name__ == "__main__":
    main()
