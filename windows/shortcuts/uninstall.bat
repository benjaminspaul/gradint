@echo off
echo This will completely remove gradint from your system
echo INCLUDING ANY WORDS YOU HAVE ADDED.
echo.
echo If that is not what you want, close this window NOW.
echo Otherwise press any key.
pause >nul

echo Some people run this by mistake.
echo Are you REALLY SURE you want to delete all your words?
pause >nul

echo Absolutely?
pause >nul

echo Positively?
pause >nul

echo Really really really, you are not just pressing buttons at random?
pause >nul

echo.
echo LAST CHANCE - REALLY DELETE EVERYTHING?
pause >nul

if not exist "%HOMEDRIVE%%HOMEPATH%" set HOMEDRIVE=C:
if not exist "%HOMEDRIVE%%HOMEPATH%" set HOMEPATH="\Program Files"
if not exist "%USERPROFILE%" set USERPROFILE="C:\WINDOWS"

tskill gradint-wrapper 2>nul
taskkill /f /im gradint-wrapper.exe 2>nul >nul
cd /D "%HOMEDRIVE%%HOMEPATH%"
rmdir /S /Q gradint
cd /D "%USERPROFILE%"
rmdir /S /Q "Desktop\gradint"
if exist "%AppData%\Microsoft\Windows\Start Menu\Programs\Startup" goto win8
del "Start Menu\Programs\Startup\Run gradint once per day.bat"
rmdir /S /Q "Start Menu\Programs\gradint"

rem This is a special case for Chinese (Simplified) Windows (XP etc), configured to use the "Chinese (PRC)" locale for legacy apps (which means these strings should be gb2312 coded).
if not exist "%USERPROFILE%\����ʼ���˵�" goto end
rmdir /S /Q "%USERPROFILE%\����\gradint" "%USERPROFILE%\����ʼ���˵�\����\gradint"
del "%USERPROFILE%\����ʼ���˵�\����\����\Run gradint once per day.bat"
goto end

:win8
del "%AppData%\Microsoft\Windows\Start Menu\Programs\Startup\Run gradint once per day.bat"
rmdir /S /Q "%AppData%\Microsoft\Windows\Start Menu\Programs\gradint"

:end
