@echo off
setlocal enabledelayedexpansion

set BASE=D:\WISSLIST
set SCRIPTS=%BASE%\scripts
set IMPORT_DIR=%BASE%\media_library\import_here
set JSON_DIR=%BASE%\scripts_json
set OUTPUT_DIR=%BASE%\output

cls
echo.
echo  ============================================
echo   WISSLIST - Video Production Automation
echo  ============================================
echo.

:: STEP 1: Product name
:INPUT_PRODUCT
set /p PRODUCT="  Product name: "
if "%PRODUCT%"=="" goto INPUT_PRODUCT
echo.
echo  [OK] Product: %PRODUCT%

echo.
set /p HOOK="  Recent hook types (optional, Enter to skip): "
echo.

:: STEP 2: Check image using Python (no CMD encoding issues)
echo  --------------------------------------------
echo  [STEP 2] Check product image
echo  --------------------------------------------
echo.
echo  Save location: %IMPORT_DIR%
echo.

:WAIT_IMAGE
python -c "import sys,os; files=[f for f in os.listdir(r'%IMPORT_DIR%') if f.lower().endswith(('.jpg','.jpeg','.png','.webp','.gif'))]; sys.exit(0 if files else 1)" 2>nul
if errorlevel 1 (
    echo  [!] No image found in import_here folder.
    echo  1. Save product image to: %IMPORT_DIR%
    echo  2. Press Enter when done.
    pause > nul
    goto WAIT_IMAGE
)
echo  [OK] Image found.
echo.

:: STEP 3: import_custom.py
echo  --------------------------------------------
echo  [STEP 3] Registering image...
echo  --------------------------------------------
echo.
python "%SCRIPTS%\import_custom.py" --product "%PRODUCT%"
if errorlevel 1 (
    echo  [ERROR] import_custom.py failed.
    pause
    exit /b 1
)
echo.

:: STEP 4: generate_script.py
echo  --------------------------------------------
echo  [STEP 4] Generating script via API...
echo  --------------------------------------------
echo.
if "%HOOK%"=="" (
    python "%SCRIPTS%\generate_script.py" "%PRODUCT%"
) else (
    python "%SCRIPTS%\generate_script.py" "%PRODUCT%" --hook "%HOOK%"
)
if errorlevel 1 (
    echo  [ERROR] Script generation failed.
    echo  Check ANTHROPIC_API_KEY in config.py
    pause
    exit /b 1
)
echo.

python -c "import sys,os; sys.exit(0 if os.path.exists(r'%JSON_DIR%\today_script.json') else 1)" 2>nul
if errorlevel 1 (
    echo  [ERROR] today_script.json not created.
    pause
    exit /b 1
)
echo  [OK] today_script.json saved.
echo.

:: STEP 5: assemble_video.py
echo  --------------------------------------------
echo  [STEP 5] Assembling video...
echo  --------------------------------------------
echo.
python "%SCRIPTS%\assemble_video.py"
if errorlevel 1 (
    echo  [ERROR] Video assembly failed.
    pause
    exit /b 1
)

:: Done
echo.
echo  ============================================
echo   Done! Opening output folder...
echo  ============================================
echo.
start "" "%OUTPUT_DIR%"

echo  -----------------------------------------------
echo   YouTube Upload Checklist
echo  -----------------------------------------------
echo   [ ] Title   : use "title" from today_script.json
echo   [ ] Desc    : paste Coupang link + disclaimer
echo   [ ] Thumb   : create on Canva (1280x720)
echo   [ ] Tags    : add #Shorts + hashtags
echo   [ ] Comment : paste one of the 7 canned comments
echo  -----------------------------------------------
echo.
pause
