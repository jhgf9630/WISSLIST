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
#
# ⚠️  이미 등록된 파일도 --product 옵션 주면 태그가 업데이트됩니다
# =============================================

import sys
import shutil
import argparse
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import BASE_DIR
from library import load_library, save_library, add_entry

BASE        = Path(BASE_DIR)
IMPORT_DIR  = BASE / "media_library" / "import_here"
CUSTOM_DIR  = BASE / "media_library" / "custom"
PRODUCT_DIR = BASE / "media_library" / "product"

SUPPORTED = {".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov", ".webp"}


def _get_product_tags(keyword: str) -> list:
    kw = keyword.lower()
    tag_map = {
        "라면":        ["라면", "음식클로즈업", "식품패키지"],
        "컵라면":      ["컵라면", "라면", "편의점음식"],
        "탕면":        ["라면", "음식클로즈업", "따뜻한계열"],
        "불닭":        ["라면", "음식클로즈업", "비비드컬러"],
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


def _build_product_tags(product_name: str) -> list:
    tags = [
        "product",
        "제품이미지",   # 스크립트 매칭 핵심 태그
        "제품단독",
        "제품등장",
        "식품패키지",
        product_name,
    ]
    tags += _get_product_tags(product_name)
    return list(set(tags))


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

    if product_name:
        print(f"\n 제품 이미지 임포트: '{product_name}' ({len(files)}개 발견)")
        print(f"   → '제품이미지', '{product_name}' 태그 자동 추가")
        print(f"   → 이미 등록된 파일은 태그만 업데이트됩니다")
    else:
        print(f"\n 커스텀 이미지 임포트: {len(files)}개 발견")

    library = load_library()
    # 파일명 → library 인덱스 맵 (빠른 검색용)
    name_to_idx = {}
    for idx, item in enumerate(library):
        name_to_idx[Path(item["file"]).name.lower()] = idx

    dest_dir = PRODUCT_DIR if product_name else CUSTOM_DIR
    category = "product" if product_name else "custom"

    added   = 0
    updated = 0

    for f in files:
        fname_lower = f.name.lower()

        # ── 이미 library에 등록된 파일인지 파일명으로 확인 ──────────
        if fname_lower in name_to_idx:
            idx  = name_to_idx[fname_lower]
            item = library[idx]
            existing_path = Path(item["file"])

            if product_name:
                # 제품 이미지 태그로 업데이트
                new_tags = _build_product_tags(product_name)
                item["all_tags"]  = list(set(item["all_tags"]) | set(new_tags))
                item["category"]  = "product"
                item["query"]     = product_name

                # 파일이 product 폴더에 없으면 이동
                if existing_path.parent != PRODUCT_DIR and existing_path.exists():
                    new_path = PRODUCT_DIR / f.name
                    shutil.move(str(existing_path), str(new_path))
                    item["file"] = str(new_path)
                    print(f"  🔄 이동+태그 업데이트: {f.name}")
                else:
                    print(f"  🔄 태그 업데이트: {f.name}  [{', '.join(new_tags[:3])}...]")
                updated += 1

                # import_here에 남아있으면 삭제
                if f.exists():
                    f.unlink()
            else:
                print(f"  건너뜀 (이미 등록됨): {f.name}")
            continue

        # ── 신규 파일 등록 ──────────────────────────────────────────
        dest    = dest_dir / f.name
        counter = 1
        while dest.exists():
            dest = dest_dir / f"{f.stem}_{counter}{f.suffix}"
            counter += 1

        shutil.move(str(f), str(dest))

        tags = _build_product_tags(product_name) if product_name else ["custom"]

        entry = {
            "file":          str(dest),
            "category":      category,
            "source":        "manual_import",
            "query":         product_name or "",
            "provider":      "custom",
            "all_tags":      tags,
            "clip_verified": False,
        }
        library.append(entry)
        print(f"  ✅ 신규 등록: {f.name} → {dest}")
        added += 1

    save_library(library)

    print(f"\n 완료: 신규 {added}개 등록, {updated}개 태그 업데이트")
    if product_name and (added + updated) > 0:
        print(f"\n 📁 파일 저장 위치: {dest_dir}")
        print(f"   (import_here에서 이동됨. 삭제된 게 아닙니다.)")
        print(f"\n 이제 스크립트 JSON에서 제품 등장 장면 visual_tag에")
        print(f"   '제품이미지' 태그를 넣으면 '{product_name}' 이미지가 우선 매칭됩니다.")
    if added > 0 and not product_name:
        print(f"\n 다음 단계 (선택): CLIP 태그 분석")
        print(f"   python D:/WISSLIST/scripts/clip_tagger.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="커스텀 이미지 등록")
    parser.add_argument("--product", "-p", type=str, default=None,
                        help="제품명 (지정 시 제품이미지 태그 자동 추가)")
    args = parser.parse_args()
    run(product_name=args.product)
