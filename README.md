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
| `generate_script.py` | **제품명 입력 → 스크립트 자동 생성 (Anthropic API)** |
| `assemble_video.py` | 영상 조립 (ffmpeg + PIL) |
| `coupang_collector.py` | 쿠팡 제품 이미지 수집 |
| `cleanup_library.py` | 삭제된 파일 library.json 정리 |
| `setup.py` | 환경 점검 |

모든 파일은 `D:\WISSLIST\scripts\` 에 저장

---

## 🚀 최초 1회 세팅

### STEP 1. 패키지 설치

```bash
pip install requests edge-tts Pillow anthropic
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install transformers
```

> moviepy는 더 이상 사용하지 않습니다. ffmpeg를 직접 사용합니다.

### STEP 2. ffmpeg 설치 (필수)

1. https://github.com/BtbN/FFmpeg-Builds/releases 접속
2. `ffmpeg-master-latest-win64-gpl.zip` 다운로드
3. 압축 해제 후 `bin` 폴더 내 파일들을 `D:\ffmpeg\bin\` 에 복사
4. 시스템 환경 변수 `Path` 에 `D:\ffmpeg\bin` 추가
5. 터미널 재시작 후 확인:

```bash
ffmpeg -version
```

### STEP 3. D드라이브 폴더 생성

```bash
python D:\WISSLIST\scripts\setup.py
```

폴더 자동 생성 + 패키지 + API 연결 전항목 ✅ 확인

### STEP 4. config.py 수정

`D:\WISSLIST\scripts\config.py` 열어서 API 키 입력 후 저장

```python
PEXELS_API_KEY    = "발급받은_Pexels_키"
PIXABAY_API_KEY   = "발급받은_Pixabay_키"
GIPHY_API_KEY     = "발급받은_Giphy_키"
ANTHROPIC_API_KEY = "발급받은_Anthropic_API_키"
BASE_DIR = "D:/WISSLIST"

# 커스텀 배경/엔딩 이미지 (직접 만들어서 경로 입력, None이면 자동 생성)
CUSTOM_BG_PATH     = None  # 예: "D:/WISSLIST/assets/bg.png"
CUSTOM_ENDING_PATH = None  # 예: "D:/WISSLIST/assets/ending.png"
```

> **Anthropic API 키 발급:** https://console.anthropic.com → API Keys

---

## 📦 STEP 5. 미디어 수집

### 기본 실행 (대화형 메뉴)

```bash
python D:\WISSLIST\scripts\collect.py
```

```
1. Pexels    (이미지+영상, 고품질, 무제한)
2. Pixabay   (이미지, 100건/일)
3. Giphy     (GIF 짤 특화, 42건/일) ⭐
4. Wikimedia (공공 이미지, 무제한)
5. 전체 소스
```

### 소스 지정 실행

```bash
python D:\WISSLIST\scripts\collect.py giphy
python D:\WISSLIST\scripts\collect.py pexels
python D:\WISSLIST\scripts\collect.py giphy pexels
python D:\WISSLIST\scripts\collect.py all
python D:\WISSLIST\scripts\collect.py giphy --count 10
```

> **Giphy가 중복만 나올 때:** tag_map.py의 GIF_CATEGORY_QUERIES에 새 검색어 추가하거나,  
> giphy.com에서 직접 다운로드 후 import_custom.py 사용

---

## 🖼️ STEP 6. 커스텀 이미지/짤 직접 등록

Mixkit, Coverr, Giphy 등에서 직접 다운받은 파일 등록:

```
① import_here 폴더에 파일 넣기
   D:\WISSLIST\media_library\import_here\

② 실행
   python D:\WISSLIST\scripts\import_custom.py

③ 결과
   → custom 폴더로 이동 + library.json 자동 등록
```

### 쿠팡 제품 이미지 수집

```bash
# 대화형
python D:\WISSLIST\scripts\coupang_collector.py

# 직접 실행
python D:\WISSLIST\scripts\coupang_collector.py "컵라면"
python D:\WISSLIST\scripts\coupang_collector.py "에어프라이어" --count 5
```

> 자동 수집이 어려우면: 쿠팡에서 상품 이미지 우클릭 → 저장 → import_here 폴더 → import_custom.py

---

## 🤖 STEP 7. CLIP 태그 보완 (주말/여유 시)

```bash
# 기본 50개
python D:\WISSLIST\scripts\clip_tagger.py

# 100개
python D:\WISSLIST\scripts\clip_tagger.py 100
```

> 파일 이동 없이 library.json의 태그만 보강합니다. i7-8565U 기준 50장 약 2~3분

---

## ✍️ STEP 8. 스크립트 자동 생성 (완전 자동화)

### 방법 A — Anthropic API 자동 생성 (추천)

제품명 하나만 입력하면 AI가 카테고리/타겟/공감포인트/훅 유형까지 자동 결정:

```bash
# 제품명 직접 입력
python D:\WISSLIST\scripts\generate_script.py 안성탕면

# 대화형
python D:\WISSLIST\scripts\generate_script.py
```

실행하면 `today_script.json`이 자동 저장됩니다. 바로 영상 조립으로 넘어가면 됩니다.

### 방법 B — Claude.ai 웹에서 수동 생성

1. Claude.ai 새 대화창 열기
2. 아래 **[SYSTEM PROMPT]** 전체 복사 → 첫 메시지로 전송
3. 제품명 입력 → JSON 복사 → `today_script.json` 저장

---

## 📋 스크립트 자동 생성 SYSTEM PROMPT (방법 B용)

```
당신은 한국 유튜브 쇼츠 스크립트 전문 작가입니다.
채널 콘셉트: 음식/맛집/편의점/배달 위주의 공감 콘텐츠.
사용자가 제품명만 알려주면 카테고리, 타겟, 공감포인트, 훅 유형을 직접 판단해서 스크립트를 완성하세요.

[핵심 철학]
- 광고처럼 보이면 절대 안 됩니다
- 시청자는 재미있거나 공감되는 콘텐츠를 보고 있다고 느껴야 합니다
- 구매 유도 문구는 영상 안에 절대 없어야 합니다

[말투 규칙 — 가장 중요]
- 친한 친구한테 카톡 보내는 말투로 작성
- "~야", "~이야", "~거든", "~잖아" 등 반말/구어체
- "~습니다" 절대 금지

[segment 규칙]
- 각 segment: 1~2초 분량 (10~20자 이내)
- 20초 영상 → 12~16개 segment

[출력 형식 — JSON만]
{
  "title": "제목 (30자 이내)",
  "hook_type": "공감/궁금증/반전/정보",
  "segments": [
    {
      "time": "00~01s",
      "narration": "짧고 친근한 나레이션",
      "on_screen_text": "핵심어 (10자 이내)",
      "visual_tag": ["태그1", "태그2"],
      "sfx": "whoosh/ding/boing/없음"
    }
  ],
  "closing_line": "마지막 한 마디",
  "description_cta": "설명란 안내",
  "disclaimer": "이 영상은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
}
```

---

## 🎬 STEP 9. 영상 조립

```bash
python D:\WISSLIST\scripts\assemble_video.py
```

자동 처리 순서:

```
[1/6] 나레이션 생성 (edge-tts CLI, 무료)
[2/6] 세그먼트 클립 생성 (ffmpeg + PIL)
[3/6] 엔딩 카드 생성
[4/6] 클립 concat (ffmpeg concat demuxer, 초고속)
[5/6] 1.5배속 적용 (ffmpeg setpts + atempo)
[6/6] BGM 믹싱 + 최종 MP4 저장
```

완성 영상: `D:\WISSLIST\output\영상제목.mp4`  
소요 시간: 약 2~5분

### 커스텀 배경/엔딩 사용 방법

직접 디자인한 배경 이미지(1080×1920 PNG)를 사용하려면:

1. 배경 이미지 준비 (1080×1920, PNG 권장)
   - 미디어 박스 영역(상단 20%~65%)은 어둡게 비워두기
   - 하단 35%는 자막이 올라갈 공간이므로 단순하게
2. `D:\WISSLIST\assets\` 폴더에 저장
3. `config.py` 수정:

```python
CUSTOM_BG_PATH     = "D:/WISSLIST/assets/bg.png"
CUSTOM_ENDING_PATH = "D:/WISSLIST/assets/ending.png"
```

설정하면 제목 텍스트와 자막만 스크립트에서 자동으로 오버레이됩니다.

---

## 🎵 BGM 추가 방법

`D:\WISSLIST\bgm\` 폴더에 MP3 파일을 넣으면 자동으로 영상에 믹싱됩니다.

무료 BGM 소스:
- **유튜브 오디오 보관함**: studio.youtube.com → 오디오 보관함 → 무료 음악
- **Pixabay Music**: pixabay.com/music

BGM 볼륨 조절: `assemble_video.py`의 `add_bgm()` 함수에서 `bgm_volume=0.15` 값 변경  
(0.10 = 조용하게, 0.25 = 크게)

---

## 📤 STEP 10. 유튜브 업로드

1. `D:\WISSLIST\output\` 에서 MP4 파일 확인
2. 유튜브 스튜디오 → **만들기** → **동영상 업로드**
3. 제목: `today_script.json`의 `title` 값
4. 설명란:

```
📦 영상 속 제품 👇
[쿠팡파트너스 링크 붙여넣기]

이 영상은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.
```

5. 해시태그 추가 (예: #가성비 #추천템 #쿠팡추천)
6. **공개** 설정 후 업로드

---

## 📅 일상 운영 루틴

### 매일 (약 5~10분)

```bash
# 1. 미디어 수집 (2~3분)
python D:\WISSLIST\scripts\collect.py giphy pexels

# 2. 스크립트 자동 생성 (30초)
python D:\WISSLIST\scripts\generate_script.py 오늘의제품명

# 3. 영상 조립 (2~5분)
python D:\WISSLIST\scripts\assemble_video.py
```

### 주말 (약 5분, 충전 중)

```bash
python D:\WISSLIST\scripts\clip_tagger.py 100
```

---

## 🗑️ 사진 삭제 후 JSON 정리

```bash
# 미리 보기 (실제 삭제 X)
python D:\WISSLIST\scripts\cleanup_library.py --scan

# 실제 정리
python D:\WISSLIST\scripts\cleanup_library.py

# 통계만
python D:\WISSLIST\scripts\cleanup_library.py --stats
```

---

## 🆓 무료 짤 소스

| 사이트 | URL | 특징 |
|---|---|---|
| Mixkit | mixkit.co | 리액션/웃긴 클립, 상업용 무료 |
| Coverr | coverr.co/stock-video-footage/meme | 밈 클립, 상업용 무료 |
| Pixabay 영상 | pixabay.com/videos | 리액션 영상 1,800개+, 무료 |
| Giphy | giphy.com | GIF 짤 (API로 자동 수집 가능) |

---

## ⚠️ 오류 해결

### TTS 오류 (edge-tts)
```bash
pip install edge-tts
```

### ffmpeg 없음
- `ffmpeg -version` 확인
- 없으면 PATH 환경변수 재등록 후 터미널 재시작

### 자막이 안 나올 때
- `C:\Windows\Fonts\malgun.ttf` 존재 여부 확인
- 없으면 `config.py` 에서 다른 폰트 경로 지정

---

## 📊 전체 비용

| 항목 | 비용 |
|---|---|
| 미디어 수집 (Pexels/Pixabay/Giphy/Wikimedia) | $0 |
| TTS 나레이션 (edge-tts CLI) | $0 |
| 영상 조립 (ffmpeg) | $0 |
| CLIP 태깅 (로컬 실행) | $0 |
| 스크립트 생성 (Anthropic API) | 영상당 약 $0.01 |
| 스크립트 생성 (Claude Pro 웹 사용 시) | $0 추가 |
| 유튜브 업로드 | $0 |
| **총합** | **~$0.01/편** |
