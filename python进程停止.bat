@echo off
:: 检查是否已获取管理员权限
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
:: 如果没有权限，则调用 UAC 提示获取管理员权限
echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
"%temp%\getadmin.vbs"
del /f /q "%temp%\getadmin.vbs"
exit /B
)
:: 已获取管理员权限，继续执行脚本
echo 已成功获取管理员权限！


taskkill /f /t /im python.exe
