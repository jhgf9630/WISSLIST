# =============================================
# WISSLIST - 쿠팡 제품 이미지 자동 수집기
#
# 사용법:
#   python coupang_collector.py "컵라면"
#   python coupang_collector.py "에어프라이어" --count 5
#   python coupang_collector.py "치킨" --category food
#
# 동작:
#   쿠팡 검색 결과 상품 이미지를 자동 저장 후
#   library.json에 제품 태그와 함께 등록
# =============================================

import sys
import time
import json
import argparse
import requests
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))
from config import BASE_DIR
from library import load_library, add_entry, get_existing_files

BASE      = Path(BASE_DIR)
PROD_DIR  = BASE / "media_library" / "product"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://www.coupang.com/",
}


def search_coupang_images(keyword: str, count: int = 5) -> list:
    """
    쿠팡 검색 결과에서 상품 이미지 URL 목록 추출.
    공식 API 대신 공개 검색 페이지의 JSON 데이터 활용.
    """
    url = (
        "https://www.coupang.com/np/search"
        f"?q={quote(keyword)}&channel=user&component=&eventSource=SER"
        f"&trcid=&traid=&sorter=scoreDesc&minPrice=&maxPrice="
        f"&priceRange=&filterType=&listSize={count}&filter=&isPriceRange=false"
        f"&brand=&offerCondition=&rating=0&page=1&rocketAll=false"
        f"&searchIndexingToken=&backgroundColor="
    )

    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"  ⚠️  쿠팡 응답 오류: {resp.status_code}")
            return results

        # 이미지 URL 패턴 추출
        import re
        # 쿠팡 상품 이미지 패턴
        patterns = [
            r'"thumbnail"\s*:\s*"([^"]+thumbnail[^"]+\.jpg[^"]*)"',
            r'"imageUrl"\s*:\s*"([^"]+\.jpg[^"]*)"',
            r'src="(https://thumbnail\d+\.coupangcdn\.com[^"]+\.jpg[^"]*)"',
            r'"img"\s*:\s*"([^"]+coupangcdn[^"]+)"',
        ]

        found = set()
        for pattern in patterns:
            matches = re.findall(pattern, resp.text)
            for m in matches:
                if "coupangcdn" in m or "coupang" in m:
                    # 고해상도 버전으로 변환
                    img_url = m.replace("\\u002F", "/").replace("\\", "")
                    if "thumbnail" in img_url and img_url not in found:
                        # 저해상도 → 고해상도
                        img_url = re.sub(r'/q\d+/w\d+', '', img_url)
                        found.add(img_url)
                        results.append(img_url)
                        if len(results) >= count:
                            break
            if len(results) >= count:
                break

    except Exception as e:
        print(f"  ⚠️  수집 오류: {e}")

    return results[:count]


def download_product_images(keyword: str, count: int = 5,
                             category: str = "product") -> int:
    """쿠팡 제품 이미지 다운로드 + library.json 등록"""

    PROD_DIR.mkdir(parents=True, exist_ok=True)
    existing_files = get_existing_files()

    # 제품 카테고리 폴더 생성
    cat_dir = BASE / "media_library" / category
    cat_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🛒 쿠팡 제품 이미지 수집: '{keyword}' ({count}개 목표)")

    image_urls = search_coupang_images(keyword, count * 2)

    if not image_urls:
        print(f"  ⚠️  이미지를 찾지 못했습니다.")
        print(f"  💡 대안: 쿠팡에서 수동으로 상품 이미지를 저장한 후")
        print(f"           import_here 폴더에 넣고 import_custom.py 실행")
        return 0

    saved = 0
    for i, url in enumerate(image_urls):
        if saved >= count:
            break

        file_name = f"coupang_{keyword}_{i+1:02d}.jpg"
        file_path = cat_dir / file_name

        if str(file_path) in existing_files or file_path.exists():
            print(f"  ↩️  중복: {file_name}")
            continue

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200 and len(resp.content) > 5000:
                with open(file_path, "wb") as f:
                    f.write(resp.content)
            else:
                continue
        except Exception as e:
            print(f"  ⚠️  다운로드 실패: {e}")
            continue

        # 제품 태그 매핑
        product_tags = _get_product_tags(keyword)
        entry = {
            "file":          str(file_path),
            "category":      category,
            "source":        url,
            "query":         keyword,
            "provider":      "coupang",
            "all_tags":      [category, "제품단독", "제품등장"] + product_tags,
            "clip_verified": False,
        }
        add_entry(entry)
        saved += 1
        print(f"  ✅  저장: {file_name}")
        time.sleep(0.5)  # 쿠팡 서버 부하 방지

    print(f"\n✅ 수집 완료: {saved}개 저장")
    return saved


def _get_product_tags(keyword: str) -> list:
    """제품명으로 태그 자동 매핑"""
    kw = keyword.lower()
    tag_map = {
        "라면":        ["라면", "음식클로즈업", "식품패키지"],
        "컵라면":      ["컵라면", "라면", "편의점음식", "식품패키지"],
        "치킨":        ["치킨", "음식클로즈업", "배달음식"],
        "피자":        ["피자", "음식클로즈업", "배달음식"],
        "에어프라이어": ["에어프라이어", "소형가전", "가전제품"],
        "전자레인지":  ["전자레인지", "가전제품", "소형가전"],
        "청소기":      ["청소기", "가전제품", "소형가전"],
        "커피":        ["커피머신", "카페분위기", "음식클로즈업"],
        "스킨케어":    ["스킨케어", "뷰티제품", "욕실뷰티"],
        "샴푸":        ["샴푸", "뷰티제품", "욕실뷰티"],
        "냉동":        ["냉동식품", "간편식", "식품패키지"],
        "간편식":      ["간편식", "편의점음식", "식품패키지"],
    }
    tags = []
    for k, v in tag_map.items():
        if k in kw:
            tags.extend(v)
    return list(set(tags)) if tags else ["제품단독", "식품패키지"]


def run_interactive():
    """대화형 실행 모드"""
    print("\n🛒 WISSLIST 쿠팡 제품 이미지 수집기")
    print("=" * 45)
    print("자동 수집이 어려운 경우 수동 방법:")
    print("  1. 쿠팡에서 원하는 제품 페이지 열기")
    print("  2. 상품 이미지 우클릭 → '이미지 저장'")
    print(f"  3. D:\\WISSLIST\\media_library\\import_here\\ 에 저장")
    print("  4. python import_custom.py 실행")
    print("=" * 45)

    keyword = input("\n검색할 제품명 입력 (예: 컵라면): ").strip()
    if not keyword:
        return

    count_str = input("다운로드 개수 (기본값: 5): ").strip()
    count     = int(count_str) if count_str.isdigit() else 5

    download_product_images(keyword, count)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="쿠팡 제품 이미지 수집")
    parser.add_argument("keyword", nargs="?", help="검색 키워드")
    parser.add_argument("--count", "-c", type=int, default=5)
    parser.add_argument("--category", default="product")
    args = parser.parse_args()

    if not BASE.exists():
        print("❌ D드라이브(USB) 연결 확인")
        sys.exit(1)

    if args.keyword:
        download_product_images(args.keyword, args.count, args.category)
    else:
        run_interactive()
