# 🎬 WISSLIST 운영 가이드
> 유튜브 쇼츠 × 쿠팡파트너스 자동화 파이프라인 | 채널: 위씨리스트 (@wisslist)

---

## ⚡ 매일 루틴 (5~10분)

### 1. 제품 이미지 등록

```
① 쿠팡에서 제품 이미지 우클릭 → 이미지 저장
② D:\WISSLIST\media_library\import_here\ 에 저장
③ 실행:
```
```bash
python D:\WISSLIST\scripts\import_custom.py --product 제품명
```

### 2. 스크립트 생성 (Claude.ai 웹)

```
① Claude.ai 새 대화창 열기 (매번 새 대화!)
② WEB_PROMPT.txt 전체 복사 → 첫 메시지로 붙여넣기
③ 다음 메시지에 입력:

   제품명: 까르보불닭볶음면
   최근 사용 훅: 공감형, 공감형   ← 다양성 위해 기록

④ 출력된 JSON 전체 복사
⑤ 메모장 → 붙여넣기 → today_script.json 으로 저장
   저장 위치: D:\WISSLIST\scripts_json\
```

> ⚠️ JSON 안에 `"product_name": "까르보불닭볶음면"` 있는지 확인. 없으면 직접 추가.

### 3. 영상 조립

```bash
python D:\WISSLIST\scripts\assemble_video.py
```

완성 영상 위치: `D:\WISSLIST\output\`

### 4. 유튜브 업로드

**유튜브 스튜디오** → 만들기 → 동영상 업로드 → MP4 파일 선택

**제목** (JSON의 title 값 복붙):
```
수영 끝나고 이거 안 먹으면 진짜 손해 🍜 #Shorts
```

**설명란** (아래 템플릿 복붙 후 링크만 교체):
```
📦 영상 속 제품 👇
[쿠팡파트너스 링크 여기에 붙여넣기]




이 영상은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.

#라면 #편의점 #가성비 #추천템 #자취생 #쿠팡추천 #Shorts
```
> ↑ 링크 아래 빈 줄 5개 = 자세히 보기 전엔 링크만 안 보이게 처리

**댓글** (아래 7개 중 하나 골라 복붙):
```
💬 여러분은 어떤 라면이 최애예요? 댓글로 알려주세요 👇
💬 이 제품 먹어본 사람? 맛 솔직하게 알려줘요 ㅋㅋ
💬 편의점에서 꼭 챙기는 템 있어요? 공유해요 👀
💬 자취하면서 없으면 안 되는 거 뭐예요?
💬 이거 아직도 안 먹어봤으면 진짜 손해인 거 맞죠? 😂
💬 요즘 가성비 최고라고 생각하는 음식/제품 댓글로!
💬 이 영상 보고 생각난 음식 있으면 댓글 달아줘요 🍽️
```

**썸네일**: Canva에서 1280×720 제작 후 업로드 (강력 권장)

**공개** 설정 후 게시

---

## 📁 파일 목록

| 파일 | 역할 |
|---|---|
| `config.py` | API 키 및 경로 설정 |
| `tag_map.py` | 태그 체계 + 검색어 매핑 |
| `library.py` | library.json 읽기/쓰기 |
| `collectors.py` | Pexels/Pixabay/Giphy/Wikimedia 수집 |
| `collect.py` | 미디어 수집 실행 |
| `collect_tenor.py` | Tenor GIF 수집 (리액션 특화) |
| `import_custom.py` | 이미지/GIF 등록 (`--product` 옵션으로 제품 이미지 우선 매칭) |
| `clip_tagger.py` | CLIP 태깅 (로컬) |
| `assemble_video.py` | 영상 조립 (ffmpeg + PIL) |
| `coupang_collector.py` | 쿠팡 제품 이미지 자동 수집 |
| `cleanup_library.py` | 삭제된 파일 library.json 정리 |
| `setup.py` | 환경 점검 |
| `WEB_PROMPT.txt` | Claude.ai 스크립트 생성 프롬프트 |

---

## 🚀 최초 1회 세팅

### STEP 1. 패키지 설치

```bash
pip install requests edge-tts Pillow anthropic
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install transformers
```

### STEP 2. ffmpeg 설치

1. https://github.com/BtbN/FFmpeg-Builds/releases 접속
2. `ffmpeg-master-latest-win64-gpl.zip` 다운로드
3. 압축 해제 → `bin` 폴더 파일을 `D:\ffmpeg\bin\` 에 복사
4. 시스템 환경변수 `Path` 에 `D:\ffmpeg\bin` 추가
5. 터미널 재시작 후: `ffmpeg -version`

### STEP 3. 폴더 생성

```bash
python D:\WISSLIST\scripts\setup.py
```

### STEP 4. config.py 수정

```python
PEXELS_API_KEY    = "발급받은_Pexels_키"
PIXABAY_API_KEY   = "발급받은_Pixabay_키"
GIPHY_API_KEY     = "발급받은_Giphy_키"
TENOR_API_KEY     = "발급받은_Tenor_키"      # developers.google.com/tenor
ANTHROPIC_API_KEY = "발급받은_Anthropic_키"  # console.anthropic.com
BASE_DIR = "D:/WISSLIST"

# 직접 만든 배경/엔딩 이미지 (None이면 자동 생성)
CUSTOM_BG_PATH     = None  # "D:/WISSLIST/assets/bg.png"
CUSTOM_ENDING_PATH = None  # "D:/WISSLIST/assets/ending.png"
```

---

## 📦 미디어 수집

```bash
# Giphy GIF
python D:\WISSLIST\scripts\collect.py giphy --count 10

# Tenor GIF (리액션 특화, 추천)
python D:\WISSLIST\scripts\collect_tenor.py

# Pexels 이미지
python D:\WISSLIST\scripts\collect.py pexels

# 전체 소스
python D:\WISSLIST\scripts\collect.py all
```

Giphy 중복만 나올 때: `tag_map.py`의 `GIF_CATEGORY_QUERIES`에 새 검색어 추가하거나 직접 다운로드 후 `import_custom.py` 사용.

---

## 🎬 영상 조립 파이프라인

```
[1/6] 나레이션 생성 (edge-tts CLI, 랜덤 목소리)
      → SunHiNeural(여성) / InJoonNeural(남성) / HyunsuNeural(남성)
[2/6] 세그먼트 클립 생성 (ffmpeg + PIL)
      → 자막 2분할 (마침표 우선, 없으면 단어 절반)
      → 미디어 변환 실패 시 후보 5개 자동 교체
[3/6] 엔딩 카드
[4/6] concat
[5/6] 1.5배속 (ffmpeg setpts + atempo)
[6/6] BGM 믹싱 + -t 옵션으로 영상 길이 강제 고정
```

### 레이아웃

```
[0~18%]   헤더 (제목 자동 오버레이)
[20~35%]  자막 영역 (2분할 표시)
[37~90%]  미디어 박스 (GIF/이미지)
```

### 커스텀 배경

`D:\WISSLIST\assets\` 폴더에 파일 저장 시 파일명으로 자동 감지:
- `bg.png` / `background.jpg` → 배경으로 사용
- `ending.png` / `outro.jpg` → 엔딩으로 사용

배경 제작 권장 레이아웃: 상단 18% 헤더 영역, 중단 자막 영역 단순하게, 37~90% 어둡게 비워두기

### BGM

`D:\WISSLIST\bgm\` 폴더에 mp3 넣으면 자동 믹싱. 무료 소스:
- 유튜브 오디오 보관함: studio.youtube.com
- Pixabay Music: pixabay.com/music

---

## 🛒 쿠팡파트너스 링크 만들기

1. partners.coupang.com 로그인
2. 링크 생성 → 상품 링크
3. 쿠팡 제품 URL 붙여넣기 → 단축 URL 생성
4. 생성된 링크를 영상 설명란에 붙여넣기

수익 구조: 시청자 링크 클릭 → 24시간 내 구매 → 구매금액의 1~3% 수수료

---

## 🗑️ library.json 정리

```bash
python D:\WISSLIST\scripts\cleanup_library.py --scan   # 미리 보기
python D:\WISSLIST\scripts\cleanup_library.py          # 실제 정리
```

---

## 🤖 CLIP 태그 보완 (주말)

```bash
python D:\WISSLIST\scripts\clip_tagger.py 100
```

---

## 🆓 무료 미디어 소스

| 사이트 | URL | 특징 |
|---|---|---|
| Mixkit | mixkit.co | 리액션 클립, 상업용 무료 |
| Giphy | giphy.com | GIF (API 자동 수집) |
| Tenor | tenor.com | GIF (collect_tenor.py) |
| Pixabay 영상 | pixabay.com/videos | 리액션 영상 무료 |

> ⚠️ 연예인 사진/GIF는 초상권 + 저작권 문제로 수익화 영상에 사용 금지. 익명 리액션 GIF로 대체.

---

## ❓ 오류 해결

| 증상 | 해결 |
|---|---|
| TTS 실패 | `pip install --upgrade edge-tts` |
| ffmpeg 없음 | PATH 등록 후 터미널 재시작 |
| 미디어 변환 실패 | 자동으로 후보 5개 시도. 모두 실패 시 배경만 표시 |
| 영상 길이 이상 | v14 이후 `-t` 옵션으로 자동 고정됨 |

동작 확인된 TTS 목소리: `SunHiNeural`, `InJoonNeural`, `HyunsuNeural`

---

## 📊 비용

| 항목 | 비용 |
|---|---|
| 미디어 수집 전체 | $0 |
| TTS (edge-tts) | $0 |
| 영상 조립 (ffmpeg) | $0 |
| CLIP 태깅 | $0 |
| 스크립트 생성 (Claude.ai 웹) | $0 추가 |
| **총합** | **$0** |
