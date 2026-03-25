import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

BASE_DIR = "D:/WISSLIST"
LIBRARY_JSON = Path(BASE_DIR) / "media_library" / "library.json"

import json

def load_library():
    if LIBRARY_JSON.exists():
        with open(LIBRARY_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_library(library):
    with open(LIBRARY_JSON, "w", encoding="utf-8") as f:
        json.dump(library, f, ensure_ascii=False, indent=2)

def show_stats(library):
    providers = {}
    categories = {}
    missing = 0
    for item in library:
        p = item.get("provider", "unknown")
        c = item.get("category", "unknown")
        providers[p] = providers.get(p, 0) + 1
        categories[c] = categories.get(c, 0) + 1
        if not Path(item["file"]).exists():
            missing += 1
    print(f"\n📊 라이브러리 통계")
    print(f"   전체 항목 : {len(library)}개")
    print(f"   파일 없음 : {missing}개  ← 정리 대상")
    print(f"\n   소스별:")
    for p, cnt in sorted(providers.items(), key=lambda x: -x[1]):
        print(f"     {p:15s}: {cnt}개")
    print(f"\n   카테고리별:")
    for c, cnt in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"     {c:20s}: {cnt}개")

def scan_orphans(library):
    orphans = [item for item in library if not Path(item["file"]).exists()]
    if not orphans:
        print("\n✅ 정리할 항목 없음 (모든 파일이 존재합니다)")
        return []
    print(f"\n🔍 삭제 대상 {len(orphans)}개 (파일이 없는 항목):")
    for item in orphans:
        print(f"   - {item['file']}")
    return orphans

def cleanup(library):
    before = len(library)
    cleaned = [item for item in library if Path(item["file"]).exists()]
    removed = before - len(cleaned)
    if removed == 0:
        print("\n✅ 정리할 항목 없음")
        return
    save_library(cleaned)
    print(f"\n✅ 완료: {before}개 → {len(cleaned)}개 ({removed}개 제거)")

def main():
    library = load_library()
    if "--stats" in sys.argv:
        show_stats(library)
        return
    if "--scan" in sys.argv:
        scan_orphans(library)
        return
    orphans = scan_orphans(library)
    if not orphans:
        show_stats(library)
        return
    print()
    try:
        confirm = input(f"위 {len(orphans)}개 항목을 library.json에서 제거할까요? (y/n): ").strip().lower()
    except EOFError:
        confirm = "n"
    if confirm == "y":
        cleanup(library)
        show_stats(load_library())
    else:
        print("취소됨.")

if __name__ == "__main__":
    main()
