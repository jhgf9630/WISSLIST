# 🎬 WISSLIST 운영 가이드

> 유튜브 쇼츠 × 쿠팡파트너스 자동화 파이프라인  
> 채널: 위씨리스트 (@wisslist)

---

## 📁 파일 목록

| 파일 | 역할 |
|---|---|
| `config.py` | API 키 및 경로 설정 |
| `tag_map.py` | 태그 체계 + 검색어 매핑 |
| `library.py` | library.json 읽기/쓰기 모듈 |
| `collectors.py` | Pexels/Pixabay/Giphy/Wikimedia 수집 엔진 |
| `collect.py` | 미디어 수집 실행 |
| `collect_tenor.py` | Tenor GIF 수집 (리액션 GIF 특화) |
| `import_custom.py` | 직접 찾은 이미지/GIF 등록 |
| `clip_tagger.py` | CLIP 보완 태깅 (로컬 실행) |
| `assemble_video.py` | 영상 조립 (ffmpeg + PIL) |
| `coupang_collector.py` | 쿠팡 제품 이미지 수집 |
| `cleanup_library.py` | 삭제된 파일 library.json 정리 |
| `setup.py` | 환경 점검 + 폴더 생성 |
| `WEB_PROMPT.txt` | Claude.ai 웹 스크립트 생성용 프롬프트 |

모든 파일 위치: `D:\WISSLIST\scripts\`

---

## 🚀 최초 1회 세팅

### STEP 1. 패키지 설치

```bash
pip install requests edge-tts Pillow anthropic
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install transformers
```

### STEP 2. ffmpeg 설치 (필수)

1. https://github.com/BtbN/FFmpeg-Builds/releases 접속
2. `ffmpeg-master-latest-win64-gpl.zip` 다운로드
3. 압축 해제 후 `bin` 폴더 파일들을 `D:\ffmpeg\bin\` 에 복사
4. 시스템 환경 변수 `Path` 에 `D:\ffmpeg\bin` 추가
5. 터미널 재시작 후 확인:

```bash
ffmpeg -version
```

### STEP 3. 폴더 생성

```bash
python D:\WISSLIST\scripts\setup.py
```

### STEP 4. config.py 수정

```python
PEXELS_API_KEY    = "발급받은_Pexels_키"
PIXABAY_API_KEY   = "발급받은_Pixabay_키"
GIPHY_API_KEY     = "발급받은_Giphy_키"
TENOR_API_KEY     = "발급받은_Tenor_키"   # https://developers.google.com/tenor
ANTHROPIC_API_KEY = "발급받은_Anthropic_키"  # https://console.anthropic.com
BASE_DIR = "D:/WISSLIST"

# 커스텀 배경/엔딩 이미지 (직접 제작 후 경로 입력, None이면 자동 생성)
CUSTOM_BG_PATH     = None  # 예: "D:/WISSLIST/assets/bg.png"
CUSTOM_ENDING_PATH = None  # 예: "D:/WISSLIST/assets/ending.png"
```

---

## 📦 STEP 5. 미디어 수집

### Giphy / Pexels / Pixabay / Wikimedia

```bash
python D:\WISSLIST\scripts\collect.py giphy
python D:\WISSLIST\scripts\collect.py pexels
python D:\WISSLIST\scripts\collect.py all
python D:\WISSLIST\scripts\collect.py giphy --count 10
```

### Tenor GIF (리액션 GIF 특화, 추천)

```bash
python D:\WISSLIST\scripts\collect_tenor.py
```

Tenor는 익명 리액션 GIF 위주로 수집합니다. Giphy와 함께 사용하면 라이브러리가 풍부해집니다.

### Giphy 중복만 나올 때

`tag_map.py`의 `GIF_CATEGORY_QUERIES`에 새 검색어를 추가하거나, giphy.com에서 직접 다운로드 후 `import_custom.py` 사용.

---

## 🖼️ STEP 6. 커스텀 이미지/제품 이미지 등록

### 일반 이미지/GIF 등록

```
① import_here 폴더에 파일 넣기
   D:\WISSLIST\media_library\import_here\

② 실행
   python D:\WISSLIST\scripts\import_custom.py
```

### 제품 이미지 등록 (영상 내 우선 매칭 보장)

```bash
# 쿠팡에서 제품 이미지 저장 → import_here 폴더에 넣기
python D:\WISSLIST\scripts\import_custom.py --product 까르보불닭볶음면
```

실행하면 `제품이미지`, `까르보불닭볶음면` 태그가 자동으로 붙습니다.  
스크립트 JSON에 `"product_name": "까르보불닭볶음면"` 이 있으면 해당 이미지가 자동으로 우선 매칭됩니다.

### 이미 등록된 파일에 제품 태그 추가

같은 명령어를 다시 실행하면 태그만 업데이트되고 product 폴더로 이동됩니다.

---

## 🤖 STEP 7. CLIP 태그 보완 (주말)

```bash
python D:\WISSLIST\scripts\clip_tagger.py        # 기본 50개
python D:\WISSLIST\scripts\clip_tagger.py 100    # 100개
```

파일 이동 없이 `library.json`의 태그만 보강합니다.

---

## ✍️ STEP 8. 스크립트 생성 (Claude.ai 웹)

### 순서

1. Claude.ai 새 대화창 열기 (**매번 새 대화**)
2. `D:\WISSLIST\scripts\WEB_PROMPT.txt` 내용 전체 복사 → 첫 메시지로 붙여넣기
3. 다음 메시지에 입력:

```
제품명: 까르보불닭볶음면
```

또는 더 구체적으로:

```
제품명: 까르보불닭볶음면
최근 사용 훅: 공감형, 공감형   ← 다양성 유지를 위해 기록
이번 설정: 야식 시간, 자취방
```

4. 출력된 JSON 복사

### JSON 저장

메모장 열기 → 붙여넣기 → 파일명 `today_script.json` → `D:\WISSLIST\scripts_json\` 에 저장

**중요:** JSON 안에 `"product_name"` 항목이 있는지 확인. 없으면 직접 추가:

```json
{
  "title": "...",
  "hook_type": "...",
  "product_name": "까르보불닭볶음면",
  "segments": [...]
}
```

### 스크립트 다양성 유지

매번 **새 대화**로 시작하고, 최근 사용 훅 유형을 기록해서 전달하면 AI가 다른 패턴을 선택합니다.

---

## 🎬 STEP 9. 영상 조립

```bash
python D:\WISSLIST\scripts\assemble_video.py
```

### 자동 처리 단계

```
[1/6] 나레이션 생성 (edge-tts CLI, 랜덤 목소리)
      사용 가능 목소리: SunHi(여성) / InJoon(남성) / Hyunsu(남성)
[2/6] 세그먼트 클립 생성 (ffmpeg + PIL)
      - 자막 2분할: 나레이션을 절반씩 나눠 한 세그먼트에 두 번 표시
      - 미디어 변환 실패 시 후보 자동 교체 (최대 5개 후보)
[3/6] 엔딩 카드 생성
[4/6] 클립 concat (ffmpeg concat demuxer)
[5/6] 1.5배속 적용 (ffmpeg setpts + atempo)
[6/6] BGM 믹싱 + 최종 저장
```

완성 영상: `D:\WISSLIST\output\영상제목.mp4`  
소요 시간: 약 2~5분

### 레이아웃 구조

```
[0~18%]   헤더 (제목 텍스트 자동 오버레이)
[20~35%]  자막 영역 (나레이션 2분할 표시)
[37~90%]  미디어 박스 (GIF/이미지)
[91~100%] 하단 여백
```

### 커스텀 배경 사용

1. 배경 이미지 제작 (1080×1920 PNG)
   - 미디어 박스 영역(37~90%) 어둡게 비워두기
   - 자막 영역(20~35%) 단순하게 처리
2. `D:\WISSLIST\assets\` 폴더에 저장
3. `config.py` 수정:

```python
CUSTOM_BG_PATH     = "D:/WISSLIST/assets/bg.png"
CUSTOM_ENDING_PATH = "D:/WISSLIST/assets/ending.png"
```

assets 폴더에 파일을 넣으면 config.py 수정 없이도 파일명으로 자동 감지됩니다.
- `bg`, `background` 포함 파일명 → 배경으로 사용
- `ending`, `outro` 포함 파일명 → 엔딩으로 사용

### BGM 추가

`D:\WISSLIST\bgm\` 폴더에 MP3 파일을 넣으면 자동 믹싱됩니다.

무료 BGM 소스:
- **유튜브 오디오 보관함**: studio.youtube.com → 오디오 보관함
- **Pixabay Music**: pixabay.com/music

볼륨 조절: `assemble_video.py`의 `add_bgm(bgm_volume=0.15)` 값 변경

---

## 📤 STEP 10. 유튜브 업로드

1. `D:\WISSLIST\output\` 에서 MP4 확인
2. 유튜브 스튜디오 → 만들기 → 동영상 업로드
3. 제목: `today_script.json`의 `title` 값
4. 설명란:

```
📦 영상 속 제품 👇
[쿠팡파트너스 링크]

이 영상은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.
```

5. 해시태그 추가 (예: #가성비 #추천템 #쿠팡추천)

---

## 📅 매일 루틴 (약 5~10분)

```bash
# 1. 미디어 수집 (선택, 라이브러리 부족 시)
python D:\WISSLIST\scripts\collect.py giphy pexels

# 2. 제품 이미지 등록
#    쿠팡에서 이미지 저장 → import_here 폴더 → 아래 실행
python D:\WISSLIST\scripts\import_custom.py --product 제품명

# 3. 스크립트 생성
#    Claude.ai 새 대화 → WEB_PROMPT.txt 붙여넣기 → 제품명 입력
#    → JSON 복사 → today_script.json 저장

# 4. 영상 조립
python D:\WISSLIST\scripts\assemble_video.py
```

### 주말 (5분)

```bash
python D:\WISSLIST\scripts\clip_tagger.py 100
```

---

## 🗑️ 사진 삭제 후 JSON 정리

탐색기에서 이미지를 삭제해도 `library.json`에 경로가 남습니다.

```bash
python D:\WISSLIST\scripts\cleanup_library.py --scan   # 미리 보기
python D:\WISSLIST\scripts\cleanup_library.py          # 실제 정리
python D:\WISSLIST\scripts\cleanup_library.py --stats  # 통계
```

---

## 🆓 무료 미디어 소스

| 사이트 | URL | 특징 |
|---|---|---|
| Mixkit | mixkit.co | 리액션/웃긴 클립, 상업용 무료 |
| Coverr | coverr.co/stock-video-footage/meme | 밈 클립, 무료 |
| Pixabay 영상 | pixabay.com/videos | 리액션 영상, 무료 |
| Giphy | giphy.com | GIF (API 자동 수집) |
| Tenor | tenor.com | GIF (API 자동 수집, collect_tenor.py) |

### 연예인 이미지 관련 주의사항

연예인 사진/GIF는 **초상권 + 저작권 이중 위험**이 있어 쿠팡파트너스 수익화 영상에 사용 금지.  
대신 Tenor/Giphy의 익명 리액션 GIF로 대체합니다.

---

## ❓ 오류 해결

### TTS 오류

```bash
pip install --upgrade edge-tts
```

동작 확인된 목소리: `ko-KR-SunHiNeural`, `ko-KR-InJoonNeural`, `ko-KR-HyunsuNeural`

### ffmpeg 없음

```bash
ffmpeg -version
```

없으면 `D:\ffmpeg\bin` PATH 등록 후 터미널 재시작.

### 미디어 변환 실패

자동으로 최대 5개 후보 파일을 순서대로 시도합니다. 모두 실패하면 배경만 표시됩니다.  
라이브러리가 부족하면 `collect.py`로 추가 수집하세요.

---

## 📊 전체 비용

| 항목 | 비용 |
|---|---|
| 미디어 수집 전체 | $0 |
| TTS (edge-tts) | $0 |
| 영상 조립 (ffmpeg) | $0 |
| CLIP 태깅 (로컬) | $0 |
| 스크립트 생성 (Claude.ai 웹) | $0 추가 |
| **총합** | **$0** |
