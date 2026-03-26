# =============================================
# WISSLIST - 영상 자동 조립 v7 (ffmpeg 직접 구동)
# 실행: python D:\WISSLIST\scripts\assemble_video.py
#
# v7 개선사항:
#  1. 자막 - ffmpeg drawtext 필터 (한국어 지원)
#  2. BGM   - D:\WISSLIST\bgm\ 폴더의 mp3 자동 적용
#  3. 속도  - moviepy 제거, ffmpeg subprocess 직접 사용
#             → 50초 영상 기준 30분 → 1~2분으로 단축
#  4. 1.5배속 - ffmpeg setpts + atempo 필터
# =============================================

import json
import sys
import subprocess
import shutil
import random
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import BASE_DIR
from library import load_library

BASE        = Path(BASE_DIR)
SCRIPT_PATH = BASE / "scripts_json" / "today_script.json"
AUDIO_DIR   = BASE / "audio"
OUTPUT_DIR  = BASE / "output"
TMP_DIR     = BASE / "tmp_clips"
BGM_DIR     = BASE / "bgm"

TARGET_W, TARGET_H = 1080, 1920
FONT_PATH = "C:/Windows/Fonts/malgun.ttf"   # 맑은 고딕 (Windows 기본)


# ══════════════════════════════════════════════════════════════════
# ffmpeg 존재 확인
# ══════════════════════════════════════════════════════════════════
def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        print("❌ ffmpeg가 설치되어 있지 않습니다.")
        print("   https://ffmpeg.org/download.html 에서 다운로드 후")
        print("   PATH에 추가하세요.")
        sys.exit(1)
    print("✅ ffmpeg 확인 완료")


# ══════════════════════════════════════════════════════════════════
# TTS — edge-tts CLI (asyncio 없음)
# ══════════════════════════════════════════════════════════════════
def make_tts(text: str, out_path: Path, voice: str = "ko-KR-SunHiNeural"):
    cmd = [
        "edge-tts",
        "--voice", voice,
        "--rate", "+5%",
        "--text", text,
        "--write-media", str(out_path),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip())
    except FileNotFoundError:
        cmd2 = [sys.executable, "-m", "edge_tts"] + cmd[1:]
        r = subprocess.run(cmd2, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise RuntimeError(f"edge-tts 실패: {r.stderr.strip()}")
    size_kb = out_path.stat().st_size // 1024
    print(f"  🎙️  {out_path.name}  ({size_kb}KB)")


def get_audio_duration(path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return float(r.stdout.strip())


# ══════════════════════════════════════════════════════════════════
# 미디어 매칭 (GIF 우선)
# ══════════════════════════════════════════════════════════════════
def find_best_media(visual_tags: list,
                    exclude_files: set = None,
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
    headers      = {"Authorization": PEXELS_API_KEY}
    url          = (f"https://api.pexels.com/v1/search"
                    f"?query={requests.utils.quote(query)}&per_page=1")
    fallback_dir = BASE / "media_library" / "fallback"
    fallback_dir.mkdir(parents=True, exist_ok=True)
    try:
        res   = requests.get(url, headers=headers, timeout=10).json()
        photo = res["photos"][0]
        path  = fallback_dir / f"pxl_{photo['id']}.jpg"
        path.write_bytes(requests.get(photo["src"]["large"], timeout=15).content)
        entry = {"file": str(path), "category": "fallback",
                 "source": photo.get("url",""), "query": query,
                 "provider": "pexels", "all_tags": [query],
                 "clip_verified": False}
        add_entry(entry)
        print(f"  📥 폴백: {path.name}")
        return entry
    except Exception as e:
        print(f"  ❌ 폴백 실패: {e}")
        return None


# ══════════════════════════════════════════════════════════════════
# ffmpeg로 단일 세그먼트 클립 생성 (빠름)
# ══════════════════════════════════════════════════════════════════
def _escape_drawtext(text: str) -> str:
    """ffmpeg drawtext 특수문자 이스케이프"""
    for ch in ["\\", "'", ":", "[", "]"]:
        text = text.replace(ch, "\\" + ch)
    return text


def make_segment_clip(media_path: str, audio_path: str,
                      subtitle: str, duration: float,
                      out_path: Path) -> bool:
    """
    ffmpeg 한 번으로 [영상/이미지/GIF] + [오디오] + [자막] → mp4 출력
    """
    ext = Path(media_path).suffix.lower() if media_path else ""

    # ── 자막 drawtext 필터 ────────────────────────────────────────
    safe_sub = _escape_drawtext(subtitle)
    font_arg = f"fontfile='{FONT_PATH}'" if Path(FONT_PATH).exists() else "font=Malgun Gothic"

    drawtext = (
        f"drawtext={font_arg}"
        f":text='{safe_sub}'"
        f":fontsize=55"
        f":fontcolor=white"
        f":borderw=3"
        f":bordercolor=black"
        f":x=(w-text_w)/2"          # 가로 중앙
        f":y=h*0.73"                 # 화면 73% 위치
        f":line_spacing=8"
    )

    # ── 영상 소스 준비 ────────────────────────────────────────────
    if not media_path or not Path(media_path).exists():
        # 검정 배경
        vf = f"color=black:s={TARGET_W}x{TARGET_H}:d={duration}[v_raw];[v_raw]{drawtext}"
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=black:s={TARGET_W}x{TARGET_H}:d={duration}",
            "-i", audio_path,
            "-vf", drawtext,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            str(out_path),
        ]

    elif ext in (".jpg", ".jpeg", ".png", ".webp"):
        # 정지 이미지 → scale + pad → drawtext
        vf = (
            f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
            f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:black,"
            f"{drawtext}"
        )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(media_path),
            "-i", audio_path,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            str(out_path),
        ]

    elif ext == ".gif":
        # GIF → loop + scale + drawtext
        vf = (
            f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
            f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:black,"
            f"{drawtext}"
        )
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(media_path),   # 무한 루프
            "-i", audio_path,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            str(out_path),
        ]

    else:
        # 영상 파일
        vf = (
            f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
            f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:black,"
            f"{drawtext}"
        )
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(media_path),
            "-i", audio_path,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            str(out_path),
        ]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"    ⚠️  ffmpeg 오류:\n{r.stderr[-500:]}")
        return False
    return True


# ══════════════════════════════════════════════════════════════════
# ffmpeg concat + 1.5배속 + BGM
# ══════════════════════════════════════════════════════════════════
def concat_clips(clip_paths: list, out_path: Path) -> bool:
    """ffmpeg concat demuxer로 클립 합치기 (매우 빠름)"""
    list_file = TMP_DIR / "concat_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{str(p).replace(chr(92), '/')}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(out_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ⚠️  concat 오류:\n{r.stderr[-300:]}")
        return False
    return True


def apply_speed(in_path: Path, out_path: Path, speed: float = 1.5) -> bool:
    """영상 전체 재생속도 변경 (영상 + 오디오 동시)"""
    vf = f"setpts={1/speed:.4f}*PTS"          # 영상 빠르게
    af = f"atempo={speed}"                      # 오디오 빠르게 (최대 2.0)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(in_path),
        "-vf", vf,
        "-af", af,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        str(out_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ⚠️  속도 변경 오류:\n{r.stderr[-300:]}")
        return False
    return True


def add_bgm(video_path: Path, out_path: Path, bgm_volume: float = 0.15) -> bool:
    """
    BGM 폴더에서 mp3 자동 선택 후 믹싱.
    BGM 없으면 건너뜀.
    bgm_volume: 0.0~1.0 (기본 0.15 = 나레이션 방해 안 되는 수준)
    """
    bgm_files = list(BGM_DIR.glob("*.mp3")) + list(BGM_DIR.glob("*.m4a"))
    if not bgm_files:
        print("  ℹ️  BGM 파일 없음 → BGM 없이 저장")
        print(f"     D:\\WISSLIST\\bgm\\ 폴더에 mp3 넣으면 자동 적용됩니다.")
        shutil.copy(str(video_path), str(out_path))
        return True

    bgm = random.choice(bgm_files)
    print(f"  🎵 BGM: {bgm.name}")

    # 영상 길이 파악
    dur = get_audio_duration(str(video_path))

    # BGM을 영상 길이에 맞춰 루프 + 볼륨 조절 후 믹싱
    af = (
        f"[1:a]aloop=loop=-1:size=2e+09,atrim=0:{dur:.3f},"
        f"volume={bgm_volume}[bgm];"
        f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=3[aout]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(bgm),
        "-filter_complex", af,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        str(out_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ⚠️  BGM 믹싱 실패 → BGM 없이 저장\n{r.stderr[-300:]}")
        shutil.copy(str(video_path), str(out_path))
    return True


# ══════════════════════════════════════════════════════════════════
# 메인 조립
# ══════════════════════════════════════════════════════════════════
def assemble(script_path=None):
    check_ffmpeg()

    if script_path is None:
        script_path = SCRIPT_PATH

    if not Path(script_path).exists():
        print(f"❌ 스크립트 없음: {script_path}")
        print("→ today_prompt.txt → Claude.ai → today_script.json 저장 후 재실행")
        return None

    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    AUDIO_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    BGM_DIR.mkdir(exist_ok=True)
    TMP_DIR.mkdir(exist_ok=True)

    print(f"\n🎬 조립 시작: {script['title']}")
    print("=" * 55)
    segments = script["segments"]

    # ── 1. TTS 생성 ────────────────────────────────────────────────
    print("\n[1/5] 나레이션 생성 중...")
    for i, seg in enumerate(segments):
        ap = AUDIO_DIR / f"seg_{i:02d}.mp3"
        make_tts(seg["narration"], ap)
        seg["audio_path"]     = str(ap)
        seg["audio_duration"] = get_audio_duration(str(ap))
        print(f"       → {seg['audio_duration']:.2f}초")

    # ── 2. 세그먼트별 클립 생성 (ffmpeg) ──────────────────────────
    print("\n[2/5] 세그먼트 클립 생성 중...")
    used       = set()
    clip_paths = []

    for i, seg in enumerate(segments):
        dur  = seg["audio_duration"]
        tags = seg["visual_tag"]
        sub  = seg["on_screen_text"]
        print(f"\n  Seg {i+1} | {dur:.2f}초 | {tags}")

        media = find_best_media(tags, exclude_files=used, prefer_gif=True)
        media_file = None
        if media and Path(media["file"]).exists():
            used.add(media["file"])
            media_file = media["file"]

        clip_out = TMP_DIR / f"clip_{i:02d}.mp4"
        ok = make_segment_clip(media_file, seg["audio_path"],
                               sub, dur, clip_out)
        if ok:
            clip_paths.append(clip_out)
            print(f"    ✅ clip_{i:02d}.mp4")
        else:
            print(f"    ❌ clip_{i:02d} 생성 실패 → 건너뜀")

    if not clip_paths:
        print("❌ 생성된 클립 없음")
        return None

    # ── 3. 클립 합치기 (concat) ─────────────────────────────────────
    print("\n[3/5] 클립 합치는 중...")
    concat_out = TMP_DIR / "concat_raw.mp4"
    if not concat_clips(clip_paths, concat_out):
        return None
    print("  ✅ concat 완료")

    # ── 4. 1.5배속 적용 ─────────────────────────────────────────────
    print("\n[4/5] 1.5배속 적용 중...")
    speed_out = TMP_DIR / "speed_1.5x.mp4"
    if not apply_speed(concat_out, speed_out, speed=1.5):
        speed_out = concat_out   # 실패 시 원본 사용
    else:
        print("  ✅ 1.5배속 완료")

    # ── 5. BGM 믹싱 → 최종 저장 ─────────────────────────────────────
    print("\n[5/5] BGM 믹싱 + 최종 저장 중...")
    safe  = "".join(c for c in script["title"][:20]
                    if c.isalnum() or c in " _-").strip()
    final = OUTPUT_DIR / f"{safe}.mp4"
    add_bgm(speed_out, final)

    # 임시 파일 정리
    shutil.rmtree(TMP_DIR, ignore_errors=True)

    total_raw = sum(s["audio_duration"] for s in segments)
    total_out = total_raw / 1.5
    print(f"\n✅ 완성: {final}")
    print(f"   원본 길이: {total_raw:.1f}초 → 1.5배속 후: {total_out:.1f}초")
    print(f"\n📋 설명란:\n{script.get('description_cta','')}")
    print(f"\n⚠️  {script.get('disclaimer','')}")
    return str(final)


if __name__ == "__main__":
    assemble()
