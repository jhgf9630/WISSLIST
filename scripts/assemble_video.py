# =============================================
# WISSLIST - 영상 자동 조립 v14
#
# v14 수정:
#  1. 배속 싱크 수정: 모든 클립에 -r 30 강제 → setpts 정확 동작
#  2. 레이아웃 전면 재설계:
#     - PIL로 배경 프레임 생성 (1080x1920)
#     - 배경 위 중앙에 GIF/이미지 박스 배치 (레퍼런스 스타일)
#     - 상단: 제목 텍스트
#     - 중간: 미디어 박스
#     - 하단: 나레이션 자막
# =============================================

import json, sys, subprocess, shutil, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from config import BASE_DIR
from library import load_library

# 커스텀 배경/엔딩 이미지 설정 읽기
try:
    from config import CUSTOM_BG_PATH, CUSTOM_ENDING_PATH
except ImportError:
    CUSTOM_BG_PATH, CUSTOM_ENDING_PATH = None, None

# ── assets 폴더 자동 감지 ─────────────────────────────────────────
# config.py에 None으로 설정되어 있어도,
# D:\WISSLIST\assets\ 에 파일이 있으면 자동으로 사용
_ASSETS_DIR = Path(BASE_DIR) / "assets"
_IMG_EXTS   = {".png", ".jpg", ".jpeg"}

def _find_asset(name_hints: list) -> str | None:
    """
    assets 폴더에서 name_hints 키워드가 포함된 이미지 파일 탐색.
    예: ["bg", "background"] → bg.png, my_bg.jpg 등 매칭
    """
    if not _ASSETS_DIR.exists():
        return None
    for f in sorted(_ASSETS_DIR.iterdir()):
        if f.suffix.lower() not in _IMG_EXTS:
            continue
        fname = f.name.lower()
        for hint in name_hints:
            if hint in fname:
                return str(f)
    # 힌트 없으면 첫 번째 이미지 반환
    all_imgs = [f for f in _ASSETS_DIR.iterdir()
                if f.suffix.lower() in _IMG_EXTS]
    return str(all_imgs[0]) if all_imgs else None

if not CUSTOM_BG_PATH:
    CUSTOM_BG_PATH = _find_asset(["bg", "background", "back"])
if not CUSTOM_ENDING_PATH:
    CUSTOM_ENDING_PATH = _find_asset(["ending", "end", "outro"])
    # 엔딩 전용 파일이 없으면 배경 파일을 엔딩으로도 사용
    if not CUSTOM_ENDING_PATH and CUSTOM_BG_PATH:
        CUSTOM_ENDING_PATH = CUSTOM_BG_PATH

if CUSTOM_BG_PATH:
    print(f"✅ 커스텀 배경 감지: {Path(CUSTOM_BG_PATH).name}")
if CUSTOM_ENDING_PATH:
    print(f"✅ 커스텀 엔딩 감지: {Path(CUSTOM_ENDING_PATH).name}")

BASE        = Path(BASE_DIR)
SCRIPT_PATH = BASE / "scripts_json" / "today_script.json"
AUDIO_DIR   = BASE / "audio"
OUTPUT_DIR  = BASE / "output"
TMP_DIR     = BASE / "tmp_clips"
BGM_DIR     = BASE / "bgm"

# 쇼츠 9:16 비율
TARGET_W, TARGET_H = 1080, 1920

# ── 레이아웃 영역 정의 ──────────────────────────────────────────────
# [0~18%]   헤더/제목
# [20~35%]  자막 영역  ← 눈에 잘 띄는 중단 위치
# [37~90%]  미디어 박스 (GIF/이미지)
# [91~100%] 하단 여백

HEADER_H  = int(TARGET_H * 0.18)   # 헤더 높이: 0~345px

SUB_TOP   = int(TARGET_H * 0.20)   # 자막 영역 시작: 384px
SUB_BOT   = int(TARGET_H * 0.35)   # 자막 영역 끝:   672px

BOX_X     = 40
BOX_Y     = int(TARGET_H * 0.37)   # 이미지 박스 시작: 710px
BOX_W     = TARGET_W - 80          # 1000px
BOX_H     = int(TARGET_H * 0.53)   # 이미지 박스 높이: 1018px (37~90%)

# 배경색 (레퍼런스: 밝은 크림/베이지)
BG_COLOR   = (245, 242, 235)
ACCENT     = (50,  50,  50)

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\malgunbd.ttf",
    r"C:\Windows\Fonts\malgun.ttf",
    r"C:\Windows\Fonts\gulim.ttc",
    r"C:\Windows\Fonts\arial.ttf",
]


def get_font(size: int):
    for fp in FONT_CANDIDATES:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ══════════════════════════════════════════════════════════════════
# subprocess 헬퍼
# ══════════════════════════════════════════════════════════════════
def run_cmd(cmd: list, timeout: int = 120) -> tuple:
    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=timeout)
        stdout = r.stdout.decode("utf-8", errors="replace") if r.stdout else ""
        stderr = r.stderr.decode("utf-8", errors="replace") if r.stderr else ""
        return r.returncode, stdout, stderr
    except FileNotFoundError:
        return 2, "", f"명령어 없음: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 1, "", "타임아웃"
    except Exception as e:
        return 1, "", str(e)


def check_ffmpeg():
    code, _, _ = run_cmd(["ffmpeg", "-version"], timeout=10)
    if code != 0:
        print("❌ ffmpeg PATH 등록 필요")
        sys.exit(1)
    print("✅ ffmpeg 확인 완료")


def get_audio_duration(path: str) -> float:
    _, out, _ = run_cmd([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)], timeout=15)
    try:
        return float(out.strip())
    except ValueError:
        return 2.0


# ── 한국어 TTS 목소리 목록 (동작 확인된 목소리만) ─────────────────
KO_VOICES = [
    "ko-KR-SunHiNeural",    # 밝고 친근한 여성 (기본)
    "ko-KR-InJoonNeural",   # 차분한 남성
    "ko-KR-HyunsuNeural",   # 활기찬 남성
]


# ══════════════════════════════════════════════════════════════════
# TTS
# ══════════════════════════════════════════════════════════════════
def make_tts(text: str, out_path: Path, voice: str = "ko-KR-SunHiNeural"):
    """
    edge-tts로 TTS 생성.
    - 텍스트를 UTF-8 파일로 저장 후 --file 옵션으로 전달 (인코딩 문제 방지)
    - 네트워크 오류 등에 대비해 최대 3회 재시도
    - 재시도 사이 1초 대기 (edge-tts 서버 rate limit 방지)
    """
    import time

    txt_path = out_path.with_suffix(".txt")
    txt_path.write_text(text, encoding="utf-8")

    base_args = [
        "--voice", voice,
        "--rate", "+5%",
        "--file", str(txt_path),
        "--write-media", str(out_path),
    ]

    last_err = ""
    for attempt in range(3):
        if attempt > 0:
            time.sleep(1.5)
            print(f"  🔄 TTS 재시도 {attempt+1}/3...")

        # 1차: edge-tts CLI
        code, _, err = run_cmd(["edge-tts"] + base_args, timeout=40)
        if code == 0 and out_path.exists() and out_path.stat().st_size > 1000:
            break

        # 2차: python -m edge_tts
        code2, _, err2 = run_cmd(
            [sys.executable, "-m", "edge_tts"] + base_args, timeout=40)
        if code2 == 0 and out_path.exists() and out_path.stat().st_size > 1000:
            break

        last_err = err2 or err
    else:
        # 3회 모두 실패
        try:
            txt_path.unlink()
        except Exception:
            pass
        raise RuntimeError(
            f"TTS 생성 실패 (3회 재시도 초과).\n"
            f"텍스트: {text[:50]}\n"
            f"오류: {last_err[:300]}\n\n"
            f"해결 방법:\n"
            f"  1. 인터넷 연결 확인\n"
            f"  2. pip install --upgrade edge-tts\n"
            f"  3. 잠시 후 다시 실행"
        )

    try:
        txt_path.unlink()
    except Exception:
        pass

    size_kb = out_path.stat().st_size // 1024
    print(f"  🎙️  {out_path.name}  ({size_kb}KB)")
    time.sleep(0.3)  # 연속 요청 간 짧은 딜레이


# ══════════════════════════════════════════════════════════════════
# PIL 유틸
# ══════════════════════════════════════════════════════════════════
def wrap_text(draw, text: str, font, max_width: int) -> list:
    words = text.split()
    lines, line = [], ""
    for word in words:
        test = (line + " " + word).strip()
        if draw.textbbox((0,0), test, font=font)[2] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def draw_text_with_outline(draw, x, y, text, font, color, outline_color,
                            outline_w=3):
    for dx in range(-outline_w, outline_w+1):
        for dy in range(-outline_w, outline_w+1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x+dx, y+dy), text, font=font, fill=outline_color)
    draw.text((x, y), text, font=font, fill=color)


# ══════════════════════════════════════════════════════════════════
# 배경 프레임 생성
# 레이아웃:
#   [0~18%]   헤더/제목
#   [20~35%]  자막 영역 (텍스트는 overlay로 별도 처리)
#   [37~90%]  미디어 박스
# ══════════════════════════════════════════════════════════════════
def make_bg_frame(title: str, out_path: Path):
    """
    배경 PNG 생성.
    narration 자막은 overlay로 별도 처리하므로 배경에 포함하지 않음.
    """
    img  = Image.new("RGB", (TARGET_W, TARGET_H), (248, 245, 238))
    draw = ImageDraw.Draw(img)

    # 배경 그라데이션
    for y in range(TARGET_H):
        t = y / TARGET_H
        draw.line([(0, y), (TARGET_W, y)],
                  fill=(int(248-t*8), int(245-t*10), int(238-t*15)))

    # ── 상단 헤더 ─────────────────────────────────────────────────
    for y in range(HEADER_H):
        c = int(15 + (y / HEADER_H) * 20)
        draw.line([(0, y), (TARGET_W, y)], fill=(c, c, c))

    # 헤더 하단 포인트 라인
    draw.rectangle([0, HEADER_H-5, TARGET_W, HEADER_H], fill=(180, 140, 255))

    # 타이틀 텍스트
    title_font = get_font(54)
    t_lines    = wrap_text(draw, title, title_font, TARGET_W - 80)
    lh         = draw.textbbox((0,0), "가", font=title_font)[3] + 16
    t_total    = lh * len(t_lines)
    t_y        = (HEADER_H - t_total) // 2

    for i, line in enumerate(t_lines):
        tw = draw.textbbox((0,0), line, font=title_font)[2]
        tx = (TARGET_W - tw) // 2
        ty = t_y + i * lh
        draw.text((tx+2, ty+2), line, font=title_font, fill=(0, 0, 0))
        draw.text((tx, ty), line, font=title_font, fill=(255, 255, 255))

    # ── 자막 영역 표시 (텍스트는 overlay로 처리, 여기선 구분선만) ──
    draw.rectangle([0, SUB_TOP-2, TARGET_W, SUB_TOP-2], fill=(180, 140, 255))

    # ── 미디어 박스 ────────────────────────────────────────────────
    bx1 = BOX_X
    by1 = BOX_Y
    bx2 = BOX_X + BOX_W
    by2 = BOX_Y + BOX_H

    # 그림자
    draw.rectangle([bx1+10, by1+10, bx2+10, by2+10], fill=(160, 155, 145))
    # 박스 내부
    draw.rectangle([bx1, by1, bx2, by2], fill=(25, 25, 25))
    # 테두리
    draw.rectangle([bx1-3, by1-3, bx2+3, by2+3],
                   outline=(70, 65, 60), width=6)

    img.save(str(out_path), "PNG")


# ══════════════════════════════════════════════════════════════════
# 자막 PNG 생성 (자막 영역 SUB_TOP~SUB_BOT 기준)
# ══════════════════════════════════════════════════════════════════
def make_subtitle_png(text: str, out_path: Path):
    """
    자막 텍스트를 중단 자막 영역(SUB_TOP~SUB_BOT)에 렌더링한 PNG.
    배경 투명, 흰 글자 + 검정 외곽선.
    """
    img  = Image.new("RGBA", (TARGET_W, TARGET_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    sub_font  = get_font(52)
    area_h    = SUB_BOT - SUB_TOP
    sub_lines = wrap_text(draw, text, sub_font, TARGET_W - 80)
    slh       = draw.textbbox((0,0), "가", font=sub_font)[3] + 16
    s_total   = slh * len(sub_lines)
    sy        = SUB_TOP + (area_h - s_total) // 2

    for i, line in enumerate(sub_lines):
        tw = draw.textbbox((0,0), line, font=sub_font)[2]
        tx = (TARGET_W - tw) // 2
        ty = sy + i * slh
        draw_text_with_outline(draw, tx, ty, line, sub_font,
                               color=(255, 255, 255),
                               outline_color=(0, 0, 0),
                               outline_w=3)

    img.save(str(out_path), "PNG")


# ══════════════════════════════════════════════════════════════════
# narration 2분할
# ══════════════════════════════════════════════════════════════════
def split_narration(text: str) -> tuple:
    """
    나레이션을 두 파트로 분할.
    1순위: 마침표(./!/?) 기준 — 자연스러운 문장 경계
    2순위: 단어 기준 절반 분할 (마침표 없을 때)
    """
    # 마침표/느낌표/물음표 뒤 공백 기준으로 분할
    import re
    # 문장 끝 구두점 + 공백 패턴 찾기
    matches = list(re.finditer(r'[.!?。]\s+', text))
    if matches:
        # 가장 중간에 가까운 구두점 위치를 분할 기준으로 선택
        mid = len(text) / 2
        best = min(matches, key=lambda m: abs(m.end() - mid))
        first  = text[:best.end()].strip()
        second = text[best.end():].strip()
        if first and second:
            return first, second

    # 구두점 없으면 단어 기준 절반 분할
    words = text.split()
    if len(words) <= 1:
        return text, text
    mid   = max(1, len(words) // 2)
    return " ".join(words[:mid]), " ".join(words[mid:])


# ══════════════════════════════════════════════════════════════════
# 미디어 매칭 (GIF 우선, 후보 목록 반환)
# ══════════════════════════════════════════════════════════════════
def find_media_candidates(visual_tags: list, exclude_files: set = None,
                          prefer_gif: bool = True, product_name: str = None,
                          max_candidates: int = 5) -> list:
    """
    태그 기반 미디어 후보 목록 반환 (최대 max_candidates개).
    변환 실패 시 순서대로 다음 후보 사용.

    반환: [item, item, ...] 점수 내림차순
    """
    if exclude_files is None:
        exclude_files = set()

    library = load_library()
    candidates = []

    # ── 제품 이미지 우선 탐색 ──────────────────────────────────────
    is_product_seg = "제품이미지" in visual_tags
    if is_product_seg and product_name:
        product_pool = []
        for item in library:
            if item["file"] in exclude_files:
                continue
            if not Path(item["file"]).exists():
                continue
            tags = set(item["all_tags"])
            if product_name in tags or product_name.replace(" ", "") in tags:
                score = len(set(visual_tags) & tags) + 10
                product_pool.append((score, item))

        if product_pool:
            product_pool.sort(key=lambda x: -x[0])
            for _, item in product_pool[:max_candidates]:
                candidates.append(item)
            print(f"  🎯 [제품] 후보 {len(candidates)}개  (제품명: {product_name})")
            return candidates
        else:
            print(f"  ⚠️  '{product_name}' 제품 이미지 없음 → 일반 태그 매칭")

    # ── 일반 태그 매칭 ────────────────────────────────────────────
    scored_gif, scored_other = [], []
    for item in library:
        if item["file"] in exclude_files:
            continue
        if not Path(item["file"]).exists():
            continue
        score = len(set(visual_tags) & set(item["all_tags"]))
        if score == 0:
            continue
        (scored_gif if item["file"].lower().endswith(".gif")
         else scored_other).append((score, item))

    # GIF 우선 풀 구성
    if prefer_gif and scored_gif:
        # GIF 상위 + 일반 나머지 순서
        scored_gif.sort(key=lambda x: -x[0])
        scored_other.sort(key=lambda x: -x[0])
        pool = scored_gif + scored_other
    else:
        pool = sorted(scored_gif + scored_other, key=lambda x: -x[0])

    for _, item in pool[:max_candidates]:
        candidates.append(item)

    if not candidates:
        # 라이브러리에 없으면 Pexels 폴백 1개
        fb = _fallback_pexels(visual_tags[0] if visual_tags else "food")
        if fb:
            candidates.append(fb)

    if candidates:
        kind = "GIF" if candidates[0]["file"].lower().endswith(".gif") else "IMG"
        print(f"  🎯 [{kind}] {Path(candidates[0]['file']).name}  "
              f"(후보 {len(candidates)}개)")
    return candidates


# 하위 호환 래퍼 (기존 코드에서 단일 아이템 반환 기대하는 곳 없지만 안전하게 유지)
def find_best_media(visual_tags, exclude_files=None,
                    prefer_gif=True, product_name=None):
    cands = find_media_candidates(visual_tags, exclude_files,
                                  prefer_gif, product_name, max_candidates=5)
    return cands[0] if cands else None


def _fallback_pexels(query: str):
    from config import PEXELS_API_KEY
    from library import add_entry
    import requests
    fallback_dir = BASE / "media_library" / "fallback"
    fallback_dir.mkdir(parents=True, exist_ok=True)
    try:
        res   = requests.get(
            f"https://api.pexels.com/v1/search?query={requests.utils.quote(query)}&per_page=1",
            headers={"Authorization": PEXELS_API_KEY}, timeout=10).json()
        photo = res["photos"][0]
        path  = fallback_dir / f"pxl_{photo['id']}.jpg"
        path.write_bytes(requests.get(photo["src"]["large"], timeout=15).content)
        entry = {"file": str(path), "category": "fallback",
                 "source": photo.get("url",""), "query": query,
                 "provider": "pexels", "all_tags": [query], "clip_verified": False}
        add_entry(entry)
        print(f"  📥 폴백: {path.name}")
        return entry
    except Exception as e:
        print(f"  ❌ 폴백 실패: {e}")
        return None


# ══════════════════════════════════════════════════════════════════
# 세그먼트 클립 생성
# 구조:
#   배경PNG(제목+이미지박스윤곽) + 미디어 overlay + 자막 2분할 overlay
# ══════════════════════════════════════════════════════════════════
def make_segment_clip(media_path, audio_path: str,
                      title: str, narration: str,
                      duration: float,
                      out_path: Path, idx: int) -> bool:

    bg_png     = TMP_DIR / f"bg_{idx:02d}.png"
    media_mp4  = TMP_DIR / f"media_{idx:02d}.mp4"
    bg_vid     = TMP_DIR / f"bg_vid_{idx:02d}.mp4"
    combined   = TMP_DIR / f"combined_{idx:02d}.mp4"
    sub1_png   = TMP_DIR / f"sub1_{idx:02d}.png"
    sub2_png   = TMP_DIR / f"sub2_{idx:02d}.png"

    # ── 1. 배경 PNG 생성 ─────────────────────────────────────────
    if CUSTOM_BG_PATH and Path(CUSTOM_BG_PATH).exists():
        _overlay_text_on_custom_bg(CUSTOM_BG_PATH, title, "", bg_png,
                                   title_only=True)
    else:
        make_bg_frame(title, bg_png)

    # ── 2. 배경 PNG → 영상 (오디오 포함, -r 30) ──────────────────
    cmd_bg = ["ffmpeg", "-y",
              "-loop", "1", "-i", str(bg_png),
              "-i", audio_path,
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
              "-r", "30", "-c:a", "aac", "-b:a", "128k",
              "-t", f"{duration:.3f}", "-pix_fmt", "yuv420p",
              str(bg_vid)]
    code, _, err = run_cmd(cmd_bg, timeout=60)
    if code != 0:
        print(f"    ⚠️  배경 영상 생성 실패:\n{err[-300:]}")
        return False

    # ── 3. 미디어를 BOX 크기로 변환 (실패 시 다음 후보 자동 시도) ──
    scale_vf = (f"scale={BOX_W}:{BOX_H}"
                f":force_original_aspect_ratio=decrease"
                f",pad={BOX_W}:{BOX_H}:(ow-iw)/2:(oh-ih)/2:black")

    def _try_convert_media(mpath: str) -> bool:
        """단일 미디어 파일을 media_mp4로 변환. 성공 True, 실패 False."""
        ext = Path(mpath).suffix.lower()
        if ext in (".jpg", ".jpeg", ".png", ".webp"):
            cmd_m = ["ffmpeg", "-y", "-loop", "1", "-i", mpath,
                     "-vf", scale_vf, "-c:v", "libx264", "-preset", "veryfast",
                     "-crf", "23", "-r", "30", "-an",
                     "-t", f"{duration:.3f}", "-pix_fmt", "yuv420p", str(media_mp4)]
        elif ext == ".gif":
            # GIF: palette 문제 방지용 -ignore_loop 0 추가
            cmd_m = ["ffmpeg", "-y",
                     "-ignore_loop", "0",
                     "-stream_loop", "-1", "-i", mpath,
                     "-vf", scale_vf, "-c:v", "libx264", "-preset", "veryfast",
                     "-crf", "23", "-r", "30", "-an",
                     "-t", f"{duration:.3f}", "-pix_fmt", "yuv420p", str(media_mp4)]
        else:
            cmd_m = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", mpath,
                     "-vf", scale_vf, "-c:v", "libx264", "-preset", "veryfast",
                     "-crf", "23", "-r", "30", "-an",
                     "-t", f"{duration:.3f}", "-pix_fmt", "yuv420p", str(media_mp4)]
        code_m, _, err_m = run_cmd(cmd_m, timeout=60)
        if code_m != 0:
            print(f"    ⚠️  변환 실패 ({Path(mpath).name}): {err_m[-120:]}")
            return False
        # 변환 결과가 실제로 유효한지 크기 확인
        if not media_mp4.exists() or media_mp4.stat().st_size < 1000:
            print(f"    ⚠️  변환 결과 불량 ({Path(mpath).name})")
            return False
        return True

    media_ok = False
    if media_path and Path(media_path).exists():
        # 1차 시도
        if _try_convert_media(media_path):
            media_ok = True
        else:
            # 후보 파일들 순서대로 재시도 (make_segment_clip 호출자가 넘겨준 candidates)
            for alt in getattr(make_segment_clip, "_candidates", []):
                alt_path = alt["file"]
                if alt_path == media_path:
                    continue
                if not Path(alt_path).exists():
                    continue
                print(f"    🔄 대체 미디어 시도: {Path(alt_path).name}")
                if _try_convert_media(alt_path):
                    media_ok = True
                    break

    if media_ok:
        # 배경 위에 미디어 overlay
        cmd_ov = ["ffmpeg", "-y",
                  "-i", str(bg_vid), "-i", str(media_mp4),
                  "-filter_complex", f"overlay={BOX_X}:{BOX_Y}",
                  "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                  "-r", "30", "-c:a", "copy",
                  "-t", f"{duration:.3f}", "-pix_fmt", "yuv420p",
                  str(combined)]
        code3, _, err3 = run_cmd(cmd_ov, timeout=60)
        if code3 != 0:
            print(f"    ⚠️  overlay 실패 → 배경만\n{err3[-200:]}")
            shutil.copy(str(bg_vid), str(combined))
    else:
        if media_path:
            print(f"    ⚠️  모든 후보 변환 실패 → 배경만 사용")
        shutil.copy(str(bg_vid), str(combined))

    # ── 4. 자막 2분할 PNG 생성 ────────────────────────────────────
    first_text, second_text = split_narration(narration)
    make_subtitle_png(first_text,  sub1_png)
    make_subtitle_png(second_text, sub2_png)

    half = duration / 2.0

    # ── 5. 자막 2개를 enable 조건으로 타이밍 분리하여 overlay ─────
    # 첫 번째 자막: 0 ~ duration/2
    # 두 번째 자막: duration/2 ~ duration
    filter_complex = (
        f"[0:v][1:v]overlay=0:0:enable='between(t,0,{half:.3f})'[v1];"
        f"[v1][2:v]overlay=0:0:enable='between(t,{half:.3f},{duration:.3f})'[vout]"
    )
    cmd_sub = ["ffmpeg", "-y",
               "-i", str(combined),
               "-i", str(sub1_png),
               "-i", str(sub2_png),
               "-filter_complex", filter_complex,
               "-map", "[vout]", "-map", "0:a",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
               "-r", "30", "-c:a", "copy",
               "-t", f"{duration:.3f}", "-pix_fmt", "yuv420p",
               str(out_path)]
    code4, _, err4 = run_cmd(cmd_sub, timeout=60)
    if code4 != 0:
        print(f"    ⚠️  자막 overlay 실패 → 자막 없이 사용\n{err4[-200:]}")
        shutil.copy(str(combined), str(out_path))

    return out_path.exists()


# ══════════════════════════════════════════════════════════════════
# 엔딩 카드
# ══════════════════════════════════════════════════════════════════
def make_ending_clip(title: str, out_path: Path, duration: float = 2.0) -> bool:
    """
    엔딩 카드 생성.
    CUSTOM_ENDING_PATH 있으면 커스텀 이미지 사용 (제목 텍스트만 오버레이).
    없으면 자동 생성.
    """
    card = TMP_DIR / "ending.png"

    if CUSTOM_ENDING_PATH and Path(CUSTOM_ENDING_PATH).exists():
        # ── 커스텀 이미지 위에 제목만 오버레이 ───────────────────────
        _overlay_text_on_custom_bg(
            CUSTOM_ENDING_PATH, title, "", card,
            title_only=True
        )
    else:
        # ── 자동 생성 엔딩 카드 (완전히 else 블록 안) ─────────────────
        img  = Image.new("RGB", (TARGET_W, TARGET_H), (12, 10, 20))
        draw = ImageDraw.Draw(img)

        # 배경 그라데이션 (위: 진한 네이비 → 아래: 짙은 보라)
        for y in range(TARGET_H):
            t = y / TARGET_H
            r = int(12 + t * 30)
            g = int(10 + t * 5)
            b = int(20 + t * 40)
            draw.line([(0, y), (TARGET_W, y)], fill=(r, g, b))

        # 중앙 글로우 원형 (연보라 빛)
        glow_cx, glow_cy = TARGET_W // 2, TARGET_H // 2 - 60
        for radius in range(300, 0, -30):
            alpha = int(18 * (1 - radius / 300))
            overlay = Image.new("RGBA", (TARGET_W, TARGET_H), (0, 0, 0, 0))
            ov_draw = ImageDraw.Draw(overlay)
            ov_draw.ellipse([glow_cx - radius, glow_cy - radius,
                             glow_cx + radius, glow_cy + radius],
                            fill=(130, 80, 255, alpha))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(img)

        # 상단/하단 포인트 라인
        draw.rectangle([0, 0, TARGET_W, 8],   fill=(150, 100, 255))
        draw.rectangle([0, TARGET_H-8, TARGET_W, TARGET_H], fill=(150, 100, 255))

        # 채널명 (상단)
        ch_font = get_font(46)
        ch_text = "📋 위씨리스트"
        cw = draw.textbbox((0,0), ch_text, font=ch_font)[2]
        draw_text_with_outline(draw, (TARGET_W-cw)//2, 80,
                               ch_text, ch_font,
                               color=(200, 180, 255), outline_color=(0,0,0), outline_w=2)

        # 구분선
        draw.rectangle([100, 160, TARGET_W-100, 164], fill=(100, 80, 180))

        # 제목 (중앙, 대형)
        tf    = get_font(66)
        lines = wrap_text(draw, title, tf, TARGET_W - 100)
        lh    = draw.textbbox((0,0), "가", font=tf)[3] + 24
        total = lh * len(lines)
        sy    = TARGET_H // 2 - total // 2 - 40

        for i, line in enumerate(lines):
            tw = draw.textbbox((0,0), line, font=tf)[2]
            tx = (TARGET_W - tw) // 2
            ty = sy + i * lh
            draw.text((tx+4, ty+4), line, font=tf, fill=(0, 0, 0))
            draw_text_with_outline(draw, tx, ty, line, tf,
                                   color=(255, 255, 255),
                                   outline_color=(80, 50, 160), outline_w=3)

        # 하단 구독 유도
        sub_font = get_font(40)
        sub_text = "👆 구독하고 다음 영상도 확인하세요"
        sw = draw.textbbox((0,0), sub_text, font=sub_font)[2]
        draw.text(((TARGET_W-sw)//2, TARGET_H - 220), sub_text,
                  font=sub_font, fill=(180, 160, 220))

        # @wisslist
        wf   = get_font(38)
        wt   = "@wisslist"
        ww   = draw.textbbox((0,0), wt, font=wf)[2]
        draw.text(((TARGET_W-ww)//2, TARGET_H - 140), wt,
                  font=wf, fill=(130, 110, 200))

        img.save(str(card), "PNG")

    cmd = ["ffmpeg", "-y",
           "-loop", "1", "-i", str(card),
           "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
           "-r", "30", "-c:a", "aac", "-b:a", "128k",
           "-t", f"{duration:.1f}", "-pix_fmt", "yuv420p",
           str(out_path)]
    code, _, err = run_cmd(cmd, timeout=30)
    if code != 0:
        print(f"  ⚠️  엔딩 카드 실패:\n{err[-200:]}")
        return False
    return True


# ══════════════════════════════════════════════════════════════════
# 커스텀 배경 위에 텍스트만 오버레이 (핵심 함수)
# ══════════════════════════════════════════════════════════════════
def _overlay_text_on_custom_bg(bg_path: str, title: str, narration: str,
                                out_path: Path, title_only: bool = False):
    """
    커스텀 배경 위에 제목 텍스트만 오버레이.
    narration 자막은 make_subtitle_png + ffmpeg overlay로 별도 처리되므로 여기선 생략.
    """
    bg = Image.open(bg_path).convert("RGB")
    if bg.size != (TARGET_W, TARGET_H):
        bg = bg.resize((TARGET_W, TARGET_H), Image.LANCZOS)

    draw = ImageDraw.Draw(bg)

    # 상단 제목
    title_font = get_font(54)
    t_lines    = wrap_text(draw, title, title_font, TARGET_W - 80)
    lh         = draw.textbbox((0,0), "가", font=title_font)[3] + 16
    t_total    = lh * len(t_lines)
    t_y        = (HEADER_H - t_total) // 2 + 10

    for i, line in enumerate(t_lines):
        tw = draw.textbbox((0,0), line, font=title_font)[2]
        tx = (TARGET_W - tw) // 2
        ty = t_y + i * lh
        draw_text_with_outline(draw, tx, ty, line, title_font,
                               color=(255, 255, 255),
                               outline_color=(0, 0, 0), outline_w=4)

    bg.save(str(out_path), "PNG")
def concat_clips(clip_paths: list, out_path: Path) -> bool:
    list_file = TMP_DIR / "concat_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{str(p).replace(chr(92), '/')}'\n")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
           "-i", str(list_file), "-c", "copy", str(out_path)]
    code, _, err = run_cmd(cmd, timeout=120)
    if code != 0:
        print(f"  ⚠️  concat 실패:\n{err[-300:]}")
        return False
    return True


def apply_speed(in_path: Path, out_path: Path, speed: float = 1.5) -> bool:
    """
    영상+오디오 동시 배속.
    -r 30 으로 고정 프레임레이트 보장 → setpts 정확 동작.
    """
    cmd = ["ffmpeg", "-y", "-i", str(in_path),
           "-vf", f"setpts={1/speed:.6f}*PTS",
           "-af", f"atempo={speed}",
           "-r", "30",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-c:a", "aac", "-b:a", "128k",
           str(out_path)]
    code, _, err = run_cmd(cmd, timeout=180)
    if code != 0:
        print(f"  ⚠️  배속 실패:\n{err[-300:]}")
        return False
    return True


def add_bgm(video_path: Path, out_path: Path, bgm_volume: float = 0.15) -> bool:
    bgm_files = list(BGM_DIR.glob("*.mp3")) + list(BGM_DIR.glob("*.m4a"))
    if not bgm_files:
        print("  ℹ️  bgm/ 폴더에 mp3 없음 → BGM 없이 저장")
        shutil.copy(str(video_path), str(out_path))
        return True
    bgm = random.choice(bgm_files)
    print(f"  🎵 BGM: {bgm.name}")
    dur = get_audio_duration(str(video_path))
    af  = (f"[1:a]aloop=loop=-1:size=2000000000,"
           f"atrim=0:{dur:.3f},volume={bgm_volume}[bgm];"
           f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=3[aout]")
    cmd = ["ffmpeg", "-y", "-i", str(video_path), "-i", str(bgm),
           "-filter_complex", af, "-map", "0:v", "-map", "[aout]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", str(out_path)]
    code, _, err = run_cmd(cmd, timeout=120)
    if code != 0:
        print(f"  ⚠️  BGM 실패 → 저장\n{err[-200:]}")
        shutil.copy(str(video_path), str(out_path))
    return True


# ══════════════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════════════
def assemble(script_path=None):
    check_ffmpeg()

    if script_path is None:
        script_path = SCRIPT_PATH
    if not Path(script_path).exists():
        print(f"❌ 스크립트 없음: {script_path}")
        return None

    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    for d in [AUDIO_DIR, OUTPUT_DIR, BGM_DIR, TMP_DIR]:
        d.mkdir(exist_ok=True)

    title        = script.get("title", "WISSLIST")
    product_name = script.get("product_name", "")   # generate_script.py가 자동 기입
    segments     = script["segments"]

    print(f"\n🎬 조립 시작: {title}")
    if product_name:
        print(f"   제품명: {product_name}  (제품 이미지 우선 매칭 활성)")
    print("=" * 55)

    # ── 1. TTS (랜덤 목소리 선택 — 영상 당 1개 목소리 고정) ──────
    print("\n[1/6] 나레이션 생성 중...")
    tts_voice = random.choice(KO_VOICES)
    print(f"   🎙️  목소리: {tts_voice}")
    for i, seg in enumerate(segments):
        ap = AUDIO_DIR / f"seg_{i:02d}.mp3"
        make_tts(seg["narration"], ap, voice=tts_voice)
        seg["audio_path"]     = str(ap)
        seg["audio_duration"] = get_audio_duration(str(ap))
        print(f"       → {seg['audio_duration']:.2f}초")

    # ── 2. 세그먼트 클립 ──────────────────────────────────────────
    print("\n[2/6] 세그먼트 클립 생성 중...")
    used, clip_paths = set(), []

    for i, seg in enumerate(segments):
        dur  = seg["audio_duration"]
        tags = seg["visual_tag"]
        narr = seg["narration"]
        print(f"\n  Seg {i+1} | {dur:.2f}초 | {tags}")

        media_file  = None
        candidates  = find_media_candidates(tags, exclude_files=used,
                                            prefer_gif=True,
                                            product_name=product_name,
                                            max_candidates=5)
        if candidates:
            media_file = candidates[0]["file"]
            used.add(media_file)
            # 후보 목록을 함수 속성으로 전달 (재시도용)
            make_segment_clip._candidates = candidates[1:]
        else:
            make_segment_clip._candidates = []

        clip_out = TMP_DIR / f"clip_{i:02d}.mp4"
        ok = make_segment_clip(media_file, seg["audio_path"],
                               title, narr, dur, clip_out, i)
        if ok and clip_out.exists():
            clip_paths.append(clip_out)
            print(f"    ✅ clip_{i:02d}.mp4")
        else:
            print(f"    ❌ clip_{i:02d} 실패 → 건너뜀")

    if not clip_paths:
        print("❌ 생성된 클립 없음")
        return None

    # ── 3. 엔딩 카드 ──────────────────────────────────────────────
    print("\n[3/6] 엔딩 카드 생성 중...")
    ending = TMP_DIR / "clip_ending.mp4"
    if make_ending_clip(title, ending, duration=2.0):
        clip_paths.append(ending)
        print("  ✅ 엔딩 카드 추가")

    # ── 4. concat ─────────────────────────────────────────────────
    print("\n[4/6] 클립 합치는 중...")
    concat_out = TMP_DIR / "concat_raw.mp4"
    if not concat_clips(clip_paths, concat_out):
        return None
    print("  ✅ concat 완료")

    # ── 5. 1.5배속 ────────────────────────────────────────────────
    print("\n[5/6] 1.5배속 적용 중...")
    speed_out = TMP_DIR / "speed_1.5x.mp4"
    if apply_speed(concat_out, speed_out, speed=1.5):
        print("  ✅ 1.5배속 완료")
    else:
        speed_out = concat_out

    # ── 6. BGM + 최종 저장 ────────────────────────────────────────
    print("\n[6/6] BGM 믹싱 + 최종 저장 중...")
    safe  = "".join(c for c in title[:20]
                    if c.isalnum() or c in " _-").strip()
    final = OUTPUT_DIR / f"{safe}.mp4"
    add_bgm(speed_out, final)

    shutil.rmtree(TMP_DIR, ignore_errors=True)

    total_raw = sum(s["audio_duration"] for s in segments)
    print(f"\n✅ 완성: {final}")
    print(f"   원본: {total_raw:.1f}초 → 1.5배속 후: {total_raw/1.5:.1f}초")
    print(f"\n📋 설명란:\n{script.get('description_cta','')}")
    print(f"\n⚠️  {script.get('disclaimer','')}")
    return str(final)


if __name__ == "__main__":
    assemble()
