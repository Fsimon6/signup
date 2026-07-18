#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目统一入口 - signup

支持的模块:
- freight: 顺丰运费查询
- excel: Excel数据导入（待开发）
- feishu_sync: 飞书表格同步（待开发）

使用方式:
    python main.py freight
    python main.py excel
    python main.py feishu_sync
"""

from __future__ import annotations

import sys


def run_freight():
    """运行顺丰运费查询模块"""
    from services.freight_service import FreightService

    service = FreightService()
    success, fail, skipped = service.run()
    return 0 if fail == 0 else 2


def run_excel():
    """运行Excel数据导入模块"""
    from services.excel_import_service import ExcelImportService

    service = ExcelImportService()
    return service.run()


def run_feishu_sync():
    """运行飞书表格同步模块"""
    from services.feishu_sync_service import FeishuSyncService

    service = FeishuSyncService()
    return service.run()


def run_all():
    """运行所有模块（按顺序执行）"""
    import pyautogui
    import pyperclip
    import time

    print("=" * 60)
    print("运行所有模块")
    print("=" * 60)

    results = []

    print("\n" + "=" * 60)
    print("模块二: Excel数据导入")
    print("=" * 60)
    try:
        result = run_excel()
        results.append(("excel", result))
    except Exception as exc:
        print(f"  ✗ 模块二执行失败: {exc}")
        import traceback
        traceback.print_exc()
        results.append(("excel", -1))

    print("\n[等待飞书表格状态恢复...]")
    time.sleep(2.0)

    pyautogui.press("escape")
    time.sleep(0.5)

    pyperclip.copy("")
    time.sleep(0.3)

    print("\n" + "=" * 60)
    print("模块一: 顺丰运费查询")
    print("=" * 60)
    try:
        result = run_freight()
        results.append(("freight", result))
    except Exception as exc:
        print(f"  ✗ 模块一执行失败: {exc}")
        import traceback
        traceback.print_exc()
        results.append(("freight", -1))


    # print("\n" + "=" * 60)
    # print("模块三: 飞书表格同步")
    # print("=" * 60)
    # try:
    #     result = run_feishu_sync()
    #     results.append(("feishu_sync", result))
    # except Exception as exc:
    #     print(f"  ✗ 模块三执行失败: {exc}")
    #     results.append(("feishu_sync", -1))

    print("\n" + "=" * 60)
    print("所有模块执行完毕")
    print("=" * 60)
    for module, result in results:
        if result == 0:
            print(f"  ✓ {module}: 成功")
        elif result == -1:
            print(f"  ✗ {module}: 异常")
        else:
            print(f"  ✗ {module}: 失败 (退出码: {result})")

    return 0


def show_usage():
    """显示使用帮助"""
    print("""
项目统一入口 - signup

使用方式:
    python main.py <module>

支持的模块:
    freight      - 顺丰运费查询（从飞书读取单号，查询顺丰，写回飞书）
    excel        - Excel数据导入（读取Excel，匹配订单，写回飞书）
    feishu_sync  - 飞书表格同步（飞书表格A+B，匹配订单，写入飞书表格C）
    all          - 运行所有模块（按顺序执行模块二→模块一）
    """)


def main():
    if len(sys.argv) < 2:
        show_usage()
        return 1

    module = sys.argv[1].lower()

    try:
        if module == "freight":
            return run_freight()
        elif module == "excel":
            return run_excel()
        elif module == "feishu_sync":
            return run_feishu_sync()
        elif module == "all":
            return run_all()
        else:
            print(f"未知模块: {module}")
            show_usage()
            return 1
    except KeyboardInterrupt:
        print("\n用户中断")
        return 130
    except Exception as exc:
        print(f"\n程序出错: {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
