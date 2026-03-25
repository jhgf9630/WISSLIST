# =============================================
# WISSLIST - 소스별 미디어 수집기
# 각 함수는 독립적으로 호출 가능
# =============================================

import requests
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import BASE_DIR, PEXELS_API_KEY, PIXABAY_API_KEY, GIPHY_API_KEY
from tag_map import QUERY_TAG_MAP
from library import get_existing_sources, get_existing_files, add_entry

BASE      = Path(BASE_DIR)
MEDIA_DIR = BASE / "media_library"


def _make_entry(file_path, category, source_url, query, provider, extra_tags=None):
    tags = QUERY_TAG_MAP.get(query, [category])
    if extra_tags:
        tags = list(set(tags + extra_tags))
    return {
        "file":          str(file_path),
        "category":      category,
        "source":        source_url,
        "query":         query,
        "provider":      provider,
        "all_tags":      list(set([category] + tags)),
        "clip_verified": False,
    }


# ════════════════════════════════════════════
# 1. PEXELS  (이미지 + 영상)
# ════════════════════════════════════════════
def collect_pexels(query: str, category: str, count: int = 3,
                   media_type: str = "image") -> int:
    """
    media_type: "image" 또는 "video"
    반환값: 새로 저장된 파일 수
    """
    if not PEXELS_API_KEY or "여기에" in PEXELS_API_KEY:
        print("  ⚠️  Pexels API 키 미설정 — config.py 확인")
        return 0

    headers = {"Authorization": PEXELS_API_KEY}

    if media_type == "video":
        url = (f"https://api.pexels.com/videos/search"
               f"?query={requests.utils.quote(query)}&per_page={count}")
    else:
        url = (f"https://api.pexels.com/v1/search"
               f"?query={requests.utils.quote(query)}&per_page={count}")

    try:
        res = requests.get(url, headers=headers, timeout=10).json()
    except Exception as e:
        print(f"  ⚠️  Pexels 요청 실패: {e}")
        return 0

    save_dir = MEDIA_DIR / category
    save_dir.mkdir(parents=True, exist_ok=True)

    existing_src   = get_existing_sources()
    existing_files = get_existing_files()
    saved = 0

    items = res.get("photos", []) if media_type == "image" else res.get("videos", [])

    for item in items:
        src_url = item.get("url", "")
        if src_url in existing_src:
            print(f"  ↩️  중복: {item['id']}")
            continue

        # 다운로드 URL 결정
        if media_type == "video":
            files = item.get("video_files", [])
            if not files:
                continue
            # 해상도 낮은 것 우선 (용량 절약)
            files_sorted = sorted(files, key=lambda x: x.get("width", 9999))
            dl_url = files_sorted[0]["link"]
            ext = ".mp4"
        else:
            dl_url = item["src"]["large"]
            ext = ".jpg"

        file_name = f"pxl_{item['id']}{ext}"
        file_path = save_dir / file_name

        if str(file_path) in existing_files:
            print(f"  ↩️  파일 중복: {file_name}")
            continue

        try:
            data = requests.get(dl_url, timeout=20).content
            with open(file_path, "wb") as f:
                f.write(data)
        except Exception as e:
            print(f"  ⚠️  다운로드 실패: {e}")
            continue

        add_entry(_make_entry(file_path, category, src_url, query, "pexels"))
        print(f"  ✅  Pexels [{media_type}] 저장: {file_name}")
        saved += 1
        time.sleep(0.2)

    return saved


# ════════════════════════════════════════════
# 2. PIXABAY  (이미지)
# ════════════════════════════════════════════
def collect_pixabay(query: str, category: str, count: int = 5) -> int:
    if not PIXABAY_API_KEY or "여기에" in PIXABAY_API_KEY:
        print("  ⚠️  Pixabay API 키 미설정 — config.py 확인")
        return 0

    url = (f"https://pixabay.com/api/"
           f"?key={PIXABAY_API_KEY}"
           f"&q={requests.utils.quote(query)}"
           f"&image_type=photo&per_page={count}&safesearch=true")

    try:
        res = requests.get(url, timeout=10).json()
    except Exception as e:
        print(f"  ⚠️  Pixabay 요청 실패: {e}")
        return 0

    save_dir = MEDIA_DIR / category
    save_dir.mkdir(parents=True, exist_ok=True)

    existing_src = get_existing_sources()
    saved = 0

    for hit in res.get("hits", []):
        src_url = hit.get("pageURL", "")
        if src_url in existing_src:
            print(f"  ↩️  중복: {hit['id']}")
            continue

        img_url   = hit.get("largeImageURL", hit.get("webformatURL", ""))
        file_name = f"pxb_{hit['id']}.jpg"
        file_path = save_dir / file_name

        if file_path.exists():
            print(f"  ↩️  파일 중복: {file_name}")
            continue

        try:
            data = requests.get(img_url, timeout=15).content
            with open(file_path, "wb") as f:
                f.write(data)
        except Exception as e:
            print(f"  ⚠️  다운로드 실패: {e}")
            continue

        add_entry(_make_entry(file_path, category, src_url, query, "pixabay"))
        print(f"  ✅  Pixabay 저장: {file_name}")
        saved += 1
        time.sleep(0.2)

    return saved


# ════════════════════════════════════════════
# 3. GIPHY  (GIF 짤)
# ════════════════════════════════════════════
def collect_giphy(query: str, category: str, count: int = 5) -> int:
    if not GIPHY_API_KEY or "여기에" in GIPHY_API_KEY:
        print("  ⚠️  Giphy API 키 미설정 — config.py 확인")
        return 0

    url = (f"https://api.giphy.com/v1/gifs/search"
           f"?api_key={GIPHY_API_KEY}"
           f"&q={requests.utils.quote(query)}"
           f"&limit={count}&rating=g")

    try:
        res = requests.get(url, timeout=10).json()
    except Exception as e:
        print(f"  ⚠️  Giphy 요청 실패: {e}")
        return 0

    save_dir = MEDIA_DIR / "gif" / category
    save_dir.mkdir(parents=True, exist_ok=True)

    existing_src = get_existing_sources()
    saved = 0

    for gif in res.get("data", []):
        src_url = gif.get("url", "")
        if src_url in existing_src:
            print(f"  ↩️  중복: {gif['id']}")
            continue

        gif_url   = gif["images"]["original"]["url"].split("?")[0]
        file_name = f"gif_{gif['id']}.gif"
        file_path = save_dir / file_name

        if file_path.exists():
            print(f"  ↩️  파일 중복: {file_name}")
            continue

        try:
            data = requests.get(gif_url, timeout=20).content
            with open(file_path, "wb") as f:
                f.write(data)
        except Exception as e:
            print(f"  ⚠️  GIF 다운로드 실패: {e}")
            continue

        add_entry(_make_entry(file_path, "gif_" + category, src_url,
                              query, "giphy", extra_tags=["gif", "유머러스한"]))
        print(f"  ✅  Giphy GIF 저장: {file_name}")
        saved += 1
        time.sleep(0.3)

    return saved


# ════════════════════════════════════════════
# 4. WIKIMEDIA  (공공 이미지, API 키 불필요)
# ════════════════════════════════════════════
def collect_wikimedia(query: str, category: str, count: int = 5) -> int:
    url = (f"https://commons.wikimedia.org/w/api.php"
           f"?action=query&generator=search&gsrnamespace=6"
           f"&gsrsearch={requests.utils.quote(query)}"
           f"&gsrlimit={count}"
           f"&prop=imageinfo&iiprop=url|size|mime&format=json")

    try:
        res = requests.get(url, timeout=10).json()
    except Exception as e:
        print(f"  ⚠️  Wikimedia 요청 실패: {e}")
        return 0

    save_dir = MEDIA_DIR / "wikimedia" / category
    save_dir.mkdir(parents=True, exist_ok=True)

    existing_src = get_existing_sources()
    saved = 0

    for page in res.get("query", {}).get("pages", {}).values():
        info    = page.get("imageinfo", [{}])[0]
        img_url = info.get("url", "")
        mime    = info.get("mime", "")

        if mime not in ("image/jpeg", "image/png") or not img_url:
            continue
        if img_url in existing_src:
            print(f"  ↩️  중복: {page['pageid']}")
            continue

        ext       = ".jpg" if mime == "image/jpeg" else ".png"
        file_name = f"wiki_{page['pageid']}{ext}"
        file_path = save_dir / file_name

        if file_path.exists():
            continue

        try:
            headers = {"User-Agent": "WISSLIST/1.0"}
            data    = requests.get(img_url, headers=headers, timeout=20).content
            with open(file_path, "wb") as f:
                f.write(data)
        except Exception as e:
            print(f"  ⚠️  Wikimedia 다운로드 실패: {e}")
            continue

        add_entry(_make_entry(file_path, category, img_url, query, "wikimedia"))
        print(f"  ✅  Wikimedia 저장: {file_name}")
        saved += 1
        time.sleep(0.3)

    return saved
