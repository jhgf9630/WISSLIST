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

:: STEP 1: Product name input
:INPUT_PRODUCT
set /p PRODUCT="  Product name (e.g. butterring, gel-mask): "
if "%PRODUCT%"=="" (
    echo  [!] Please enter a product name.
    goto INPUT_PRODUCT
)
echo.
echo  [OK] Product: %PRODUCT%

:: Hook type input (optional)
echo.
set /p HOOK="  Recent hook types used (optional, press Enter to skip. e.g. empathy,empathy): "
echo.

:: STEP 2: Check import_here folder
echo  --------------------------------------------
echo  [STEP 2] Check product image
echo  --------------------------------------------
echo.

:WAIT_IMAGE
set FILE_COUNT=0
pushd "%IMPORT_DIR%" 2>nul
for %%f in (*.jpg *.jpeg *.png *.webp *.gif) do set /a FILE_COUNT+=1
popd

if %FILE_COUNT%==0 (
    echo  [!] No image found in import_here folder.
    echo.
    echo  Please do the following, then press Enter:
    echo  1. Save product image from Coupang
    echo  2. Filename: %PRODUCT%.jpeg (or .png)
    echo  3. Save to: %IMPORT_DIR%
    echo.
    pause
    goto WAIT_IMAGE
)

echo  [OK] %FILE_COUNT% image(s) found
echo.

:: STEP 3: Run import_custom.py
echo  --------------------------------------------
echo  [STEP 3] Registering image...
echo  --------------------------------------------
echo.
python "%SCRIPTS%\import_custom.py" --product "%PRODUCT%"
if errorlevel 1 (
    echo.
    echo  [ERROR] import_custom.py failed.
    pause
    exit /b 1
)
echo.

:: STEP 4: Run generate_script.py
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
    echo.
    echo  [ERROR] Script generation failed.
    echo  Check ANTHROPIC_API_KEY in config.py
    pause
    exit /b 1
)
echo.

if not exist "%JSON_DIR%\today_script.json" (
    echo  [ERROR] today_script.json not created.
    pause
    exit /b 1
)
echo  [OK] today_script.json saved.
echo.

:: STEP 5: Run assemble_video.py
echo  --------------------------------------------
echo  [STEP 5] Assembling video...
echo  --------------------------------------------
echo.
python "%SCRIPTS%\assemble_video.py"
if errorlevel 1 (
    echo.
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
