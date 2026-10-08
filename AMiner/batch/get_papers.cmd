@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

rem ============================================================
rem  批量执行 query_paper_lists
rem  依次对 7 个关键词调用 main.py，size=10，max_pages=10
rem  输出：papers_关键词_参数.json
rem ============================================================

set "PY=python"
set "SIZE=10"
set "MAX_PAGES=10"

set "KEYWORDS=生命科学 材料化学 高能物理 量子科技 集成电路 新型电力系统 航空航天"

set /a COUNT=0
set /a OK=0
set /a FAIL=0

echo ============================================================
echo  开始批量查询，共 7 个关键词
echo ============================================================
echo.

for %%K in (%KEYWORDS%) do (
    set /a COUNT+=1
    echo ------------------------------------------------------------
    echo [!COUNT!] 关键词: %%K
    echo ------------------------------------------------------------
    %PY% ../main.py --function query_paper_lists --params "{\"keywords\": [\"%%K\"], \"size\": %SIZE%, \"max_pages\": %MAX_PAGES%}"
    if errorlevel 1 (
        set /a FAIL+=1
        echo [失败] %%K
    ) else (
        set /a OK+=1
        echo [成功] %%K
    )
    echo.
)

echo ============================================================
echo  全部完成: 共 !COUNT! 个, 成功 !OK! 个, 失败 !FAIL! 个
echo ============================================================

endlocal
pause