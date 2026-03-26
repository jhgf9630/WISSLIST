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
    배경 PNG 생성.
    구조:
      [상단 16%] 채널명/타이틀 텍스트
      [중단 45%] 미디어 박스 (회색 테두리, 내부는 투명으로 남김)
      [하단 35%] 나레이션 자막
    """
    img  = Image.new("RGB", (TARGET_W, TARGET_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # ── 상단 타이틀 바 ─────────────────────────────────────────────
    # 어두운 헤더 바
    draw.rectangle([0, 0, TARGET_W, int(TARGET_H * 0.17)],
                   fill=(30, 30, 30))

    title_font = get_font(52)
    t_lines    = wrap_text(draw, title, title_font,
                           max_width=TARGET_W - 60)
    line_h     = draw.textbbox((0,0), "가", font=title_font)[3] + 14
    t_total    = line_h * len(t_lines)
    t_y_start  = (int(TARGET_H * 0.17) - t_total) // 2

    for i, line in enumerate(t_lines):
        tw = draw.textbbox((0,0), line, font=title_font)[2]
        tx = (TARGET_W - tw) // 2
        ty = t_y_start + i * line_h
        draw.text((tx, ty), line, font=title_font, fill=(255, 255, 255))

    # ── 미디어 박스 테두리 ──────────────────────────────────────────
    bx1, by1 = BOX_X,        BOX_Y
    bx2, by2 = BOX_X + BOX_W, BOX_Y + BOX_H
    # 박스 내부: 검정 (나중에 GIF가 올라갈 자리)
    draw.rectangle([bx1, by1, bx2, by2], fill=(20, 20, 20))
    # 테두리
    draw.rectangle([bx1-4, by1-4, bx2+4, by2+4],
                   outline=(80, 80, 80), width=4)

    # ── 하단 자막 영역 ─────────────────────────────────────────────
    sub_font   = get_font(50)
    sub_lines  = wrap_text(draw, narration, sub_font,
                           max_width=TARGET_W - 80)
    sub_line_h = draw.textbbox((0,0), "가", font=sub_font)[3] + 16
    sub_total  = sub_line_h * len(sub_lines)

    # 자막 영역 시작: 박스 아래 60px
    sub_y_start = by2 + 60

    for i, line in enumerate(sub_lines):
        tw = draw.textbbox((0,0), line, font=sub_font)[2]
        tx = (TARGET_W - tw) // 2
        ty = sub_y_start + i * sub_line_h
        draw_text_with_outline(draw, tx, ty, line, sub_font,
                                color=(30,30,30),
                                outline_color=(200,200,200),
                                outline_w=2)

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
    card = TMP_DIR / "ending.png"

    img  = Image.new("RGB", (TARGET_W, TARGET_H), (20, 20, 30))
    draw = ImageDraw.Draw(img)

    # 상단 포인트 바
    draw.rectangle([0, 0, TARGET_W, 10], fill=(120, 80, 255))

    tf    = get_font(68)
    cf    = get_font(40)
    lines = wrap_text(draw, title, tf, TARGET_W - 80)
    lh    = draw.textbbox((0,0), "가", font=tf)[3] + 22
    total = lh * len(lines)
    sy    = TARGET_H // 2 - total // 2 - 30

    for i, line in enumerate(lines):
        tw = draw.textbbox((0,0), line, font=tf)[2]
        draw_text_with_outline(draw, (TARGET_W-tw)//2, sy+i*lh,
                               line, tf, (255,255,255), (0,0,0), 4)

    cw = draw.textbbox((0,0), "@wisslist", font=cf)[2]
    draw.text(((TARGET_W-cw)//2, TARGET_H-160), "@wisslist",
              font=cf, fill=(160, 140, 255))

    img.save(str(card), "PNG")

    cmd = ["ffmpeg", "-y",
           "-loop", "1", "-i", str(card),
           "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
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
