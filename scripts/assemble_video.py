# =============================================
# WISSLIST - 영상 자동 조립 (moviepy v1/v2 호환)
# 실행: python D:\WISSLIST\scripts\assemble_video.py
# =============================================

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import BASE_DIR
from match_media import find_best_media

BASE        = Path(BASE_DIR)
SCRIPT_PATH = BASE / "scripts_json" / "today_script.json"
AUDIO_DIR   = BASE / "audio"
OUTPUT_DIR  = BASE / "output"

# ── moviepy 버전 호환 임포트 ──────────────────────────────────────
try:
    # moviepy v1 (editor 서브모듈 있음)
    from moviepy.editor import (
        VideoFileClip, AudioFileClip, TextClip,
        CompositeVideoClip, concatenate_videoclips, ColorClip,
    )
    MOVIEPY_V = 1
except ModuleNotFoundError:
    try:
        # moviepy v2 (editor 서브모듈 제거됨)
        from moviepy import (
            VideoFileClip, AudioFileClip, TextClip,
            CompositeVideoClip, concatenate_videoclips, ColorClip,
        )
        MOVIEPY_V = 2
    except ImportError:
        print("❌ moviepy가 설치되어 있지 않습니다.")
        print("   pip install moviepy 실행 후 다시 시도하세요.")
        sys.exit(1)

print(f"✅ moviepy v{MOVIEPY_V} 로드됨")


async def _tts(text: str, out_path: Path, voice="ko-KR-SunHiNeural"):
    import edge_tts
    await edge_tts.Communicate(text=text, voice=voice).save(str(out_path))
    print(f"  🎙️  {out_path.name}")


def _parse_sec(time_str: str) -> int:
    """'00~03s' → 3, '03~10s' → 7"""
    parts = time_str.replace("s", "").split("~")
    return int(parts[1]) - int(parts[0])


def make_black_clip(duration):
    """검정 배경 클립 생성 (버전 호환)"""
    return ColorClip((1080, 1920), color=(0, 0, 0), duration=duration)


def add_subtitle(video, text, duration):
    """자막 오버레이 (버전 호환)"""
    try:
        if MOVIEPY_V == 1:
            txt = (TextClip(
                text, fontsize=52, color="white",
                stroke_color="black", stroke_width=2.5,
                method="caption", size=(960, None),
            )
            .set_duration(duration)
            .set_position(("center", 0.75), relative=True))
        else:
            # moviepy v2 API
            txt = (TextClip(
                text=text, font_size=52, color="white",
                stroke_color="black", stroke_width=2.5,
                method="caption", size=(960, None),
                duration=duration,
            )
            .with_position(("center", 0.75), relative=True))
        return CompositeVideoClip([video, txt])
    except Exception as e:
        print(f"    ⚠️  자막 생성 실패 (무시하고 계속): {e}")
        return video


def load_video(path, duration):
    """영상 파일 로드 (버전 호환)"""
    raw = VideoFileClip(str(path))
    clip_dur = min(duration, raw.duration)
    if MOVIEPY_V == 1:
        return raw.subclip(0, clip_dur).resize((1080, 1920))
    else:
        return raw.subclipped(0, clip_dur).resized((1080, 1920))


def set_audio(video, audio_path):
    """오디오 합치기 (버전 호환)"""
    audio = AudioFileClip(str(audio_path))
    if MOVIEPY_V == 1:
        return video.set_audio(audio)
    else:
        return video.with_audio(audio)


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
    print("=" * 50)

    # 1. TTS 나레이션 생성
    print("\n[1/3] 나레이션 생성...")
    for i, seg in enumerate(script["segments"]):
        ap = AUDIO_DIR / f"seg_{i:02d}.mp3"
        asyncio.run(_tts(seg["narration"], ap))
        seg["audio_file"] = str(ap)

    # 2. 미디어 매칭 + 클립 조립
    print("\n[2/3] 클립 조립...")
    used, clips = set(), []

    for i, seg in enumerate(script["segments"]):
        dur   = _parse_sec(seg["time"])
        media = find_best_media(seg["visual_tag"], exclude_files=used)
        print(f"  Segment {i+1} ({seg['time']})")

        # 영상/이미지 로드
        video = None
        if media and Path(media["file"]).exists():
            used.add(media["file"])
            try:
                video = load_video(media["file"], dur)
            except Exception as e:
                print(f"    ⚠️  로드 실패: {e} → 검정 배경 사용")

        if video is None:
            print("    ⚠️  미디어 없음 → 검정 배경 사용")
            video = make_black_clip(dur)

        # 오디오 합치기
        try:
            video = set_audio(video, seg["audio_file"])
        except Exception as e:
            print(f"    ⚠️  오디오 실패: {e}")

        # 자막 오버레이
        video = add_subtitle(video, seg["on_screen_text"], video.duration)

        clips.append(video)

    # 3. 최종 합치기 + 저장
    print("\n[3/3] 영상 합치는 중...")
    final = concatenate_videoclips(clips, method="compose")
    safe  = "".join(c for c in script["title"][:20]
                    if c.isalnum() or c in " _-").strip()
    out   = OUTPUT_DIR / f"{safe}.mp4"

    final.write_videofile(
        str(out), fps=30,
        codec="libx264", audio_codec="aac",
        logger=None
    )

    print(f"\n✅ 완성: {out}")
    print(f"\n📋 설명란 복사:\n{script.get('description_cta', '')}")
    print(f"\n⚠️  {script.get('disclaimer', '')}")
    return str(out)


if __name__ == "__main__":
    assemble()
