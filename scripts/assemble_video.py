# =============================================
# WISSLIST - 영상 자동 조립 v5
# 실행: python D:\WISSLIST\scripts\assemble_video.py
#
# v5 수정:
#  - Windows Python 3.12 asyncio 오류 해결
#    (asyncio.run() 루프 반복 → 단일 async 함수로 통합)
#  - GIF 우선 매칭 + 루프 처리
#  - 오디오 실제 길이 기준 클립 맞춤
#  - 고화질 출력 (bitrate 4000k, crf 18)
# =============================================

import asyncio
import json
import sys
import os
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
# TTS — Windows asyncio 안전 버전
# asyncio.run()을 루프 안에서 반복 호출하면 Win32에서 crash
# → 모든 segment를 단일 async 함수에서 한 번에 처리
# ══════════════════════════════════════════════════════════════════
async def _generate_all_tts(segments: list, voice: str = "ko-KR-SunHiNeural"):
    """모든 segment의 TTS를 비동기로 한 번에 생성"""
    import edge_tts

    tasks = []
    for i, seg in enumerate(segments):
        ap = AUDIO_DIR / f"seg_{i:02d}.mp3"
        seg["audio_path"] = str(ap)
        comm = edge_tts.Communicate(
            text=seg["narration"], voice=voice, rate="+5%"
        )
        tasks.append(comm.save(str(ap)))

    # 모든 TTS 동시 생성
    await asyncio.gather(*tasks)


def run_tts(segments: list, voice: str = "ko-KR-SunHiNeural"):
    """Windows 호환 asyncio 실행 — 단 1회만 호출"""
    # Python 3.10+ Windows 에서 ProactorEventLoop 문제 우회
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(_generate_all_tts(segments, voice))


def get_audio_duration(path: str) -> float:
    clip = AudioFileClip(path)
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
def _set_duration(clip, duration):
    if MOVIEPY_V == 1:
        return clip.set_duration(duration)
    else:
        return clip.with_duration(duration)


def _resize(clip, height):
    if MOVIEPY_V == 1:
        return clip.resize(height=height)
    else:
        return clip.resized(height=height)


def _pad_to_vertical(clip, duration):
    """1080x1920 맞춤 + 좌우 검정 패딩"""
    clip = _set_duration(clip, duration)
    w = clip.size[0]

    if w < TARGET_W:
        bg    = ColorClip((TARGET_W, TARGET_H), color=(0,0,0), duration=duration)
        x_off = (TARGET_W - w) // 2
        if MOVIEPY_V == 1:
            clip = clip.set_position((x_off, 0))
        else:
            clip = clip.with_position((x_off, 0))
        clip = CompositeVideoClip([bg, clip], size=(TARGET_W, TARGET_H))
        clip = _set_duration(clip, duration)

    return clip


def make_clip(media_path: str, duration: float):
    ext = Path(media_path).suffix.lower()

    if ext in (".jpg", ".jpeg", ".png", ".webp"):
        # ── 정지 이미지 ──────────────────────────────────────────
        clip = ImageClip(media_path) if MOVIEPY_V == 1 \
               else ImageClip(media_path, duration=duration)
        clip = _resize(clip, TARGET_H)
        clip = _pad_to_vertical(clip, duration)

    elif ext == ".gif":
        # ── GIF — duration만큼 루프 ───────────────────────────────
        try:
            raw   = VideoFileClip(media_path)
            loops = max(1, int(duration / raw.duration) + 1)
            if MOVIEPY_V == 1:
                from moviepy.video.fx.all import loop as fx_loop
                clip = fx_loop(raw, n=loops)
                clip = clip.subclip(0, duration)
            else:
                from moviepy import vfx
                clip = raw.with_effects([vfx.Loop(n=loops)])
                clip = clip.subclipped(0, duration)
            clip = _resize(clip, TARGET_H)
            clip = _pad_to_vertical(clip, duration)
        except Exception as e:
            print(f"    ⚠️  GIF 로드 실패({e}) → 검정 배경")
            clip = ColorClip((TARGET_W, TARGET_H), color=(0,0,0), duration=duration)

    else:
        # ── 영상 ─────────────────────────────────────────────────
        try:
            raw      = VideoFileClip(media_path)
            use_dur  = min(duration, raw.duration)
            if MOVIEPY_V == 1:
                clip = raw.subclip(0, use_dur)
            else:
                clip = raw.subclipped(0, use_dur)
            clip = _resize(clip, TARGET_H)
            clip = _pad_to_vertical(clip, duration)
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

    # ── 1. TTS 전체 한 번에 생성 (Windows asyncio 안전) ───────────
    print("\n[1/3] 나레이션 생성 중...")
    run_tts(segments, voice="ko-KR-SunHiNeural")

    # 오디오 길이 측정
    for i, seg in enumerate(segments):
        seg["audio_duration"] = get_audio_duration(seg["audio_path"])
        size_kb = Path(seg["audio_path"]).stat().st_size // 1024
        print(f"  🎙️  seg_{i:02d}.mp3  ({size_kb}KB) → {seg['audio_duration']:.2f}초")

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
            if MOVIEPY_V == 1:
                video = video.set_audio(audio)
            else:
                video = video.with_audio(audio)
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
