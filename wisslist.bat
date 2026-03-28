@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

set BASE=D:\WISSLIST
set SCRIPTS=%BASE%\scripts
set IMPORT_DIR=%BASE%\media_library\import_here
set JSON_DIR=%BASE%\scripts_json
set OUTPUT_DIR=%BASE%\output

cls
echo.
echo  ============================================
echo   WISSLIST 영상 제작 자동화
echo  ============================================
echo.

:: ── STEP 1. 제품명 입력 ────────────────────────────────────
:INPUT_PRODUCT
set /p PRODUCT="  제품명 입력 (예: 버터링, 겔마스크): "
if "%PRODUCT%"=="" (
    echo  ⚠️  제품명을 입력해주세요.
    goto INPUT_PRODUCT
)
echo.
echo  ✅ 제품명: %PRODUCT%

:: 훅 유형 입력 (다양성 유지용, 선택사항)
echo.
set /p HOOK="  최근 사용 훅 유형 (선택, 엔터 생략 가능. 예: 공감형,공감형): "
echo.

:: ── STEP 2. 이미지 확인 ────────────────────────────────────
echo  ────────────────────────────────────────────
echo  [STEP 2] 제품 이미지 확인
echo  ────────────────────────────────────────────
echo.

:WAIT_IMAGE
set FILE_COUNT=0
for %%f in ("%IMPORT_DIR%\*.jpg" "%IMPORT_DIR%\*.jpeg" "%IMPORT_DIR%\*.png" "%IMPORT_DIR%\*.webp") do set /a FILE_COUNT+=1

if %FILE_COUNT%==0 (
    echo  ⚠️  import_here 폴더에 이미지가 없습니다.
    echo.
    echo  작업 후 Enter를 누르세요:
    echo  1. 쿠팡에서 [%PRODUCT%] 이미지 우클릭 → 이미지 저장
    echo  2. 파일명: %PRODUCT%.jpeg (또는 .png)
    echo  3. 저장 위치: %IMPORT_DIR%
    echo.
    pause
    goto WAIT_IMAGE
)

echo  ✅ 이미지 %FILE_COUNT%개 발견
echo.

:: ── STEP 3. import_custom.py 실행 ──────────────────────────
echo  ────────────────────────────────────────────
echo  [STEP 3] 이미지 등록 (import_custom.py)
echo  ────────────────────────────────────────────
echo.
python "%SCRIPTS%\import_custom.py" --product "%PRODUCT%"
if errorlevel 1 (
    echo.
    echo  ❌ import_custom.py 실패
    pause
    exit /b 1
)
echo.

:: ── STEP 4. generate_script.py로 JSON 자동 생성 ────────────
echo  ────────────────────────────────────────────
echo  [STEP 4] 스크립트 자동 생성 (Anthropic API)
echo  ────────────────────────────────────────────
echo.
echo  WEB_PROMPT.txt 프롬프트로 스크립트를 생성합니다...
echo.

if "%HOOK%"=="" (
    python "%SCRIPTS%\generate_script.py" "%PRODUCT%"
) else (
    python "%SCRIPTS%\generate_script.py" "%PRODUCT%" --hook "%HOOK%"
)

if errorlevel 1 (
    echo.
    echo  ❌ 스크립트 생성 실패
    echo  config.py의 ANTHROPIC_API_KEY를 확인하세요.
    pause
    exit /b 1
)
echo.

:: 생성된 JSON 확인
set SAFE_NAME=%PRODUCT%
set JSON_FILE=%JSON_DIR%\%SAFE_NAME%.json
if not exist "%JSON_DIR%\today_script.json" (
    echo  ❌ today_script.json이 생성되지 않았습니다.
    pause
    exit /b 1
)
echo  ✅ today_script.json 저장 완료
echo.

:: ── STEP 5. assemble_video.py 실행 ─────────────────────────
echo  ────────────────────────────────────────────
echo  [STEP 5] 영상 조립 (assemble_video.py)
echo  ────────────────────────────────────────────
echo.
python "%SCRIPTS%\assemble_video.py"
if errorlevel 1 (
    echo.
    echo  ❌ 영상 조립 실패
    pause
    exit /b 1
)

:: ── 완료 ────────────────────────────────────────────────────
echo.
echo  ============================================
echo   ✅ 완료! 출력 폴더를 엽니다.
echo  ============================================
echo.
start "" "%OUTPUT_DIR%"

echo  ┌─────────────────────────────────────────┐
echo  │  유튜브 업로드 체크리스트               │
echo  │                                         │
echo  │  □ 제목: today_script.json의 title      │
echo  │  □ 설명란: 쿠팡링크 + 면책고지          │
echo  │  □ 썸네일: Canva 제작                   │
echo  │  □ #Shorts 해시태그 추가                │
echo  │  □ 첫 댓글 등록                         │
echo  └─────────────────────────────────────────┘
echo.
pause
