# =============================================
# WISSLIST - 영상 자동 조립 v11
# 실행: python D:\WISSLIST\scripts\assemble_video.py
#
# v11 핵심 수정:
#  - drawtext text= 이스케이프 문제 완전 해결
#    → 자막 텍스트를 임시 파일로 저장 후
#      textfile= 파라미터로 전달 (이스케이프 불필요)
#  - fontfile 경로 문제도 동시 해결
# =============================================

import json
import sys
import subprocess
import shutil
import random
import tempfile
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
FONT_PATH = r"C:\Windows\Fonts\malgun.ttf"   # 맑은 고딕


# ══════════════════════════════════════════════════════════════════
# subprocess 헬퍼
# ══════════════════════════════════════════════════════════════════
def run_cmd(cmd: list, timeout: int = 120) -> tuple:
    try:
        r = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        stdout = r.stdout.decode("utf-8", errors="replace") if r.stdout else ""
        stderr = r.stderr.decode("utf-8", errors="replace") if r.stderr else ""
        return r.returncode, stdout, stderr
    except FileNotFoundError:
        return 2, "", f"명령어를 찾을 수 없음: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 1, "", f"타임아웃 ({timeout}초)"
    except Exception as e:
        return 1, "", str(e)


# ══════════════════════════════════════════════════════════════════
# ffmpeg 확인
# ══════════════════════════════════════════════════════════════════
def check_ffmpeg():
    code, _, _ = run_cmd(["ffmpeg", "-version"], timeout=10)
    if code != 0:
        print("❌ ffmpeg를 찾을 수 없습니다. PATH 환경변수 등록 필요")
        sys.exit(1)
    print("✅ ffmpeg 확인 완료")


# ══════════════════════════════════════════════════════════════════
# TTS
# ══════════════════════════════════════════════════════════════════
def make_tts(text: str, out_path: Path, voice: str = "ko-KR-SunHiNeural"):
    base_args = ["--voice", voice, "--rate", "+5%",
                 "--text", text, "--write-media", str(out_path)]
    code, _, err = run_cmd(["edge-tts"] + base_args, timeout=30)
    if code != 0:
        code2, _, err2 = run_cmd(
            [sys.executable, "-m", "edge_tts"] + base_args, timeout=30)
        if code2 != 0:
            raise RuntimeError(f"TTS 실패. pip install edge-tts\n{err2[:200]}")
    print(f"  🎙️  {out_path.name}  ({out_path.stat().st_size//1024}KB)")


def get_audio_duration(path: str) -> float:
    _, out, _ = run_cmd([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ], timeout=15)
    try:
        return float(out.strip())
    except ValueError:
        return 2.0


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
# drawtext 필터 생성
# 핵심: 텍스트를 파일로 저장 → textfile= 로 전달
#       → text= 이스케이프 문제 완전 해결
# ══════════════════════════════════════════════════════════════════
def make_drawtext_filter(subtitle: str, textfile_path: Path) -> str:
    """
    자막 텍스트를 UTF-8 파일로 저장 후 textfile= 파라미터 사용.
    text= 에서 발생하는 한국어/특수문자 이스케이프 문제 원천 차단.
    """
    # 텍스트 파일 저장 (UTF-8)
    textfile_path.write_text(subtitle, encoding="utf-8")

    # textfile 경로: Windows 역슬래시 → 슬래시, 콜론 이스케이프
    tf = str(textfile_path).replace("\\", "/").replace(":", "\\:")

    # 폰트 경로 이스케이프
    fp = FONT_PATH.replace("\\", "/").replace(":", "\\:")
    font_opt = f"fontfile={fp}" if Path(FONT_PATH).exists() else "font=Arial"

    return (
        f"drawtext={font_opt}"
        f":textfile={tf}"
        f":fontsize=55"
        f":fontcolor=white"
        f":borderw=3"
        f":bordercolor=black"
        f":x=(w-text_w)/2"
        f":y=h*0.73"
        f":reload=1"
    )


# ══════════════════════════════════════════════════════════════════
# 세그먼트 클립 생성
# ══════════════════════════════════════════════════════════════════
def make_segment_clip(media_path, audio_path: str,
                      subtitle: str, duration: float,
                      out_path: Path, idx: int) -> bool:

    # 자막 텍스트파일 경로
    textfile = TMP_DIR / f"sub_{idx:02d}.txt"
    drawtext = make_drawtext_filter(subtitle, textfile)

    ext = Path(media_path).suffix.lower() if media_path else ""

    scale_pad = (
        f"scale={TARGET_W}:{TARGET_H}"
        f":force_original_aspect_ratio=decrease"
        f",pad={TARGET_W}:{TARGET_H}"
        f":(ow-iw)/2:(oh-ih)/2"
        f":black"
    )

    common_out = [
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-t", f"{duration:.3f}",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]

    if not media_path or not Path(media_path).exists():
        vf  = drawtext
        cmd = (["ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=black:s={TARGET_W}x{TARGET_H}:d={duration:.3f}",
                "-i", audio_path,
                "-vf", vf]
               + common_out)

    elif ext in (".jpg", ".jpeg", ".png", ".webp"):
        vf  = f"{scale_pad},{drawtext}"
        cmd = (["ffmpeg", "-y",
                "-loop", "1", "-i", media_path,
                "-i", audio_path,
                "-vf", vf]
               + common_out)

    else:   # gif / mp4 등
        vf  = f"{scale_pad},{drawtext}"
        cmd = (["ffmpeg", "-y",
                "-stream_loop", "-1", "-i", media_path,
                "-i", audio_path,
                "-vf", vf]
               + common_out)

    code, _, err = run_cmd(cmd, timeout=60)
    if code != 0:
        print(f"    ⚠️  clip 생성 실패:\n{err[-500:]}")
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
    cmd = ["ffmpeg", "-y", "-i", str(in_path),
           "-vf", f"setpts={1/speed:.4f}*PTS",
           "-af", f"atempo={speed}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-c:a", "aac", "-b:a", "128k", str(out_path)]
    code, _, err = run_cmd(cmd, timeout=120)
    if code != 0:
        print(f"  ⚠️  배속 실패:\n{err[-300:]}")
        return False
    return True


def add_bgm(video_path: Path, out_path: Path, bgm_volume: float = 0.15) -> bool:
    bgm_files = list(BGM_DIR.glob("*.mp3")) + list(BGM_DIR.glob("*.m4a"))
    if not bgm_files:
        print("  ℹ️  bgm/ 폴더에 mp3 없음 → BGM 없이 저장")
        print(f"     D:\\WISSLIST\\bgm\\ 에 mp3 넣으면 다음 실행부터 자동 적용")
        shutil.copy(str(video_path), str(out_path))
        return True

    bgm = random.choice(bgm_files)
    print(f"  🎵 BGM: {bgm.name}")
    dur = get_audio_duration(str(video_path))

    af = (
        f"[1:a]aloop=loop=-1:size=2000000000,"
        f"atrim=0:{dur:.3f},"
        f"volume={bgm_volume}[bgm];"
        f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=3[aout]"
    )
    cmd = ["ffmpeg", "-y",
           "-i", str(video_path), "-i", str(bgm),
           "-filter_complex", af,
           "-map", "0:v", "-map", "[aout]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
           str(out_path)]
    code, _, err = run_cmd(cmd, timeout=120)
    if code != 0:
        print(f"  ⚠️  BGM 실패 → BGM 없이 저장\n{err[-200:]}")
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
        print("→ today_prompt.txt → Claude.ai → today_script.json 저장 후 재실행")
        return None

    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    for d in [AUDIO_DIR, OUTPUT_DIR, BGM_DIR, TMP_DIR]:
        d.mkdir(exist_ok=True)

    print(f"\n🎬 조립 시작: {script['title']}")
    print("=" * 55)
    segments = script["segments"]

    # ── 1. TTS ────────────────────────────────────────────────────
    print("\n[1/5] 나레이션 생성 중...")
    for i, seg in enumerate(segments):
        ap = AUDIO_DIR / f"seg_{i:02d}.mp3"
        make_tts(seg["narration"], ap)
        seg["audio_path"]     = str(ap)
        seg["audio_duration"] = get_audio_duration(str(ap))
        print(f"       → {seg['audio_duration']:.2f}초")

    # ── 2. 세그먼트 클립 ──────────────────────────────────────────
    print("\n[2/5] 세그먼트 클립 생성 중...")
    used, clip_paths = set(), []

    for i, seg in enumerate(segments):
        dur   = seg["audio_duration"]
        tags  = seg["visual_tag"]
        sub   = seg["on_screen_text"]
        print(f"\n  Seg {i+1} | {dur:.2f}초 | {tags}")

        media      = find_best_media(tags, exclude_files=used, prefer_gif=True)
        media_file = None
        if media and Path(media["file"]).exists():
            used.add(media["file"])
            media_file = media["file"]

        clip_out = TMP_DIR / f"clip_{i:02d}.mp4"
        ok = make_segment_clip(media_file, seg["audio_path"],
                               sub, dur, clip_out, i)
        if ok:
            clip_paths.append(clip_out)
            print(f"    ✅ clip_{i:02d}.mp4")
        else:
            print(f"    ❌ clip_{i:02d} 실패 → 건너뜀")

    if not clip_paths:
        print("❌ 생성된 클립 없음")
        return None

    # ── 3. concat ─────────────────────────────────────────────────
    print("\n[3/5] 클립 합치는 중...")
    concat_out = TMP_DIR / "concat_raw.mp4"
    if not concat_clips(clip_paths, concat_out):
        return None
    print("  ✅ concat 완료")

    # ── 4. 1.5배속 ────────────────────────────────────────────────
    print("\n[4/5] 1.5배속 적용 중...")
    speed_out = TMP_DIR / "speed_1.5x.mp4"
    if not apply_speed(concat_out, speed_out, speed=1.5):
        speed_out = concat_out
    else:
        print("  ✅ 1.5배속 완료")

    # ── 5. BGM + 최종 저장 ────────────────────────────────────────
    print("\n[5/5] BGM 믹싱 + 최종 저장 중...")
    safe  = "".join(c for c in script["title"][:20]
                    if c.isalnum() or c in " _-").strip()
    final = OUTPUT_DIR / f"{safe}.mp4"
    add_bgm(speed_out, final)

    shutil.rmtree(TMP_DIR, ignore_errors=True)

    total_raw = sum(s["audio_duration"] for s in segments)
    total_out = total_raw / 1.5
    print(f"\n✅ 완성: {final}")
    print(f"   원본: {total_raw:.1f}초 → 1.5배속 후: {total_out:.1f}초")
    print(f"\n📋 설명란:\n{script.get('description_cta','')}")
    print(f"\n⚠️  {script.get('disclaimer','')}")
    return str(final)


if __name__ == "__main__":
    assemble()
