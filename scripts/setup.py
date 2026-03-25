# =============================================
# WISSLIST - 최초 환경 점검 스크립트
# 실행: python setup.py
# =============================================

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import BASE_DIR, PEXELS_API_KEY, PIXABAY_API_KEY, GIPHY_API_KEY

print("\n🎬 WISSLIST 환경 점검")
print("=" * 45)

BASE = Path(BASE_DIR)

# 1. USB/D드라이브
print("\n📁 D드라이브(USB) 확인:")
if not BASE.exists():
    print("  ❌ D드라이브 없음 → USB를 연결 후 다시 실행")
    sys.exit(1)
print(f"  ✅ {BASE_DIR} 존재")

# 2. 폴더 생성
print("\n📂 폴더 자동 생성:")
folders = [
    "media_library/kitchen", "media_library/food", "media_library/lifestyle",
    "media_library/outdoor", "media_library/tech_gadgets",
    "media_library/health_beauty", "media_library/baby_kids",
    "media_library/text_bg", "media_library/emotion", "media_library/money_price",
    "media_library/gif/reaction_gif", "media_library/gif/food_gif",
    "media_library/gif/shopping_gif",
    "audio", "output", "scripts_json", "logs", "scripts",
]
for f in folders:
    (BASE / f).mkdir(parents=True, exist_ok=True)
    print(f"  ✅ {f}")

# 3. API 키 상태
print("\n🔑 API 키 상태:")
key_map = {
    "Pexels":    PEXELS_API_KEY,
    "Pixabay":   PIXABAY_API_KEY,
    "Giphy":     GIPHY_API_KEY,
    "Wikimedia": "불필요",
}
for name, key in key_map.items():
    if name == "Wikimedia":
        print(f"  ✅ {name}: API 키 불필요")
    elif "여기에" in key or not key:
        print(f"  ⚠️  {name}: 미설정 → config.py 에 입력 필요")
    else:
        masked = key[:6] + "..." + key[-4:]
        print(f"  ✅ {name}: {masked}")

# 4. 패키지 확인
print("\n📦 패키지 확인:")
packages = {
    "requests":     "requests",
    "edge_tts":     "edge-tts",
    "moviepy":      "moviepy",
    "torch":        "torch (CPU)",
    "transformers": "transformers",
    "PIL":          "Pillow",
}
all_ok = True
for mod, name in packages.items():
    try:
        __import__(mod)
        print(f"  ✅ {name}")
    except ImportError:
        print(f"  ❌ {name} → pip install {name.split()[0]}")
        all_ok = False

# 5. Pexels 연결 테스트
print("\n📡 Pexels API 연결 테스트:")
if "여기에" not in PEXELS_API_KEY:
    import requests
    try:
        res = requests.get(
            "https://api.pexels.com/v1/search?query=food&per_page=1",
            headers={"Authorization": PEXELS_API_KEY}, timeout=8
        ).json()
        if res.get("photos"):
            print("  ✅ Pexels 연결 성공")
        else:
            print("  ❌ Pexels 응답 오류 — API 키 재확인")
    except Exception as e:
        print(f"  ❌ 연결 실패: {e}")
else:
    print("  ⚠️  Pexels 키 미설정 — 건너뜀")

print("\n" + "=" * 45)
if all_ok:
    print("🎉 환경 점검 완료! 다음 명령어로 수집을 시작하세요:")
    print("\n  python collect.py giphy        ← Giphy GIF만")
    print("  python collect.py pexels       ← Pexels만")
    print("  python collect.py              ← 대화형 메뉴")
else:
    print("⚠️  ❌ 항목을 해결 후 다시 실행하세요.")
