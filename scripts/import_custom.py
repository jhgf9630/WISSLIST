# =============================================
# WISSLIST - 커스텀 이미지 임포터 (CLIP 전처리)
#
# 사용법:
#   1. D:/WISSLIST/media_library/import_here/ 폴더에
#      분류하고 싶은 이미지/GIF를 넣기
#   2. python import_custom.py 실행
#   3. library.json에 자동 등록 (clip_verified=False)
#   4. clip_tagger.py 실행하면 CLIP이 태그 분석
# =============================================

import sys, shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import BASE_DIR
from library import load_library, add_entry, get_existing_files

BASE       = Path(BASE_DIR)
IMPORT_DIR = BASE / "media_library" / "import_here"
CUSTOM_DIR = BASE / "media_library" / "custom"

SUPPORTED = {".jpg",".jpeg",".png",".gif",".mp4",".mov"}

def run():
    if not BASE.exists():
        print("USB(D드라이브) 연결 확인")
        return

    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    CUSTOM_DIR.mkdir(parents=True, exist_ok=True)

    files = [f for f in IMPORT_DIR.iterdir()
             if f.suffix.lower() in SUPPORTED]

    if not files:
        print(f"
 import_here 폴더가 비어있습니다.")
        print(f"   경로: {IMPORT_DIR}")
        print(f"   이미지/GIF/영상 파일을 넣고 다시 실행하세요.")
        return

    existing = get_existing_files()
    added = 0

    print(f"
 커스텀 미디어 임포트 시작: {len(files)}개 발견")

    for f in files:
        dest = CUSTOM_DIR / f.name
        # 동명 파일 중복 방지
        counter = 1
        while dest.exists():
            dest = CUSTOM_DIR / f"{f.stem}_{counter}{f.suffix}"
            counter += 1

        if str(dest) in existing:
            print(f"  건너뜀 (이미 등록됨): {f.name}")
            continue

        shutil.move(str(f), str(dest))

        entry = {
            "file":          str(dest),
            "category":      "custom",
            "source":        "manual_import",
            "query":         "",
            "provider":      "custom",
            "all_tags":      ["custom"],
            "clip_verified": False,  # CLIP이 태그 분석 예정
        }
        add_entry(entry)
        print(f"  등록: {dest.name}")
        added += 1

    print(f"
 임포트 완료: {added}개 등록")
    print(f"  저장 위치: {CUSTOM_DIR}")
    if added > 0:
        print(f"
 다음 단계: CLIP 태그 분석 실행")
        print(f"   python D:/WISSLIST/scripts/clip_tagger.py")

if __name__ == "__main__":
    run()
