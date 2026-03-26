# =============================================
# WISSLIST - 스크립트 자동 생성
# 실행: python D:\WISSLIST\scripts\generate_script.py
#       python D:\WISSLIST\scripts\generate_script.py 안성탕면
# =============================================

import sys
import json
import requests
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import BASE_DIR, ANTHROPIC_API_KEY

BASE        = Path(BASE_DIR)
SCRIPT_DIR  = BASE / "scripts_json"

TAG_SYSTEM = """
scene_type: 실내생활,주방조리,거실풍경,침실인테리어,욕실뷰티,홈오피스,카페분위기,음식클로즈업,음식준비중,음식완성샷,디저트,배달음식,편의점음식,라면조리,제품단독,제품언박싱,제품사용중,제품비교,가전제품,소형가전,뷰티제품,식품패키지,인물감정,인물리액션,인물일상,혼자식사,혼자쇼핑,야외활동,마트쇼핑,온라인쇼핑화면,택배도착,텍스트배경,숫자가격표,비교대조,비포애프터,영수증클로즈업,쿠팡앱화면

mood: 따뜻한,신나는,설레는,만족스러운,뿌듯한,공감가는,현실적인,피곤한,귀찮은,허탈한,유머러스한,황당한,어이없는,웃긴,신뢰감있는,전문적인,깔끔한,세련된,아늑한,역동적인

color_tone: 화이트톤,따뜻한계열,차가운계열,어두운계열,자연초록,음식풍부한색감,파스텔톤,비비드컬러,모노크롬,골드브라운

usability: 훅배경,제품등장,감정표현,조리과정,비포애프터,가격강조,클로징,자막배경,언박싱,사용후기,불편함표현,해결완료

subject: 라면,치킨,피자,햄버거,삼겹살,떡볶이,냉동식품,간편식,컵라면,캔음식,에어프라이어,전자레인지,믹서기,커피머신,청소기,가습기,선풍기,히터,스킨케어,마스크팩,샴푸,세제,방향제,택배박스,쿠팡박스,장바구니,할인쿠폰,놀란표정,만족표정,실망표정,기쁜표정,팝콘먹는사람,깔끔한흰배경,원목테이블,대리석배경,제품이미지
"""

SYSTEM_PROMPT = f"""당신은 한국 유튜브 쇼츠 스크립트 전문 작가입니다.
채널 콘셉트: 음식/맛집/편의점/배달/생활용품 위주의 공감 콘텐츠. 쿠팡파트너스 연계.

제품명 하나만 받으면, 당신이 직접:
1. 제품의 특징·소비자 심리·유행 트렌드를 분석
2. 가장 효과적인 훅 유형과 공감 포인트 결정
3. 완성된 쇼츠 스크립트 JSON 생성

━━━━━━━━━━━━━━━━━━━━━━━━━━
[핵심 철학]
━━━━━━━━━━━━━━━━━━━━━━━━━━
- 광고처럼 보이면 절대 안 됩니다. 시청자는 재미있거나 공감되는 콘텐츠를 보는 느낌이어야 합니다.
- 제품은 이야기의 "자연스러운 해결책"으로 등장해야 합니다.
- 가격, 링크, 쿠팡, 할인, 구매 유도 문구는 영상 안에 절대 언급 금지.
- "오늘 소개할 제품은~" 같은 광고 오프닝 절대 금지.

━━━━━━━━━━━━━━━━━━━━━━━━━━
[말투 규칙 — 가장 중요, 반드시 지킬 것]
━━━━━━━━━━━━━━━━━━━━━━━━━━
- 친한 친구한테 카카오톡 보내는 말투로 작성하세요.
- 반말 또는 구어체 사용: "~야", "~이야", "~거든", "~잖아", "~했어", "~인 거 알지?", "솔직히", "진짜로"
- "~습니다", "~입니다", "~하세요" 절대 금지
- 자연스러운 감탄사 사용 가능: "야 진짜", "어 이거", "아 맞다", "근데", "그니까"
- 시청자를 "너"처럼 대화하는 느낌: "너도 이런 적 있지?", "나만 이런 거 아니지?"

좋은 예시:
  ✅ "운동 끝나고 뭔가 먹고 싶은데 귀찮아 죽겠잖아"
  ✅ "진짜 이거 없으면 못 살아 요즘"
  ✅ "어 근데 이게 생각보다 너무 맛있는 거야"
  ✅ "솔직히 나만 이런 거 아니지?"

나쁜 예시:
  ❌ "본 제품은 뛰어난 품질을 자랑합니다"
  ❌ "많은 분들이 추천하는 제품입니다"
  ❌ "오늘 소개해드릴 제품은~"

━━━━━━━━━━━━━━━━━━━━━━━━━━
[3막 구조 — 반드시 준수]
━━━━━━━━━━━━━━━━━━━━━━━━━━
1막 훅 (처음 2~3 segments):
  - 제품명 절대 언급 금지
  - 감정/상황/궁금증으로 시작 → 시청자가 "어? 나도"하고 멈추게 만들기
  - 훅 유형별 예시:
    · 공감형: "운동 끝나고 진짜 배고픈데 배달 시키기엔 귀찮고"
    · 궁금증형: "편의점에서 이거 한 번도 안 먹어봤으면 진짜 손해야"
    · 반전형: "맛있어서 자주 사다 먹던 거 끊었어. 이유가 있거든"
    · 정보형: "이 조합으로 먹으면 진짜 레스토랑 수준임"

2막 몸통 (중간 segments):
  - 공감대 형성 → 상황 전개 → 제품이 자연스럽게 해결책으로 등장
  - 제품 이름은 2막 중반 이후에 처음 등장하는 게 이상적

3막 클로징 (마지막 1~2 segments):
  - 짧고 임팩트 있는 한 마디로 마무리
  - 구매 유도 없이 감정적 공감으로 끝내기

━━━━━━━━━━━━━━━━━━━━━━━━━━
[segment 설계 규칙]
━━━━━━━━━━━━━━━━━━━━━━━━━━
- 각 segment = 1~2초 분량 (나레이션 10~20자 이내, 짧고 리듬감 있게)
- 15초 영상 → 9~12개 / 20초 → 12~16개 / 25초 → 16~20개
- 문장을 쪼개서 리듬감 있게: "진짜 / 이거 없으면 / 못 살 것 같아"처럼 분리
- on_screen_text: narration의 핵심 단어 1~3개, 10자 이내

━━━━━━━━━━━━━━━━━━━━━━━━━━
[visual_tag 선택 전략]
━━━━━━━━━━━━━━━━━━━━━━━━━━
- 제품 이미지가 라이브러리에 있을 수 있음 → 제품 등장 장면에는 반드시 아래 태그 중 하나 포함:
  · "제품이미지" (직접 수집한 제품 이미지 매칭용 — 가장 높은 우선순위)
  · "제품단독", "제품사용중", "제품등장", "식품패키지"
- 감정/리액션 장면: 인물리액션, 인물감정, 유머러스한, 황당한, 공감가는 포함 (GIF 매칭)
- 음식 장면: 음식클로즈업, 음식풍부한색감, 음식완성샷, 라면조리 위주
- 훅 장면: 훅배경, 인물리액션, 텍스트배경 중 선택
- 클로징: 클로징, 만족표정, 해결완료 중 선택

━━━━━━━━━━━━━━━━━━━━━━━━━━
[태그 체계 — visual_tag는 반드시 아래 목록에서만 선택, 1 segment당 2~3개]
━━━━━━━━━━━━━━━━━━━━━━━━━━
{TAG_SYSTEM}

━━━━━━━━━━━━━━━━━━━━━━━━━━
[출력 형식 — JSON만 출력, 다른 텍스트 없음]
━━━━━━━━━━━━━━━━━━━━━━━━━━
{{
  "title": "유튜브 영상 제목 (클릭 유도, 30자 이내, 궁금증/공감 유발)",
  "hook_type": "공감/궁금증/반전/정보 중 하나",
  "product_name": "제품명",
  "segments": [
    {{
      "time": "00~01s",
      "narration": "짧고 친근한 구어체 나레이션 (10~20자)",
      "on_screen_text": "핵심 키워드 (10자 이내)",
      "visual_tag": ["태그1", "태그2", "태그3"],
      "sfx": "whoosh/ding/boing/없음 중 하나"
    }}
  ],
  "closing_line": "마지막 한 마디 (10자 이내, 감정 담긴)",
  "description_cta": "영상 설명란 안내 문구 (링크는 설명란에서 처리)",
  "disclaimer": "이 영상은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
}}"""


def call_anthropic(product_name: str) -> dict:
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
                    f"이 제품의 특징을 분석하고 가장 효과적인 쇼츠 스크립트를 만들어줘.\n"
                    f"카테고리, 타겟, 공감포인트, 훅 유형 모두 네가 직접 판단해서 결정해.\n"
                    f"영상 길이: 20초 (12~16 segments)\n"
                    f"JSON만 출력해."
                ),
            }
        ],
    }

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers, json=body, timeout=60)

    if resp.status_code != 200:
        raise RuntimeError(f"API 오류 {resp.status_code}: {resp.text[:300]}")

    content = resp.json()["content"][0]["text"].strip()
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if json_match:
        content = json_match.group(1)
    elif not content.startswith("{"):
        start, end = content.find("{"), content.rfind("}") + 1
        if start != -1 and end > start:
            content = content[start:end]

    return json.loads(content)


def generate(product_name: str, output_path: Path = None) -> dict:
    if output_path is None:
        output_path = SCRIPT_DIR / "today_script.json"
    SCRIPT_DIR.mkdir(exist_ok=True)

    print(f"\n🎬 WISSLIST 스크립트 자동 생성")
    print(f"   제품명: {product_name}")
    print(f"   AI 분석 중...")

    script = call_anthropic(product_name)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 생성 완료!")
    print(f"   제목: {script.get('title','')}")
    print(f"   훅 유형: {script.get('hook_type','')}")
    print(f"   segments: {len(script.get('segments',[]))}개")
    print(f"   저장: {output_path}")
    print(f"\n다음 단계: python D:\\WISSLIST\\scripts\\assemble_video.py")
    return script


if __name__ == "__main__":
    if not BASE.exists():
        print("❌ D드라이브(USB) 연결 확인")
        sys.exit(1)

    if len(sys.argv) > 1:
        product = " ".join(sys.argv[1:])
    else:
        print("\n🛒 WISSLIST 스크립트 자동 생성기")
        product = input("\n제품명 입력 (예: 안성탕면): ").strip()
        if not product:
            sys.exit(1)

    generate(product)
