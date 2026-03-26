# =============================================
# WISSLIST - 커스텀 이미지 임포터
#
# 사용법:
#   python import_custom.py                     일반 이미지 등록
#   python import_custom.py --product 안성탕면  제품 이미지로 등록 (우선 매칭)
#
# 제품 이미지로 등록하면:
#   - all_tags에 "제품이미지", "제품명(안성탕면)" 태그 자동 추가
#   - 스크립트에서 "제품이미지" 태그 쓰면 이 이미지가 우선 매칭
# =============================================

import sys
import shutil
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import BASE_DIR
from library import load_library, add_entry, get_existing_files

BASE       = Path(BASE_DIR)
IMPORT_DIR = BASE / "media_library" / "import_here"
CUSTOM_DIR = BASE / "media_library" / "custom"
PRODUCT_DIR = BASE / "media_library" / "product"

SUPPORTED = {".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov", ".webp"}


def run(product_name: str = None):
    if not BASE.exists():
        print("❌ D드라이브(USB) 연결 확인")
        return

    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
    PRODUCT_DIR.mkdir(parents=True, exist_ok=True)

    files = [f for f in IMPORT_DIR.iterdir()
             if f.suffix.lower() in SUPPORTED]

    if not files:
        print(f"\n import_here 폴더가 비어있습니다.")
        print(f"   경로: {IMPORT_DIR}")
        return

    existing = get_existing_files()
    added = 0

    # 저장 폴더 결정
    dest_dir  = PRODUCT_DIR if product_name else CUSTOM_DIR
    category  = "product" if product_name else "custom"

    if product_name:
        print(f"\n 제품 이미지 임포트: '{product_name}' ({len(files)}개 발견)")
        print(f"   → 'product' 카테고리, '제품이미지' 태그 자동 추가")
    else:
        print(f"\n 커스텀 이미지 임포트: {len(files)}개 발견")

    for f in files:
        dest = dest_dir / f.name
        counter = 1
        while dest.exists():
            dest = dest_dir / f"{f.stem}_{counter}{f.suffix}"
            counter += 1

        if str(dest) in existing:
            print(f"  건너뜀: {f.name}")
            continue

        shutil.move(str(f), str(dest))

        # ── 태그 구성 ───────────────────────────────────────────
        if product_name:
            # 제품 이미지: "제품이미지" 태그 포함 → 스크립트 매칭 보장
            tags = [
                "product",
                "제품이미지",        # ← 스크립트의 visual_tag와 매칭되는 핵심 태그
                "제품단독",
                "제품등장",
                "식품패키지",
                product_name,        # 제품명 태그 (예: "안성탕면")
            ]
            # 제품 카테고리별 추가 태그
            tags += _get_product_tags(product_name)
        else:
            tags = ["custom"]

        entry = {
            "file":          str(dest),
            "category":      category,
            "source":        "manual_import",
            "query":         product_name or "",
            "provider":      "custom",
            "all_tags":      list(set(tags)),
            "clip_verified": False,
        }
        add_entry(entry)
        tag_preview = ", ".join(tags[:4])
        print(f"  ✅ 등록: {dest.name}  [{tag_preview}...]")
        added += 1

    print(f"\n 임포트 완료: {added}개 등록")
    if product_name:
        print(f"\n 이제 스크립트의 제품 등장 장면 visual_tag에 '제품이미지' 또는 '{product_name}' 추가하면")
        print(f"   방금 등록한 이미지가 우선 매칭됩니다.")
    if added > 0 and not product_name:
        print(f"\n 다음 단계 (선택): CLIP 태그 분석")
        print(f"   python D:/WISSLIST/scripts/clip_tagger.py")


def _get_product_tags(keyword: str) -> list:
    kw = keyword.lower()
    tag_map = {
        "라면":        ["라면", "음식클로즈업", "식품패키지"],
        "컵라면":      ["컵라면", "라면", "편의점음식"],
        "탕면":        ["라면", "음식클로즈업", "따뜻한계열"],
        "치킨":        ["치킨", "음식클로즈업", "배달음식"],
        "피자":        ["피자", "음식클로즈업", "배달음식"],
        "에어프라이어": ["에어프라이어", "소형가전", "가전제품"],
        "전자레인지":  ["전자레인지", "가전제품"],
        "청소기":      ["청소기", "가전제품"],
        "커피":        ["커피머신", "카페분위기"],
        "스킨케어":    ["스킨케어", "뷰티제품"],
        "샴푸":        ["샴푸", "뷰티제품"],
        "냉동":        ["냉동식품", "간편식"],
        "간편식":      ["간편식", "편의점음식"],
        "과자":        ["편의점음식", "간편식"],
        "음료":        ["편의점음식", "음식클로즈업"],
    }
    tags = []
    for k, v in tag_map.items():
        if k in kw:
            tags.extend(v)
    return list(set(tags))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="커스텀 이미지 등록")
    parser.add_argument("--product", "-p", type=str, default=None,
                        help="제품명 (지정 시 제품이미지 태그 자동 추가)")
    args = parser.parse_args()
    run(product_name=args.product)
