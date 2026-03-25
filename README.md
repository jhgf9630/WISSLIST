# 🎬 WISSLIST 운영 가이드

> 유튜브 × 쿠팡파트너스 자동화 파이프라인  
> 채널: 위씨리스트 (@wisslist)

---

## 📁 파일 목록

| 파일 | 역할 |
|---|---|
| `config.py` | API 키 및 경로 설정 (최초 1회 수정) |
| `tag_map.py` | 태그 체계 + 검색어 매핑 |
| `library.py` | library.json 읽기/쓰기 공통 모듈 |
| `collectors.py` | 4개 소스 수집 엔진 |
| `collect.py` | 미디어 수집 실행 파일 |
| `import_custom.py` | 직접 찾은 이미지/GIF 등록 |
| `clip_tagger.py` | CLIP 보완 태깅 |
| `match_media.py` | 태그 기반 미디어 매칭 |
| `assemble_video.py` | 영상 조립 |
| `setup.py` | 환경 점검 |

모든 파일은 `D:\WISSLIST\scripts\` 에 저장

---

## 🚀 최초 1회 세팅

### STEP 1. 패키지 설치

```bash
pip install requests edge-tts moviepy Pillow
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install transformers
```

### STEP 2. D드라이브 폴더 생성

```bash
python D:\WISSLIST\scripts\setup.py
```

폴더 자동 생성 + 패키지 + API 연결 전항목 ✅ 확인

### STEP 3. config.py 수정

`D:\WISSLIST\scripts\config.py` 열어서 API 키 3개 입력 후 저장

```python
PEXELS_API_KEY   = "발급받은_Pexels_키"
PIXABAY_API_KEY  = "발급받은_Pixabay_키"
GIPHY_API_KEY    = "발급받은_Giphy_키"
BASE_DIR = "D:/WISSLIST"
```

---

## 📦 STEP 4. 미디어 수집

### 기본 실행 (대화형 메뉴)

```bash
python D:\WISSLIST\scripts\collect.py
```

번호를 입력하면 소스를 선택할 수 있습니다.

```
1. Pexels    (이미지+영상, 고품질, 무제한)
2. Pixabay   (이미지, 100건/일)
3. Giphy     (GIF 짤 특화, 42건/일) ⭐
4. Wikimedia (공공 이미지, 무제한)
5. 전체 소스
```

### 소스 지정 실행

```bash
# Giphy만 (GIF 짤)
python D:\WISSLIST\scripts\collect.py giphy

# Pexels만
python D:\WISSLIST\scripts\collect.py pexels

# Giphy + Pexels 동시
python D:\WISSLIST\scripts\collect.py giphy pexels

# 전체
python D:\WISSLIST\scripts\collect.py all

# 카테고리당 10개씩
python D:\WISSLIST\scripts\collect.py giphy --count 10
```

> 중복 수집 없음 — 이미 저장된 파일은 자동으로 건너뜁니다  
> 요금 없음 — 모든 소스 무료 (카드 등록 없음)

---

## 🖼️ STEP 5. 커스텀 이미지 직접 등록 (선택)

Mixkit, Coverr 등에서 직접 다운받은 이미지/GIF/영상을 등록할 때 사용합니다.

```
① 이 폴더에 파일 넣기
   D:\WISSLIST\media_library\import_here\

② 실행
   python D:\WISSLIST\scripts\import_custom.py

③ 결과
   → D:\WISSLIST\media_library\custom\ 으로 이동
   → library.json 에 자동 등록 (clip_verified=False)
```

> 추천 무료 짤 소스:
> - mixkit.co — 리액션/웃긴 클립, 상업용 무료
> - coverr.co — 밈/팝콘먹는사람 등, 상업용 무료
> - pixabay.com/videos — 리액션 영상, 무료

---

## 🤖 STEP 6. CLIP 태그 보완 (주말/여유 시)

자동 수집된 이미지 + 직접 등록한 이미지 모두에 적용됩니다.  
파일을 이동하지 않고 library.json의 태그만 보강합니다.

### 최초 실행 (모델 다운로드 약 600MB, 1회만)

```bash
python D:\WISSLIST\scripts\clip_tagger.py
```

### 처리 수 조절

```bash
# 기본 50개
python D:\WISSLIST\scripts\clip_tagger.py

# 100개
python D:\WISSLIST\scripts\clip_tagger.py 100

# 전체
python D:\WISSLIST\scripts\clip_tagger.py 9999
```

### 동작 방식

```
library.json에서 clip_verified=False 항목 필터링
    ↓
CLIP이 이미지 분석 → 태그 체계에서 가장 잘 맞는 태그 선택
    ↓
all_tags에 새 태그 병합 (중복 제거)
    ↓
clip_verified=True 로 변경 (다음 실행 때 건너뜀)
    ↓
10개마다 자동 중간 저장
```

> i7-8565U 기준: 이미지 1장당 약 2~4초, 50장 = 약 2~3분

---

## ✍️ STEP 7. 스크립트 생성

### 7-1. today_prompt.txt 작성

`D:\WISSLIST\today_prompt.txt` 열어서 아래 형식으로 입력 후 저장

```
제품명: (예: 에어프라이어)
카테고리: (예: 주방가전)
타겟 시청자: (예: 자취생, 요리 초보)
핵심 공감 포인트: (예: 기름 없이 바삭하게 먹고 싶다)
훅 유형: 공감  ← 아래 4가지 중 1개
영상 길이: 20초  ← 15초 / 20초 / 25초 중 1개
```

훅 유형 선택:
- `공감` — "자취생들 다 이럴 거야" 식 공감 유도
- `궁금증` — "이걸 모르면 손해" 식 호기심 유발
- `반전` — "살 것 같았는데 안 샀던 이유" 식 반전
- `정보` — "이 제품의 숨겨진 기능" 식 유용한 정보

### 7-2. Claude.ai에서 스크립트 생성

1. **Claude.ai 새 대화창** 열기
2. 아래 **[SYSTEM PROMPT]** 전체 복사 → 첫 메시지로 전송
3. 이어서 `today_prompt.txt` 내용 붙여넣기
4. 출력된 JSON 전체 복사

---

## 📋 스크립트 자동 생성 SYSTEM PROMPT

Claude.ai에 아래 내용을 그대로 붙여넣으세요.

```
당신은 한국 유튜브 쇼츠 스크립트 전문 작가입니다.
채널 콘셉트: 음식/맛집/편의점/배달 위주의 공감 콘텐츠.
아래 규칙을 철저히 따라 스크립트를 작성하세요.

[핵심 철학]
- 이 영상은 광고처럼 보여서는 절대 안 됩니다.
- 시청자는 "재미있거나 공감되는 콘텐츠"를 보고 있다고 느껴야 합니다.
- 제품은 이야기의 "자연스러운 해결책"으로 등장해야 합니다.
- 구매 유도 문구("지금 구매", "할인", "링크" 등)는 영상 스크립트에 절대 포함하지 않습니다.

[3막 구조 — 반드시 준수]
1막 훅 (처음 1~2 segments): 제품명 없이 감정/상황/궁금증으로 시작. 시청자가 멈추게 만드는 것이 목적.
2막 몸통 (중간 segments): 공감대 형성 → 정보/이야기 전개 → 제품이 해결책으로 자연 등장.
3막 클로징 (마지막 1 segment): 짧고 감정이 담긴 한 마디로 마무리. CTA 없음.

[금지 사항]
- 영상 안에서 가격, 링크, 쿠팡, 할인, 구매 유도 문구 언급 금지
- 제품 사진을 첫 장면에 크게 노출하는 구성 금지
- "오늘 소개할 제품은~" 같은 광고 오프닝 금지
- 영상 길이 25초 초과 금지

[segment 설계 규칙 — 매우 중요]
- 각 segment는 정확히 1~2초 분량의 나레이션으로 구성합니다.
- narration은 한 문장 또는 짧은 두 문장 이내로 작성합니다.
  · 15초 영상 → segment 9~12개 (1~1.5초씩)
  · 20초 영상 → segment 12~16개 (1~1.5초씩)
  · 25초 영상 → segment 16~20개 (1~1.5초씩)
- on_screen_text는 narration의 핵심 키워드 1~3단어, 절대 10자 이내.
- 화면은 segment마다 전환 → 1초 단위 빠른 컷 편집 효과 자동 구현.

[visual_tag 선택 전략]
- 감정/리액션 장면은 반드시 아래 GIF 친화 태그를 포함:
  인물리액션, 인물감정, 유머러스한, 황당한, 공감가는, 만족스러운, 놀란표정, 만족표정
- 음식 장면은 아래 태그 위주로:
  음식클로즈업, 음식풍부한색감, 음식완성샷, 라면조리, 주방조리, 혼자식사
- 훅(0~3초) 배경은: 훅배경, 인물리액션, 텍스트배경 중 선택
- 클로징은: 클로징, 만족표정, 해결완료 중 선택

[태그 체계 — visual_tag에 반드시 아래 목록 중에서만 선택, 1개 segment당 2~3개]

scene_type (장면 유형):
실내생활, 주방조리, 거실풍경, 침실인테리어, 욕실뷰티, 홈오피스, 카페분위기,
음식클로즈업, 음식준비중, 음식완성샷, 디저트, 배달음식, 편의점음식, 라면조리,
제품단독, 제품언박싱, 제품사용중, 제품비교, 가전제품, 소형가전, 뷰티제품, 식품패키지,
인물감정, 인물리액션, 인물일상, 혼자식사, 혼자쇼핑,
야외활동, 마트쇼핑, 온라인쇼핑화면, 택배도착,
텍스트배경, 숫자가격표, 비교대조, 비포애프터, 영수증클로즈업, 쿠팡앱화면

mood (분위기):
따뜻한, 신나는, 설레는, 만족스러운, 뿌듯한,
공감가는, 현실적인, 피곤한, 귀찮은, 허탈한,
유머러스한, 황당한, 어이없는, 웃긴,
신뢰감있는, 전문적인, 깔끔한, 세련된, 아늑한, 역동적인

color_tone (색감):
화이트톤, 따뜻한계열, 차가운계열, 어두운계열,
자연초록, 음식풍부한색감, 파스텔톤, 비비드컬러, 모노크롬, 골드브라운

usability (영상 내 용도):
훅배경, 제품등장, 감정표현, 조리과정, 비포애프터,
가격강조, 클로징, 자막배경, 언박싱, 사용후기, 불편함표현, 해결완료

subject (구체적 피사체):
라면, 치킨, 피자, 햄버거, 삼겹살, 떡볶이, 냉동식품, 간편식, 컵라면, 캔음식,
에어프라이어, 전자레인지, 믹서기, 커피머신, 청소기, 가습기, 선풍기, 히터,
스킨케어, 마스크팩, 샴푸, 세제, 방향제,
택배박스, 쿠팡박스, 장바구니, 할인쿠폰,
놀란표정, 만족표정, 실망표정, 기쁜표정, 팝콘먹는사람,
깔끔한흰배경, 원목테이블, 대리석배경

[출력 형식 — JSON만 출력, 다른 텍스트 없음]
{
  "title": "유튜브 영상 제목 (클릭 유도, 30자 이내)",
  "hook_type": "사용한 훅 유형 (공감/궁금증/반전/정보 중 하나)",
  "segments": [
    {
      "time": "00~01s",
      "narration": "1~2초 분량의 짧은 나레이션",
      "on_screen_text": "핵심 키워드만 (10자 이내)",
      "visual_tag": ["태그1", "태그2", "태그3"],
      "sfx": "효과음 유형 (whoosh/ding/boing/없음 중 하나)"
    }
  ],
  "closing_line": "마지막 한 마디 (10자 이내)",
  "description_cta": "영상 설명란 안내 문구",
  "disclaimer": "이 영상은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
}
```


## 🎬 STEP 8. 영상 조립

```bash
python D:\WISSLIST\scripts\assemble_video.py
```

자동 처리 순서:
```
[1/3] 나레이션 생성 (edge-tts, 무료)
[2/3] 미디어 매칭 + 클립 조립
[3/3] 최종 MP4 저장
```

완성 영상 위치: `D:\WISSLIST\output\영상제목.mp4`  
소요 시간: 약 3~5분

---

## 📤 STEP 9. 유튜브 업로드

1. 완성된 MP4 파일 확인: `D:\WISSLIST\output\`
2. 유튜브 스튜디오 → **만들기** → **동영상 업로드**
3. 제목: `today_script.json`의 `title` 값
4. 설명란 입력:

```
📦 영상 속 제품 👇
[쿠팡파트너스 링크 붙여넣기]

이 영상은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.
```

5. 해시태그 추가 (예: #가성비 #추천템 #쿠팡추천)
6. **공개** 설정 후 업로드

---

## 📅 일상 운영 루틴

### 매일 (약 10분)

```bash
# 1. 미디어 수집 (2~3분)
python D:\WISSLIST\scripts\collect.py giphy pexels

# 2. 직접 찾은 짤 있으면 (선택, 1분)
#    import_here 폴더에 파일 넣기 후:
python D:\WISSLIST\scripts\import_custom.py

# 3. 스크립트 생성 (1분)
#    today_prompt.txt 작성 → Claude.ai 붙여넣기 → JSON 저장

# 4. 영상 조립 (3~5분)
python D:\WISSLIST\scripts\assemble_video.py
```

### 주말 (약 5분, 노트북 충전 중)

```bash
# CLIP 태그 보완
python D:\WISSLIST\scripts\clip_tagger.py 100
```

---

## 🏷️ 태그 추가 방법

`tag_map.py`의 `QUERY_TAG_MAP` 딕셔너리에 한 줄 추가

```python
# 예시: 새 검색어 추가
"air fryer recipe": ["에어프라이어", "조리과정", "소형가전", "해결완료"],
```

`CATEGORY_QUERIES`에도 해당 카테고리에 검색어 추가:

```python
"kitchen": [...기존..., "air fryer recipe"],
```

---

## 🆓 무료 짤 소스 (직접 다운로드 후 import_custom.py 사용)

| 사이트 | URL | 특징 |
|---|---|---|
| Mixkit | mixkit.co | 리액션/웃긴 클립, 상업용 무료, 워터마크 없음 |
| Coverr | coverr.co/stock-video-footage/meme | 밈/팝콘 클립, 상업용 무료 |
| Pixabay 영상 | pixabay.com/videos | 리액션 영상 1,800개+, 무료 |
| Giphy | giphy.com | GIF 짤 (API로 자동 수집 가능) |

---

## ❓ 자주 묻는 것

**Q. 중복 수집 되나요?**  
A. library.json에서 이미 저장된 파일을 확인해서 중복이면 자동으로 건너뜁니다.

**Q. 요금이 청구될 수 있나요?**  
A. 모든 소스(Pexels, Pixabay, Giphy, Wikimedia)는 카드 등록 없이 무료 이메일 가입만 하는 구조라 청구 자체가 불가능합니다.

**Q. CLIP은 파일을 폴더로 분류하나요?**  
A. 아닙니다. 파일은 원래 위치에 그대로 두고, library.json의 all_tags에만 태그를 추가합니다.

**Q. today_script.json을 저장하고 나서 바로 영상을 못 만들어도 괜찮나요?**  
A. 네, 파일이 있는 동안 언제든 assemble_video.py를 실행할 수 있습니다.

**Q. 영상 조립 중 "검정 배경"이 나오면?**  
A. 해당 태그와 매칭되는 미디어가 라이브러리에 없는 것입니다. collect.py를 더 실행해서 라이브러리를 쌓거나, import_custom.py로 관련 이미지를 직접 추가하세요.

---

## 📊 전체 비용

| 항목 | 비용 |
|---|---|
| 미디어 수집 (Pexels/Pixabay/Giphy/Wikimedia) | $0 |
| TTS 나레이션 (edge-tts) | $0 |
| 영상 조립 (MoviePy) | $0 |
| CLIP 태깅 (로컬 실행) | $0 |
| 스크립트 생성 (Claude Pro 웹) | $0 추가 |
| 유튜브 업로드 API | $0 |
| **총합** | **$0** |

---

## 🗑️ 사진 삭제 후 JSON 정리

탐색기에서 이미지 파일을 직접 삭제하면 `library.json`에는 경로가 그대로 남습니다.
아래 명령어로 정리하세요.

```bash
# 삭제 대상 미리 보기 (실제 삭제 X)
python D:\WISSLIST\scripts\cleanup_library.py --scan

# 실제 정리 실행 (y 입력 시 JSON에서만 제거)
python D:\WISSLIST\scripts\cleanup_library.py

# 통계만 확인
python D:\WISSLIST\scripts\cleanup_library.py --stats
```

실행하면 파일이 없는 항목 목록을 보여주고, `y` 입력 시 `library.json`에서만 제거합니다.  
실제 파일은 건드리지 않습니다.

---

## ⚠️ moviepy 오류 해결 — `No module named 'moviepy.editor'`

moviepy v2에서 `editor` 서브모듈이 제거되어 발생하는 오류입니다.

### 해결법 1 — 구버전으로 재설치 (권장)

```bash
pip uninstall moviepy -y
pip install "moviepy==1.0.3"
```

### 해결법 2 — 최신 버전 재설치

```bash
pip uninstall moviepy -y
pip install moviepy
```

> `assemble_video.py`는 v1/v2를 자동 감지하도록 수정되어 있습니다.  
> 재설치 후 바로 실행 가능합니다.


---

## 🎯 영상 퀄리티 향상 체크리스트

### 미디어 라이브러리 강화
- **음식 이미지 퀄리티:** Pexels에서 `food close up`, `melting cheese`, `steam hot food` 등 구체적인 쿼리로 수집
- **GIF 최대 활용:** `collect.py giphy --count 10` 으로 GIF를 충분히 수집해두면 영상이 훨씬 생동감 있어짐
- **직접 수집 추천:** Mixkit(`mixkit.co/free-stock-video/food`)에서 음식 영상 클립 직접 다운로드 후 `import_custom.py` 등록

### 스크립트 퀄리티
- segment당 나레이션을 **1~1.5초 분량**(10~15자 이내)으로 짧게 유지
- 감정/리액션 장면에는 `인물리액션`, `유머러스한` 태그를 반드시 포함 → GIF 자동 매칭
- 음식 클로즈업 장면에는 `음식풍부한색감`, `음식클로즈업` 태그 사용

### TTS 음성 선택
```bash
# 기본 (밝고 친근한 여성)
voice = "ko-KR-SunHiNeural"

# 차분한 남성
voice = "ko-KR-InJoonNeural"

# 젊고 활기찬 남성
voice = "ko-KR-HyunsuNeural"
```
assemble_video.py의 `make_tts()` 함수에서 voice 파라미터 변경

### moviepy 재설치 (오류 시)
```bash
pip uninstall moviepy -y
pip install "moviepy==1.0.3"
```

### 전체 비용
| 항목 | 비용 |
|---|---|
| 미디어 수집 전체 | $0 |
| TTS (edge-tts, Microsoft) | $0 |
| 영상 조립 (MoviePy) | $0 |
| CLIP 태깅 (로컬) | $0 |
| 스크립트 생성 (Claude Pro 웹) | $0 추가 |
| **총합** | **$0** |
