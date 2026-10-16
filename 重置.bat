@echo off
chcp 65001 >nul
type nul > "%~dp0reset.txt"
echo 已重置，签到名单已清空，仅统计之后的新签到。
