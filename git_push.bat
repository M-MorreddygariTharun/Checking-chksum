@echo off
git pull origin main
git add .
git commit -m "Auto commit: %date% %time%"
git push origin main
echo Git push completed.
pause
