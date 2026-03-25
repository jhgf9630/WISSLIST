# =============================================
# WISSLIST - 영상 자동 조립
# 실행: python assemble_video.py
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


async def _tts(text: str, out_path: Path, voice="ko-KR-SunHiNeural"):
    import edge_tts
    await edge_tts.Communicate(text=text, voice=voice).save(str(out_path))
    print(f"  🎙️  {out_path.name}")


def _parse_sec(time_str: str) -> int:
    parts = time_str.replace("s", "").split("~")
    return int(parts[1]) - int(parts[0])


def assemble(script_path=None):
    from moviepy.editor import (
        VideoFileClip, AudioFileClip, TextClip,
        CompositeVideoClip, concatenate_videoclips, ColorClip,
        ImageClip,
    )
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

    # 1. TTS
    print("\n[1/3] 나레이션 생성...")
    for i, seg in enumerate(script["segments"]):
        ap = AUDIO_DIR / f"seg_{i:02d}.mp3"
        asyncio.run(_tts(seg["narration"], ap))
        seg["audio_file"] = str(ap)

    # 2. 클립 조립
    print("\n[2/3] 클립 조립...")
    used, clips = set(), []

    for i, seg in enumerate(script["segments"]):
        dur    = _parse_sec(seg["time"])
        media  = find_best_media(seg["visual_tag"], exclude_files=used)
        print(f"  Seg {i+1} ({seg['time']})")

        # 미디어 로드
        if media and Path(media["file"]).exists():
            used.add(media["file"])
            mfile = media["file"]
            try:
                if mfile.endswith(".gif"):
                    from moviepy.video.io.VideoFileClip import VideoFileClip as VFC
                    raw = VFC(mfile)
                else:
                    raw = VideoFileClip(mfile)
                clip_dur = min(dur, raw.duration)
                video = raw.subclip(0, clip_dur).resize((1080, 1920))
            except Exception as e:
                print(f"    ⚠️  로드 실패({e}) → 검정 배경")
                video = ColorClip((1080, 1920), color=(0, 0, 0), duration=dur)
        else:
            print("    ⚠️  미디어 없음 → 검정 배경")
            video = ColorClip((1080, 1920), color=(0, 0, 0), duration=dur)

        # 오디오
        try:
            audio = AudioFileClip(seg["audio_file"])
            video = video.set_audio(audio)
        except Exception as e:
            print(f"    ⚠️  오디오 실패: {e}")

        # 자막
        try:
            txt = (TextClip(
                seg["on_screen_text"], fontsize=52, color="white",
                stroke_color="black", stroke_width=2.5,
                method="caption", size=(960, None),
            )
            .set_duration(video.duration)
            .set_position(("center", 0.75), relative=True))
            video = CompositeVideoClip([video, txt])
        except Exception as e:
            print(f"    ⚠️  자막 실패: {e}")

        clips.append(video)

    # 3. 최종 저장
    print("\n[3/3] 영상 합치는 중...")
    final = concatenate_videoclips(clips, method="compose")
    safe  = "".join(c for c in script["title"][:20]
                    if c.isalnum() or c in " _-").strip()
    out   = OUTPUT_DIR / f"{safe}.mp4"
    final.write_videofile(str(out), fps=30, codec="libx264",
                          audio_codec="aac", logger=None)

    print(f"\n✅ 완성: {out}")
    print(f"\n📋 설명란 복사:\n{script.get('description_cta','')}")
    print(f"\n⚠️  {script.get('disclaimer','')}")
    return str(out)


if __name__ == "__main__":
    assemble()
