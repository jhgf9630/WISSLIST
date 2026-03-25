# =============================================
# WISSLIST - 영상 자동 조립 v4 (품질 개선판)
# 실행: python D:\WISSLIST\scripts\assemble_video.py
#
# 개선 사항:
#  - 이미지/GIF/영상 모두 정확한 segment 길이로 맞춤
#  - GIF 우선 매칭
#  - 자막 타이밍 오디오 길이 기준으로 정확히 맞춤
#  - 고화질 출력 (1080x1920, 30fps, 높은 비트레이트)
#  - moviepy v1/v2 자동 호환
# =============================================

import asyncio, json, sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import BASE_DIR
from library import load_library

BASE        = Path(BASE_DIR)
SCRIPT_PATH = BASE / "scripts_json" / "today_script.json"
AUDIO_DIR   = BASE / "audio"
OUTPUT_DIR  = BASE / "output"

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
        print("❌ moviepy 없음. pip install 'moviepy==1.0.3'")
        sys.exit(1)

TARGET_W, TARGET_H = 1080, 1920


# ══════════════════════════════════════════════════════════════════
# TTS
# ══════════════════════════════════════════════════════════════════
async def _tts_async(text: str, out_path: Path,
                     voice="ko-KR-SunHiNeural"):
    import edge_tts
    comm = edge_tts.Communicate(text=text, voice=voice, rate="+5%")
    await comm.save(str(out_path))


def make_tts(text: str, out_path: Path, voice="ko-KR-SunHiNeural"):
    asyncio.run(_tts_async(text, out_path, voice))
    print(f"  🎙️  {out_path.name}  ({out_path.stat().st_size//1024}KB)")


def get_audio_duration(path: Path) -> float:
    """실제 오디오 길이(초) 반환 — 자막/클립 길이의 기준"""
    clip = AudioFileClip(str(path))
    dur  = clip.duration
    clip.close()
    return dur


# ══════════════════════════════════════════════════════════════════
# 미디어 매칭 (GIF 우선)
# ══════════════════════════════════════════════════════════════════
def find_best_media(visual_tags: list,
                    exclude_files: set = None,
                    prefer_gif: bool = True) -> dict | None:
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
        is_gif = item["file"].lower().endswith(".gif")
        if is_gif:
            scored_gif.append((score, item))
        else:
            scored_other.append((score, item))

    # GIF 우선: GIF 중 가장 높은 점수 → 없으면 일반 미디어
    pool = scored_gif if (prefer_gif and scored_gif) else (scored_gif + scored_other)
    if not pool:
        pool = scored_other   # GIF 없으면 일반으로

    if not pool:
        return _fallback_pexels(visual_tags[0] if visual_tags else "food")

    max_score   = max(s for s, _ in pool)
    top_matches = [item for s, item in pool if s == max_score]
    chosen      = random.choice(top_matches)
    kind = "GIF" if chosen["file"].lower().endswith(".gif") else "IMG"
    print(f"  🎯 [{kind}] {Path(chosen['file']).name}  (점수:{max_score})")
    return chosen


def _fallback_pexels(query: str) -> dict | None:
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
# 클립 생성 (이미지 / GIF / 영상 통합)
# ══════════════════════════════════════════════════════════════════
def make_clip(media_path: str, duration: float):
    """
    파일 종류에 따라 적절한 방법으로 클립 생성,
    TARGET_W x TARGET_H(1080x1920) + 정확히 duration 길이로 맞춤
    """
    ext = Path(media_path).suffix.lower()

    if ext in (".jpg", ".jpeg", ".png", ".webp"):
        # ── 정지 이미지 ──────────────────────────────────────────
        if MOVIEPY_V == 1:
            clip = (ImageClip(media_path)
                    .set_duration(duration)
                    .resize(height=TARGET_H))
        else:
            clip = (ImageClip(media_path, duration=duration)
                    .resized(height=TARGET_H))
        # 가로 여백은 blur 배경으로 채우기
        clip = _pad_to_vertical(clip, duration)

    elif ext == ".gif":
        # ── GIF ──────────────────────────────────────────────────
        try:
            raw = VideoFileClip(media_path)
            # GIF를 duration만큼 반복
            loops = max(1, int(duration / raw.duration) + 1)
            if MOVIEPY_V == 1:
                from moviepy.video.fx.all import loop as fx_loop
                clip = fx_loop(raw, n=loops).subclip(0, duration)
                clip = clip.resize(height=TARGET_H)
            else:
                from moviepy import vfx
                clip = raw.with_effects([vfx.Loop(n=loops)]).subclipped(0, duration)
                clip = clip.resized(height=TARGET_H)
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
                clip = raw.subclip(0, use_dur).resize(height=TARGET_H)
            else:
                clip = raw.subclipped(0, use_dur).resized(height=TARGET_H)
            clip = _pad_to_vertical(clip, duration)
        except Exception as e:
            print(f"    ⚠️  영상 로드 실패({e}) → 검정 배경")
            clip = ColorClip((TARGET_W, TARGET_H), color=(0,0,0), duration=duration)

    return clip


def _pad_to_vertical(clip, duration):
    """
    가로가 TARGET_W보다 좁으면 좌우를 검정으로 채움.
    세로가 TARGET_H보다 길면 크롭.
    duration도 정확히 맞춤.
    """
    w = clip.size[0] if hasattr(clip, 'size') else TARGET_W
    h = clip.size[1] if hasattr(clip, 'size') else TARGET_H

    if w < TARGET_W:
        # 좌우 패딩
        bg = ColorClip((TARGET_W, TARGET_H), color=(0,0,0), duration=duration)
        x_off = (TARGET_W - w) // 2
        if MOVIEPY_V == 1:
            clip = clip.set_position((x_off, 0))
            clip = CompositeVideoClip([bg, clip], size=(TARGET_W, TARGET_H))
        else:
            clip = clip.with_position((x_off, 0))
            clip = CompositeVideoClip([bg, clip], size=(TARGET_W, TARGET_H))

    # duration 맞춤
    if MOVIEPY_V == 1:
        clip = clip.set_duration(duration)
    else:
        clip = clip.with_duration(duration)

    return clip


# ══════════════════════════════════════════════════════════════════
# 자막 오버레이
# ══════════════════════════════════════════════════════════════════
def add_subtitle(video_clip, text: str, duration: float):
    """
    하단 75% 위치에 자막 오버레이.
    배경 반투명 박스 포함.
    """
    if not text.strip():
        return video_clip
    try:
        if MOVIEPY_V == 1:
            txt = (TextClip(
                text,
                fontsize=58,
                color="white",
                font="NanumGothic",          # 없으면 기본 폰트
                stroke_color="black",
                stroke_width=3,
                method="caption",
                size=(TARGET_W - 80, None),
                align="center",
            )
            .set_duration(duration)
            .set_position(("center", 0.72), relative=True))
        else:
            txt = (TextClip(
                text=text,
                font_size=58,
                color="white",
                stroke_color="black",
                stroke_width=3,
                method="caption",
                size=(TARGET_W - 80, None),
                duration=duration,
            )
            .with_position(("center", 0.72), relative=True))

        return CompositeVideoClip([video_clip, txt])
    except Exception as e:
        print(f"    ⚠️  자막 실패({e}), 자막 없이 진행")
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

    # ── 1. TTS 나레이션 생성 ───────────────────────────────────────
    print("\n[1/3] 나레이션 생성 중...")
    for i, seg in enumerate(segments):
        ap = AUDIO_DIR / f"seg_{i:02d}.mp3"
        make_tts(seg["narration"], ap)
        seg["audio_path"]    = str(ap)
        seg["audio_duration"] = get_audio_duration(ap)
        print(f"       → 실제 길이: {seg['audio_duration']:.2f}초")

    # ── 2. 클립 조립 ──────────────────────────────────────────────
    print("\n[2/3] 클립 조립 중...")
    used  = set()
    clips = []

    for i, seg in enumerate(segments):
        dur   = seg["audio_duration"]   # ← 오디오 실제 길이 기준
        tags  = seg["visual_tag"]
        print(f"\n  Seg {i+1} | {seg['time']} | {dur:.2f}초")
        print(f"  태그: {tags}")

        media = find_best_media(tags, exclude_files=used, prefer_gif=True)

        if media and Path(media["file"]).exists():
            used.add(media["file"])
            video = make_clip(media["file"], dur)
        else:
            print("    ⚠️  미디어 없음 → 검정 배경")
            video = ColorClip((TARGET_W, TARGET_H),
                              color=(0,0,0), duration=dur)

        # 오디오 붙이기
        try:
            audio = AudioFileClip(seg["audio_path"])
            if MOVIEPY_V == 1:
                video = video.set_audio(audio)
            else:
                video = video.with_audio(audio)
        except Exception as e:
            print(f"    ⚠️  오디오 실패: {e}")

        # 자막 붙이기
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
        bitrate="4000k",        # 고화질
        audio_bitrate="192k",
        ffmpeg_params=["-crf", "18"],   # 품질 최우선
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
