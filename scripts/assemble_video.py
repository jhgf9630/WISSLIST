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

BASE        = Path(BASE_DIR)
SCRIPT_PATH = BASE / "scripts_json" / "today_script.json"
AUDIO_DIR   = BASE / "audio"
OUTPUT_DIR  = BASE / "output"
TMP_DIR     = BASE / "tmp_clips"
BGM_DIR     = BASE / "bgm"

# 쇼츠 9:16 비율
TARGET_W, TARGET_H = 1080, 1920

# 미디어 박스 영역 (화면 중앙, 상단 20%~65%)
BOX_X      = 40
BOX_Y      = int(TARGET_H * 0.20)
BOX_W      = TARGET_W - 80
BOX_H      = int(TARGET_H * 0.45)

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


# ══════════════════════════════════════════════════════════════════
# TTS
# ══════════════════════════════════════════════════════════════════
def make_tts(text: str, out_path: Path, voice: str = "ko-KR-SunHiNeural"):
    """
    edge-tts로 TTS 생성.
    --text 인자로 한국어를 직접 넘기면 Windows subprocess에서
    인코딩 오류가 발생할 수 있으므로, 텍스트를 UTF-8 파일로 저장 후
    --file 옵션으로 전달. 이스케이프/인코딩 문제 완전 차단.
    """
    # 텍스트를 UTF-8 임시 파일로 저장
    txt_path = out_path.with_suffix(".txt")
    txt_path.write_text(text, encoding="utf-8")

    base_args = [
        "--voice", voice,
        "--rate", "+5%",
        "--file", str(txt_path),        # ← --text 대신 --file 사용
        "--write-media", str(out_path),
    ]

    code, _, _ = run_cmd(["edge-tts"] + base_args, timeout=30)
    if code != 0:
        code2, _, err2 = run_cmd(
            [sys.executable, "-m", "edge_tts"] + base_args, timeout=30)
        if code2 != 0:
            raise RuntimeError(
                f"TTS 실패. pip install edge-tts\n{err2[:300]}")

    # 임시 텍스트 파일 삭제
    try:
        txt_path.unlink()
    except Exception:
        pass

    print(f"  🎙️  {out_path.name}  ({out_path.stat().st_size//1024}KB)")


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
# 배경 프레임 생성 (레퍼런스 스타일)
# - 밝은 크림 배경
# - 상단 타이틀
# - 중앙 미디어 박스 (border)
# - 하단 자막 영역
# ══════════════════════════════════════════════════════════════════
def make_bg_frame(title: str, narration: str, out_path: Path):
    """
    배경 PNG 생성 (고품질 v2)
    구조:
      [상단 18%] 그라데이션 헤더 + 볼드 타이틀
      [중단 46%] 미디어 박스 (둥근 모서리 효과 + 그림자)
      [하단 36%] 자막 (흰 글자 + 반투명 배경 패널)
    """
    from PIL import ImageFilter

    # ── 배경: 밝은 크림 ────────────────────────────────────────────
    img  = Image.new("RGB", (TARGET_W, TARGET_H), (248, 245, 238))
    draw = ImageDraw.Draw(img)

    # 배경 미묘한 그라데이션 느낌 (상단 살짝 어둡게)
    for y in range(TARGET_H):
        t = y / TARGET_H
        r = int(248 - t * 8)
        g = int(245 - t * 10)
        b = int(238 - t * 15)
        draw.line([(0, y), (TARGET_W, y)], fill=(r, g, b))

    # ── 상단 헤더 (그라데이션 블랙) ────────────────────────────────
    header_h = int(TARGET_H * 0.18)
    for y in range(header_h):
        t  = y / header_h
        # 위쪽은 진한 검정, 아래쪽으로 살짝 밝아짐
        c  = int(15 + t * 20)
        draw.line([(0, y), (TARGET_W, y)], fill=(c, c, c))

    # 헤더 하단 포인트 라인 (연보라)
    draw.rectangle([0, header_h - 5, TARGET_W, header_h], fill=(180, 140, 255))

    # 타이틀 텍스트
    title_font = get_font(54)
    t_lines    = wrap_text(draw, title, title_font, TARGET_W - 80)
    lh         = draw.textbbox((0,0), "가", font=title_font)[3] + 16
    t_total    = lh * len(t_lines)
    t_y        = (header_h - t_total) // 2

    for i, line in enumerate(t_lines):
        tw = draw.textbbox((0,0), line, font=title_font)[2]
        tx = (TARGET_W - tw) // 2
        ty = t_y + i * lh
        # 미세한 그림자
        draw.text((tx+2, ty+2), line, font=title_font, fill=(0, 0, 0, 120))
        draw.text((tx, ty), line, font=title_font, fill=(255, 255, 255))

    # ── 미디어 박스 ────────────────────────────────────────────────
    bx1, by1 = BOX_X,         BOX_Y
    bx2, by2 = BOX_X + BOX_W, BOX_Y + BOX_H

    # 그림자 효과 (박스 오른쪽/아래에 어두운 사각형)
    shadow_off = 10
    draw.rectangle([bx1 + shadow_off, by1 + shadow_off,
                    bx2 + shadow_off, by2 + shadow_off],
                   fill=(160, 155, 145))

    # 박스 내부 (진한 회색 — 미디어가 올라갈 자리)
    draw.rectangle([bx1, by1, bx2, by2], fill=(25, 25, 25))

    # 박스 테두리 (두께 6)
    draw.rectangle([bx1-3, by1-3, bx2+3, by2+3],
                   outline=(70, 65, 60), width=6)

    # ── 자막 패널 (반투명 박스 + 텍스트) ──────────────────────────
    sub_panel_y = by2 + 40
    sub_panel_h = TARGET_H - sub_panel_y - 30

    # 반투명 패널
    panel = Image.new("RGBA", (TARGET_W - 60, sub_panel_h), (30, 28, 25, 210))
    img_rgba = img.convert("RGBA")
    img_rgba.paste(panel, (30, sub_panel_y), panel)
    img = img_rgba.convert("RGB")
    draw = ImageDraw.Draw(img)

    # 패널 테두리
    draw.rectangle([30, sub_panel_y, TARGET_W-30,
                    sub_panel_y + sub_panel_h],
                   outline=(100, 95, 90), width=2)

    # 자막 텍스트
    sub_font  = get_font(48)
    sub_lines = wrap_text(draw, narration, sub_font, TARGET_W - 120)
    slh       = draw.textbbox((0,0), "가", font=sub_font)[3] + 18
    s_total   = slh * len(sub_lines)
    sy        = sub_panel_y + (sub_panel_h - s_total) // 2

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
# 미디어 매칭 (GIF 우선)
# ══════════════════════════════════════════════════════════════════
def find_best_media(visual_tags: list, exclude_files: set = None,
                    prefer_gif: bool = True):
    if exclude_files is None:
        exclude_files = set()
    library = load_library()
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

    pool = scored_gif if (prefer_gif and scored_gif) else (scored_gif + scored_other)
    if not pool:
        pool = scored_other
    if not pool:
        return _fallback_pexels(visual_tags[0] if visual_tags else "food")

    max_score   = max(s for s, _ in pool)
    top_matches = [item for s, item in pool if s == max_score]
    chosen      = random.choice(top_matches)
    kind = "GIF" if chosen["file"].lower().endswith(".gif") else "IMG"
    print(f"  🎯 [{kind}] {Path(chosen['file']).name}  (점수:{max_score})")
    return chosen


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
# 구조: 배경PNG + 미디어(GIF/이미지) 박스 overlay
# ══════════════════════════════════════════════════════════════════
def make_segment_clip(media_path, audio_path: str,
                      title: str, narration: str,
                      duration: float,
                      out_path: Path, idx: int) -> bool:

    bg_png   = TMP_DIR / f"bg_{idx:02d}.png"
    media_mp4 = TMP_DIR / f"media_{idx:02d}.mp4"

    # 1. 배경 PNG 생성 (PIL)
    make_bg_frame(title, narration, bg_png)

    # 2. 배경 PNG → 고정 프레임 영상 (오디오 포함, -r 30 강제)
    bg_vid = TMP_DIR / f"bg_vid_{idx:02d}.mp4"
    cmd_bg = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(bg_png),
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-r", "30",                      # 고정 프레임레이트 → setpts 정확
        "-c:a", "aac", "-b:a", "128k",
        "-t", f"{duration:.3f}",
        "-pix_fmt", "yuv420p",
        str(bg_vid),
    ]
    code, _, err = run_cmd(cmd_bg, timeout=60)
    if code != 0:
        print(f"    ⚠️  배경 영상 생성 실패:\n{err[-300:]}")
        return False

    # 3. 미디어(GIF/이미지/영상)를 BOX 크기로 스케일 후 배경 위에 overlay
    if media_path and Path(media_path).exists():
        ext = Path(media_path).suffix.lower()

        # 미디어를 BOX_W x BOX_H 로 스케일 (비율 유지, 패드)
        scale_vf = (
            f"scale={BOX_W}:{BOX_H}"
            f":force_original_aspect_ratio=decrease"
            f",pad={BOX_W}:{BOX_H}:(ow-iw)/2:(oh-ih)/2:black"
        )

        # 미디어 클립 생성 (오디오 없음, -r 30)
        if ext in (".jpg", ".jpeg", ".png", ".webp"):
            cmd_m = ["ffmpeg", "-y",
                     "-loop", "1", "-i", media_path,
                     "-vf", scale_vf,
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                     "-r", "30", "-an",
                     "-t", f"{duration:.3f}",
                     "-pix_fmt", "yuv420p",
                     str(media_mp4)]
        else:  # gif / mp4
            cmd_m = ["ffmpeg", "-y",
                     "-stream_loop", "-1", "-i", media_path,
                     "-vf", scale_vf,
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                     "-r", "30", "-an",
                     "-t", f"{duration:.3f}",
                     "-pix_fmt", "yuv420p",
                     str(media_mp4)]

        code2, _, err2 = run_cmd(cmd_m, timeout=60)
        if code2 != 0:
            print(f"    ⚠️  미디어 변환 실패 → 배경만 사용\n{err2[-200:]}")
            shutil.copy(str(bg_vid), str(out_path))
            return out_path.exists()

        # 배경 위에 미디어 overlay (BOX_X, BOX_Y 위치)
        overlay_vf = f"overlay={BOX_X}:{BOX_Y}"
        cmd_ov = [
            "ffmpeg", "-y",
            "-i", str(bg_vid),
            "-i", str(media_mp4),
            "-filter_complex", overlay_vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-r", "30",
            "-c:a", "copy",
            "-t", f"{duration:.3f}",
            "-pix_fmt", "yuv420p",
            str(out_path),
        ]
        code3, _, err3 = run_cmd(cmd_ov, timeout=60)
        if code3 != 0:
            print(f"    ⚠️  overlay 실패 → 배경만 사용\n{err3[-200:]}")
            shutil.copy(str(bg_vid), str(out_path))
    else:
        # 미디어 없음 → 배경 영상 그대로
        shutil.copy(str(bg_vid), str(out_path))

    return out_path.exists()


# ══════════════════════════════════════════════════════════════════
# 엔딩 카드
# ══════════════════════════════════════════════════════════════════
def make_ending_clip(title: str, out_path: Path, duration: float = 2.0) -> bool:
    """
    고품질 엔딩 카드 (v2)
    - 그라데이션 배경
    - 채널 로고 영역
    - 굵은 제목 + 그림자
    - 하단 구독 유도 문구
    """
    card = TMP_DIR / "ending.png"
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
        # 그림자
        draw.text((tx+4, ty+4), line, font=tf, fill=(0, 0, 0))
        # 본문
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
# concat + 배속 + BGM
# ══════════════════════════════════════════════════════════════════
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

    title    = script.get("title", "WISSLIST")
    segments = script["segments"]

    print(f"\n🎬 조립 시작: {title}")
    print("=" * 55)

    # ── 1. TTS ────────────────────────────────────────────────────
    print("\n[1/6] 나레이션 생성 중...")
    for i, seg in enumerate(segments):
        ap = AUDIO_DIR / f"seg_{i:02d}.mp3"
        make_tts(seg["narration"], ap)
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

        media      = find_best_media(tags, exclude_files=used, prefer_gif=True)
        media_file = None
        if media and Path(media["file"]).exists():
            used.add(media["file"])
            media_file = media["file"]

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
