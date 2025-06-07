cd D:\CHKSUM_PYTHON_SCRIPT\CHKSUM_CHECKER

:: Checkout the actual branch (main)
git checkout main

:: Pull latest changes from GitHub
git pull origin main

:: Stage changes
git add .

:: Commit changes (only if there are any)
git diff --cached --quiet || git commit -m "Auto commit from Jenkins"

:: Push changes to GitHub
git push origin main

echo Git push completed.

pause
