@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

:: ============================================================
:: WISSLIST 영상 제작 자동화 배치파일
:: 사용법: wisslist.bat
:: 위치: D:\WISSLIST\wisslist.bat (더블클릭 실행)
:: ============================================================

set BASE=D:\WISSLIST
set SCRIPTS=%BASE%\scripts
set IMPORT_DIR=%BASE%\media_library\import_here
set JSON_DIR=%BASE%\scripts_json
set OUTPUT_DIR=%BASE%\output

:: 제목
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
echo.

:: ── STEP 2. import_here 폴더 파일 확인 ─────────────────────
echo  ────────────────────────────────────────────
echo  [STEP 2] 제품 이미지 등록
echo  ────────────────────────────────────────────
echo.
echo  import_here 폴더를 확인합니다...
echo  경로: %IMPORT_DIR%
echo.

:WAIT_IMAGE
set FILE_COUNT=0
for %%f in ("%IMPORT_DIR%\*.jpg" "%IMPORT_DIR%\*.jpeg" "%IMPORT_DIR%\*.png" "%IMPORT_DIR%\*.webp") do (
    set /a FILE_COUNT+=1
)

if %FILE_COUNT%==0 (
    echo  ⚠️  import_here 폴더에 이미지가 없습니다.
    echo.
    echo  아래 작업을 완료한 후 Enter를 누르세요:
    echo  1. 쿠팡에서 [%PRODUCT%] 이미지 우클릭 → 이미지 저장
    echo  2. 저장 위치: %IMPORT_DIR%
    echo.
    pause
    goto WAIT_IMAGE
)

echo  ✅ 이미지 %FILE_COUNT%개 발견
echo.

:: ── STEP 3. import_custom.py 실행 ──────────────────────────
echo  ────────────────────────────────────────────
echo  [STEP 3] import_custom.py 실행 중...
echo  ────────────────────────────────────────────
echo.
python %SCRIPTS%\import_custom.py --product "%PRODUCT%"
if errorlevel 1 (
    echo.
    echo  ❌ import_custom.py 실패. 오류를 확인해주세요.
    pause
    exit /b 1
)
echo.

:: ── STEP 4. Claude.ai 안내 + 채팅방 열기 ──────────────────
echo  ────────────────────────────────────────────
echo  [STEP 4] 스크립트 생성 (Claude.ai)
echo  ────────────────────────────────────────────
echo.

:: Claude.ai 채팅방 열기
:: ▼▼▼ 아래 URL을 본인의 채팅방 링크로 교체하세요 ▼▼▼
set CLAUDE_URL=https://claude.ai/new
:: ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

echo  브라우저에서 Claude.ai를 엽니다...
start "" "%CLAUDE_URL%"
echo.
echo  ┌─────────────────────────────────────────┐
echo  │  Claude.ai에서 아래를 수행해주세요:     │
echo  │                                         │
echo  │  1. WEB_PROMPT.txt 내용 붙여넣기        │
echo  │  2. 제품명: %PRODUCT%
echo  │  3. JSON 출력 확인                      │
echo  └─────────────────────────────────────────┘
echo.

:: ── STEP 5. JSON 파일 감지 대기 ────────────────────────────
echo  ────────────────────────────────────────────
echo  [STEP 5] 스크립트 JSON 저장 대기
echo  ────────────────────────────────────────────
echo.
echo  Claude.ai에서 출력된 JSON을 아래 위치에 저장해주세요:
echo.
echo  파일명: %PRODUCT%.json
echo  저장위치: %JSON_DIR%\
echo.
echo  저장이 완료되면 Enter를 누르세요.
pause > nul

:: JSON 파일 존재 확인
set JSON_FILE=%JSON_DIR%\%PRODUCT%.json
if not exist "%JSON_FILE%" (
    echo.
    echo  ⚠️  %JSON_FILE% 파일을 찾을 수 없습니다.
    echo  파일을 저장한 후 Enter를 누르세요.
    pause > nul
)

if not exist "%JSON_FILE%" (
    echo  ❌ JSON 파일이 없습니다. 종료합니다.
    pause
    exit /b 1
)

:: today_script.json으로 복사
echo.
echo  ✅ %PRODUCT%.json 발견
echo  → today_script.json으로 복사 중...
copy /y "%JSON_FILE%" "%JSON_DIR%\today_script.json" > nul
echo  ✅ today_script.json 업데이트 완료
echo.

:: ── STEP 6. assemble_video.py 실행 ─────────────────────────
echo  ────────────────────────────────────────────
echo  [STEP 6] 영상 조립 시작
echo  ────────────────────────────────────────────
echo.
python %SCRIPTS%\assemble_video.py
if errorlevel 1 (
    echo.
    echo  ❌ 영상 조립 실패. 오류를 확인해주세요.
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

:: 업로드 안내
echo  ┌─────────────────────────────────────────┐
echo  │  유튜브 업로드 체크리스트               │
echo  │                                         │
echo  │  □ 제목: JSON의 title 값 복붙           │
echo  │  □ 설명란: 쿠팡링크 + 면책고지          │
echo  │  □ 썸네일: Canva에서 제작               │
echo  │  □ #Shorts 태그 추가                    │
echo  │  □ 댓글 7개 중 하나 복붙               │
echo  └─────────────────────────────────────────┘
echo.
pause
