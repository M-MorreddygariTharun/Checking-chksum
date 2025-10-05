@echo off
REM git-push.bat - safe push using environment vars GIT_USERNAME and GIT_TOKEN
setlocal enabledelayedexpansion

REM Change to repository folder (optional if Jenkins workspace is repo root)
REM cd /d D:\CHKSUM_PYTHON_SCRIPT\CHKSUM_CHECKER

echo [GIT] Checking out main...
git checkout main

echo [GIT] Pulling latest from origin/main...
git pull origin main

echo [GIT] Staging changes...
git add -A

REM Only commit if there are staged changes
git diff --cached --quiet
if errorlevel 1 (
    echo [GIT] Changes detected - committing...
    git -c user.name="%GIT_USERNAME%" -c user.email="%GIT_USERNAME%@users.noreply.github.com" commit -m "Auto commit from Jenkins"
) else (
    echo [GIT] No changes to commit.
)

REM If GIT_TOKEN is provided, set temporary remote with token to push securely
if defined GIT_TOKEN (
    if not defined GIT_USERNAME (
        echo [ERROR] GIT_USERNAME not set. Cannot push with token.
        exit /b 1
    )

    REM get current origin url (https)
    for /f "tokens=*" %%u in ('git remote get-url origin') do set ORIGIN_URL=%%u

    REM build tokenized URL - insert username:token@ into HTTPS URL
    REM origin url like https://github.com/owner/repo.git
    set TOKEN_REMOTE=%ORIGIN_URL:https://=%  REM remove https:// prefix
    set PUSH_URL=https://%GIT_USERNAME%:%GIT_TOKEN%@%TOKEN_REMOTE%

    echo [GIT] Pushing to origin using tokenized remote...
    git push %PUSH_URL% main
    set EXITCODE=%ERRORLEVEL%

    REM Optional: push with normal remote to set upstream (if above succeeded)
    if %EXITCODE% EQU 0 (
        echo [GIT] Push succeeded.
    ) else (
        echo [GIT] Push failed with exit code %EXITCODE%.
        exit /b %EXITCODE%
    )
) else (
    echo [GIT] No GIT_TOKEN provided. Trying normal push (may fail if auth needed)...
    git push origin main
)

echo [GIT] Git push completed.
endlocal
pause
