# =============================================
# WISSLIST - 스크립트 자동 생성
# 실행: python D:\WISSLIST\scripts\generate_script.py
#       python D:\WISSLIST\scripts\generate_script.py 안성탕면
#
# 동작:
#   1. 제품명만 입력하면 Anthropic API로
#      카테고리/타겟/공감포인트/훅 자동 생성
#   2. today_script.json 바로 저장
#   3. Claude Pro 웹 없이 완전 자동화
#
# 설치: pip install anthropic
# =============================================

import sys
import json
import requests
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import BASE_DIR, ANTHROPIC_API_KEY  # config.py에 키 추가 필요

BASE        = Path(BASE_DIR)
SCRIPT_DIR  = BASE / "scripts_json"

# ── 태그 체계 (스크립트 AI에게 전달) ─────────────────────────────
TAG_SYSTEM = """
scene_type: 실내생활,주방조리,거실풍경,침실인테리어,욕실뷰티,홈오피스,카페분위기,음식클로즈업,음식준비중,음식완성샷,디저트,배달음식,편의점음식,라면조리,제품단독,제품언박싱,제품사용중,제품비교,가전제품,소형가전,뷰티제품,식품패키지,인물감정,인물리액션,인물일상,혼자식사,혼자쇼핑,야외활동,마트쇼핑,온라인쇼핑화면,택배도착,텍스트배경,숫자가격표,비교대조,비포애프터,영수증클로즈업,쿠팡앱화면

mood: 따뜻한,신나는,설레는,만족스러운,뿌듯한,공감가는,현실적인,피곤한,귀찮은,허탈한,유머러스한,황당한,어이없는,웃긴,신뢰감있는,전문적인,깔끔한,세련된,아늑한,역동적인

color_tone: 화이트톤,따뜻한계열,차가운계열,어두운계열,자연초록,음식풍부한색감,파스텔톤,비비드컬러,모노크롬,골드브라운

usability: 훅배경,제품등장,감정표현,조리과정,비포애프터,가격강조,클로징,자막배경,언박싱,사용후기,불편함표현,해결완료

subject: 라면,치킨,피자,햄버거,삼겹살,떡볶이,냉동식품,간편식,컵라면,캔음식,에어프라이어,전자레인지,믹서기,커피머신,청소기,가습기,선풍기,히터,스킨케어,마스크팩,샴푸,세제,방향제,택배박스,쿠팡박스,장바구니,할인쿠폰,놀란표정,만족표정,실망표정,기쁜표정,팝콘먹는사람,깔끔한흰배경,원목테이블,대리석배경
"""

# ── 시스템 프롬프트 ───────────────────────────────────────────────
SYSTEM_PROMPT = f"""당신은 한국 유튜브 쇼츠 스크립트 전문 작가입니다.
채널 콘셉트: 음식/맛집/편의점/배달 위주의 공감 콘텐츠.

사용자가 제품명 하나만 알려주면, 당신이 직접:
1. 제품을 분석해서 타겟 시청자, 핵심 공감 포인트, 최적 훅 유형 결정
2. 완성된 스크립트 JSON 생성

[핵심 철학]
- 광고처럼 보이면 절대 안 됩니다
- 시청자는 "재미있거나 공감되는 콘텐츠"를 보고 있다고 느껴야 합니다
- 제품은 이야기의 자연스러운 해결책으로 등장해야 합니다
- 구매 유도 문구는 영상에 절대 없어야 합니다
- **대본은 친근하고 편안한 말투로 작성합니다. 마치 친한 친구가 말하듯이.**

[대본 말투 규칙 — 매우 중요]
- 존댓말 X → 반말 또는 구어체 사용
- "~습니다" X → "~야", "~이야", "~거든", "~잖아" 등 사용
- 문어체 X → 카카오톡에서 친구한테 보내는 느낌
- 예시 좋음: "진짜 이거 없으면 못 살아", "솔직히 나만 이런 거 아니지?"
- 예시 나쁨: "본 제품은 뛰어난 품질을 자랑합니다"

[3막 구조]
1막 훅 (처음 2~3 segments): 제품명 없이 감정/상황/궁금증으로 시작
2막 몸통 (중간 segments): 공감대 → 이야기 → 제품이 해결책으로 자연 등장
3막 클로징 (마지막 1 segment): 짧고 감정 담긴 한 마디

[segment 설계 — 중요]
- 각 segment: 1~2초 분량 나레이션 (10~20자 이내)
- 20초 영상 → 12~16개 segment
- 화면은 segment마다 전환 → 1초 단위 빠른 컷

[visual_tag 전략]
- 감정/리액션 장면: 인물리액션, 인물감정, 유머러스한, 황당한, 공감가는 포함 (GIF 매칭)
- 음식 장면: 음식클로즈업, 음식풍부한색감, 음식완성샷, 라면조리 위주

[태그 체계 — visual_tag에 아래 목록에서만 선택, 1 segment당 2~3개]
{TAG_SYSTEM}

[출력 형식 — JSON만 출력, 다른 텍스트 없음]
{{
  "title": "유튜브 영상 제목 (클릭 유도, 30자 이내)",
  "hook_type": "공감/궁금증/반전/정보 중 하나",
  "segments": [
    {{
      "time": "00~01s",
      "narration": "1~2초 분량의 짧고 친근한 나레이션",
      "on_screen_text": "핵심 키워드 (10자 이내)",
      "visual_tag": ["태그1", "태그2", "태그3"],
      "sfx": "whoosh/ding/boing/없음 중 하나"
    }}
  ],
  "closing_line": "마지막 한 마디 (10자 이내)",
  "description_cta": "영상 설명란 안내 문구",
  "disclaimer": "이 영상은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
}}"""


def call_anthropic(product_name: str) -> dict:
    """Anthropic API 호출"""
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": (
                    f"제품명: {product_name}\n\n"
                    f"위 제품의 특징을 파악하고 효과적인 유튜브 쇼츠 스크립트를 작성해줘.\n"
                    f"카테고리, 타겟 시청자, 핵심 공감 포인트, 훅 유형은 직접 판단해서 결정해.\n"
                    f"영상 길이: 20초 (12~16 segments)\n"
                    f"JSON만 출력해."
                ),
            }
        ],
    }

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=body,
        timeout=60,
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"API 오류 {resp.status_code}: {resp.text[:300]}"
        )

    content = resp.json()["content"][0]["text"].strip()

    # JSON 파싱 (```json ... ``` 블록 처리)
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```",
                           content, re.DOTALL)
    if json_match:
        content = json_match.group(1)
    elif content.startswith("{"):
        pass
    else:
        # 첫 { 부터 마지막 } 까지 추출
        start = content.find("{")
        end   = content.rfind("}") + 1
        if start != -1 and end > start:
            content = content[start:end]

    return json.loads(content)


def generate(product_name: str, output_path: Path = None) -> dict:
    if output_path is None:
        output_path = SCRIPT_DIR / "today_script.json"

    SCRIPT_DIR.mkdir(exist_ok=True)

    print(f"\n🎬 WISSLIST 스크립트 자동 생성")
    print(f"   제품명: {product_name}")
    print(f"   AI가 카테고리/타겟/공감포인트/훅 자동 결정 중...")

    script = call_anthropic(product_name)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    seg_count = len(script.get("segments", []))
    print(f"\n✅ 스크립트 생성 완료!")
    print(f"   제목: {script.get('title','')}")
    print(f"   훅 유형: {script.get('hook_type','')}")
    print(f"   segment 수: {seg_count}개")
    print(f"   저장 위치: {output_path}")
    print(f"\n다음 단계:")
    print(f"   python D:\\WISSLIST\\scripts\\assemble_video.py")

    return script


if __name__ == "__main__":
    if not BASE.exists():
        print("❌ D드라이브(USB) 연결 확인")
        sys.exit(1)

    # 커맨드라인 인자 또는 대화형 입력
    if len(sys.argv) > 1:
        product = " ".join(sys.argv[1:])
    else:
        print("\n🛒 WISSLIST 스크립트 자동 생성기")
        print("제품명만 입력하면 스크립트를 자동으로 만들어드립니다.")
        product = input("\n제품명 입력 (예: 안성탕면, 에어프라이어): ").strip()
        if not product:
            print("제품명을 입력해주세요.")
            sys.exit(1)

    generate(product)
