# =============================================
# WISSLIST - 영상 자동 조립 v6
# 실행: python D:\WISSLIST\scripts\assemble_video.py
#
# v6 핵심 변경:
#  - asyncio 완전 제거 → edge-tts CLI subprocess 호출
#    (Windows Python 3.12 socketpair 오류 근본 해결)
#  - GIF 우선 매칭 + 루프 처리
#  - 오디오 실제 길이 기준 클립 맞춤
#  - 고화질 출력
# =============================================

import json
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import BASE_DIR
from library import load_library

BASE        = Path(BASE_DIR)
SCRIPT_PATH = BASE / "scripts_json" / "today_script.json"
AUDIO_DIR   = BASE / "audio"
OUTPUT_DIR  = BASE / "output"

TARGET_W, TARGET_H = 1080, 1920

# ── moviepy 버전 호환 ─────────────────────────────────────────────
try:
    from moviepy.editor import (
        VideoFileClip, ImageClip, AudioFileClip, TextClip,
        CompositeVideoClip, concatenate_videoclips, ColorClip,
    )
    MOVIEPY_V = 1
    print("✅ moviepy v1 로드됨")
except ModuleNotFoundError:
    try:
        from moviepy import (
            VideoFileClip, ImageClip, AudioFileClip, TextClip,
            CompositeVideoClip, concatenate_videoclips, ColorClip,
        )
        MOVIEPY_V = 2
        print("✅ moviepy v2 로드됨")
    except ImportError:
        print("❌ moviepy 없음. pip install \"moviepy==1.0.3\"")
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════
# TTS — asyncio 완전 제거, subprocess로 edge-tts CLI 직접 호출
# ══════════════════════════════════════════════════════════════════
def make_tts(text: str, out_path: Path, voice: str = "ko-KR-SunHiNeural"):
    """
    edge-tts CLI를 subprocess로 실행.
    asyncio / socket 문제와 완전히 무관하게 동작.
    """
    cmd = [
        "edge-tts",
        "--voice", voice,
        "--rate", "+5%",        # 약간 빠르게 (자연스러운 쇼츠 속도)
        "--text", text,
        "--write-media", str(out_path),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
        size_kb = out_path.stat().st_size // 1024
        print(f"  🎙️  {out_path.name}  ({size_kb}KB)")
    except FileNotFoundError:
        # edge-tts 명령이 PATH에 없는 경우 python -m edge_tts 로 재시도
        cmd2 = [sys.executable, "-m", "edge_tts"] + cmd[1:]
        result = subprocess.run(cmd2, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"edge-tts 실패: {result.stderr.strip()}")
        size_kb = out_path.stat().st_size // 1024
        print(f"  🎙️  {out_path.name}  ({size_kb}KB)")


def get_audio_duration(path: str) -> float:
    clip = AudioFileClip(str(path))
    dur  = clip.duration
    clip.close()
    return dur


# ══════════════════════════════════════════════════════════════════
# 미디어 매칭 (GIF 우선)
# ══════════════════════════════════════════════════════════════════
def find_best_media(visual_tags: list,
                    exclude_files: set = None,
                    prefer_gif: bool = True):
    import random
    if exclude_files is None:
        exclude_files = set()

    library = load_library()
    scored_gif   = []
    scored_other = []

    for item in library:
        if item["file"] in exclude_files:
            continue
        if not Path(item["file"]).exists():
            continue
        score = len(set(visual_tags) & set(item["all_tags"]))
        if score == 0:
            continue
        if item["file"].lower().endswith(".gif"):
            scored_gif.append((score, item))
        else:
            scored_other.append((score, item))

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
        data  = requests.get(photo["src"]["large"], timeout=15).content
        path.write_bytes(data)
        entry = {"file": str(path), "category": "fallback",
                 "source": photo.get("url",""), "query": query,
                 "provider": "pexels", "all_tags": [query],
                 "clip_verified": False}
        add_entry(entry)
        print(f"  📥 폴백 다운로드: {path.name}")
        return entry
    except Exception as e:
        print(f"  ❌ 폴백 실패: {e}")
        return None


# ══════════════════════════════════════════════════════════════════
# 클립 생성
# ══════════════════════════════════════════════════════════════════
def _v1_duration(clip, d):  return clip.set_duration(d)
def _v2_duration(clip, d):  return clip.with_duration(d)
def _set_dur(clip, d):
    return _v1_duration(clip, d) if MOVIEPY_V == 1 else _v2_duration(clip, d)

def _v1_resize(clip, h):    return clip.resize(height=h)
def _v2_resize(clip, h):    return clip.resized(height=h)
def _resize_h(clip, h):
    return _v1_resize(clip, h) if MOVIEPY_V == 1 else _v2_resize(clip, h)

def _set_pos(clip, pos):
    return clip.set_position(pos) if MOVIEPY_V == 1 else clip.with_position(pos)

def _pad_to_vertical(clip, duration):
    """1080×1920 맞춤 패딩"""
    clip = _set_dur(clip, duration)
    w    = clip.size[0]
    if w < TARGET_W:
        bg    = ColorClip((TARGET_W, TARGET_H), color=(0,0,0), duration=duration)
        x_off = (TARGET_W - w) // 2
        clip  = _set_pos(clip, (x_off, 0))
        clip  = CompositeVideoClip([bg, clip], size=(TARGET_W, TARGET_H))
        clip  = _set_dur(clip, duration)
    return clip


def make_clip(media_path: str, duration: float):
    ext = Path(media_path).suffix.lower()

    if ext in (".jpg", ".jpeg", ".png", ".webp"):
        clip = (ImageClip(media_path)
                if MOVIEPY_V == 1
                else ImageClip(media_path, duration=duration))
        clip = _resize_h(clip, TARGET_H)
        clip = _pad_to_vertical(clip, duration)

    elif ext == ".gif":
        try:
            raw   = VideoFileClip(media_path)
            loops = max(1, int(duration / raw.duration) + 1)
            if MOVIEPY_V == 1:
                from moviepy.video.fx.all import loop as fx_loop
                clip = fx_loop(raw, n=loops).subclip(0, duration)
            else:
                from moviepy import vfx
                clip = raw.with_effects([vfx.Loop(n=loops)]).subclipped(0, duration)
            clip = _resize_h(clip, TARGET_H)
            clip = _pad_to_vertical(clip, duration)
        except Exception as e:
            print(f"    ⚠️  GIF 로드 실패({e}) → 검정 배경")
            clip = ColorClip((TARGET_W, TARGET_H), color=(0,0,0), duration=duration)

    else:
        try:
            raw     = VideoFileClip(media_path)
            use_dur = min(duration, raw.duration)
            clip    = (raw.subclip(0, use_dur) if MOVIEPY_V == 1
                       else raw.subclipped(0, use_dur))
            clip    = _resize_h(clip, TARGET_H)
            clip    = _pad_to_vertical(clip, duration)
        except Exception as e:
            print(f"    ⚠️  영상 로드 실패({e}) → 검정 배경")
            clip = ColorClip((TARGET_W, TARGET_H), color=(0,0,0), duration=duration)

    return clip


# ══════════════════════════════════════════════════════════════════
# 자막 오버레이
# ══════════════════════════════════════════════════════════════════
def add_subtitle(video_clip, text: str, duration: float):
    if not text.strip():
        return video_clip
    try:
        if MOVIEPY_V == 1:
            txt = (TextClip(
                text,
                fontsize=58, color="white",
                stroke_color="black", stroke_width=3,
                method="caption", size=(TARGET_W - 80, None),
                align="center",
            )
            .set_duration(duration)
            .set_position(("center", 0.72), relative=True))
        else:
            txt = (TextClip(
                text=text,
                font_size=58, color="white",
                stroke_color="black", stroke_width=3,
                method="caption", size=(TARGET_W - 80, None),
                duration=duration,
            )
            .with_position(("center", 0.72), relative=True))
        return CompositeVideoClip([video_clip, txt])
    except Exception as e:
        print(f"    ⚠️  자막 실패({e}), 자막 없이 계속")
        return video_clip


# ══════════════════════════════════════════════════════════════════
# 메인 조립
# ══════════════════════════════════════════════════════════════════
def assemble(script_path=None):
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

    print(f"\n🎬 조립 시작: {script['title']}")
    print("=" * 55)

    segments = script["segments"]

    # ── 1. TTS 생성 (subprocess, asyncio 없음) ────────────────────
    print("\n[1/3] 나레이션 생성 중...")
    for i, seg in enumerate(segments):
        ap = AUDIO_DIR / f"seg_{i:02d}.mp3"
        make_tts(seg["narration"], ap)
        seg["audio_path"]     = str(ap)
        seg["audio_duration"] = get_audio_duration(str(ap))
        print(f"       → 실제 길이: {seg['audio_duration']:.2f}초")

    # ── 2. 클립 조립 ──────────────────────────────────────────────
    print("\n[2/3] 클립 조립 중...")
    used  = set()
    clips = []

    for i, seg in enumerate(segments):
        dur  = seg["audio_duration"]
        tags = seg["visual_tag"]
        print(f"\n  Seg {i+1} | {seg['time']} | {dur:.2f}초 | 태그: {tags}")

        media = find_best_media(tags, exclude_files=used, prefer_gif=True)

        if media and Path(media["file"]).exists():
            used.add(media["file"])
            video = make_clip(media["file"], dur)
        else:
            print("    ⚠️  미디어 없음 → 검정 배경")
            video = ColorClip((TARGET_W, TARGET_H), color=(0,0,0), duration=dur)

        # 오디오
        try:
            audio = AudioFileClip(seg["audio_path"])
            video = (video.set_audio(audio) if MOVIEPY_V == 1
                     else video.with_audio(audio))
        except Exception as e:
            print(f"    ⚠️  오디오 실패: {e}")

        # 자막
        video = add_subtitle(video, seg["on_screen_text"], dur)
        clips.append(video)

    # ── 3. 최종 합치기 + 저장 ─────────────────────────────────────
    print("\n[3/3] 최종 영상 합치는 중...")
    final = concatenate_videoclips(clips, method="compose")

    safe  = "".join(c for c in script["title"][:20]
                    if c.isalnum() or c in " _-").strip()
    out   = OUTPUT_DIR / f"{safe}.mp4"

    final.write_videofile(
        str(out),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        bitrate="4000k",
        audio_bitrate="192k",
        ffmpeg_params=["-crf", "18"],
        logger=None,
        threads=4,
    )

    total_sec = sum(s["audio_duration"] for s in segments)
    print(f"\n✅ 완성: {out}")
    print(f"   총 길이: {total_sec:.1f}초")
    print(f"\n📋 설명란:\n{script.get('description_cta','')}")
    print(f"\n⚠️  {script.get('disclaimer','')}")
    return str(out)


if __name__ == "__main__":
    assemble()
