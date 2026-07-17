# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# """
# 顺丰运费自动查询脚本 - GUI自动化版
#
# 流程:
# 1. 在飞书文档复制单号
# 2. 顺丰网站查询
# 3. 获取交易金额（元）
# 4. 回填飞书
# """
#
# from __future__ import annotations
#
# import sys
# import time
#
# from config import (
#     COL_AMOUNT,
#     COL_TRACKING,
#     FEISHU_TAB_NUMBER,
#     MAX_ROWS,
#     QUERY_DELAY_SECONDS,
#     SF_RESULT_WAIT_SECONDS,
#     SF_TAB_NUMBER,
#     SKIP_FILLED,
# )
# from feishu_client import FeishuBrowserClient
# from sf_express import SFExpressBrowserClient
# from progress import load_progress, save_progress, save_failed
#
#
# def main() -> int:
#     print("=" * 60)
#     print("顺丰运费自动查询 - GUI自动化版")
#     print("=" * 60)
#     print(f"\n飞书文档: 标签页 {FEISHU_TAB_NUMBER}")
#     print(f"顺丰页面: 标签页 {SF_TAB_NUMBER}")
#     print(f"结果等待: {SF_RESULT_WAIT_SECONDS}s")
#     print(f"查询间隔: {QUERY_DELAY_SECONDS}s")
#     print()
#
#     completed_set = load_progress()
#     if completed_set:
#         print(f"断点续传：已完成 {len(completed_set)} 个单号\n")
#
#     feishu = FeishuBrowserClient(tab_number=FEISHU_TAB_NUMBER)
#     sf_client = SFExpressBrowserClient(tab_number=SF_TAB_NUMBER)
#
#     try:
#         print("[1/4] 查找夸克浏览器窗口...")
#         quark = feishu.find_quark_window()
#         if not quark:
#             print("错误：未找到夸克浏览器窗口，请确保夸克已打开")
#             return 1
#         print(f"  找到: {quark.title[:60]}")
#
#         print("\n[2/4] 读取飞书表格数据...")
#         feishu.switch_to_feishu()
#         tracking_col, amount_col = feishu.find_columns(COL_TRACKING, COL_AMOUNT)
#         print(f"  「{COL_TRACKING}」= 第 {tracking_col + 1} 列")
#         print(f"  「{COL_AMOUNT}」= 第 {amount_col + 1} 列")
#
#         rows = feishu.read_all_rows(tracking_col, amount_col)
#         print(f"  共读取 {len(rows)} 行数据")
#
#         tasks = []
#         skipped_filled = 0
#         skipped_progress = 0
#         for row_num, tn, amt in rows:
#             if tn in completed_set:
#                 skipped_progress += 1
#                 continue
#             if SKIP_FILLED and amt:
#                 skipped_filled += 1
#                 continue
#             tasks.append((row_num, tn))
#
#         if MAX_ROWS > 0:
#             tasks = tasks[:MAX_ROWS]
#
#         print(f"  进度跳过: {skipped_progress}")
#         print(f"  已填金额: {skipped_filled}")
#         print(f"  待处理: {len(tasks)}")
#
#         if not tasks:
#             print("\n没有需要处理的单号 ✓")
#             return 0
#
#         print(f"\n[3/4] 开始批量查询...（共 {len(tasks)} 条，每次10条）\n")
#         success = 0
#         fail = 0
#
#         batch_size = 10
#         for batch_idx in range(0, len(tasks), batch_size):
#             batch = tasks[batch_idx:batch_idx + batch_size]
#             print(f"{'─' * 50}")
#             print(f"[批次 {batch_idx // batch_size + 1}/{(len(tasks) + batch_size - 1) // batch_size}] "
#                   f"共 {len(batch)} 条")
#
#             tracking_numbers = [tn for _, tn in batch]
#
#             try:
#                 results = sf_client.query_amounts_batch(tracking_numbers)
#             except Exception as exc:
#                 print(f"  ✗ 批量查询异常: {exc}")
#                 for _, tn in batch:
#                     fail += 1
#                     save_failed(tn, f"查询异常: {exc}")
#                 continue
#
#             for row_num, tn in batch:
#                 amount = results.get(tn)
#                 print(f"  [{tn}] 飞书第 {row_num} 行")
#
#                 if not amount:
#                     fail += 1
#                     save_failed(tn, "未提取到「交易金额（元）」")
#                     print(f"    ✗ 未提取到金额")
#                     continue
#
#                 try:
#                     feishu.write_amount(row_num, amount_col, amount)
#                     save_progress(tn)
#                     success += 1
#                     print(f"    ✓ 已填写: {amount} 元")
#                 except Exception as exc:
#                     fail += 1
#                     save_failed(tn, f"写回飞书失败: {exc}")
#                     print(f"    ✗ 写回失败: {exc}")
#
#             if batch_idx + batch_size < len(tasks):
#                 time.sleep(QUERY_DELAY_SECONDS)
#
#         print(f"\n[4/4] {'=' * 50}")
#         print(f"执行完毕!")
#         print(f"  成功: {success}")
#         print(f"  失败: {fail}")
#         print(f"  已有金额(跳过): {skipped_filled}")
#         print(f"  进度跳过: {skipped_progress}")
#         print(f"  进度文件: .sf_progress.json")
#         print(f"  失败记录: .sf_failed.json")
#         print("=" * 60)
#         return 0 if fail == 0 else 2
#
#     except KeyboardInterrupt:
#         print("\n用户中断")
#         return 130
#     except Exception as exc:
#         print(f"\n程序出错: {exc}")
#         import traceback
#         traceback.print_exc()
#         return 1
#
#
# if __name__ == "__main__":
#     sys.exit(main())