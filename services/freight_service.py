"""运费查询服务 - 协调飞书读取、顺丰查询、飞书写入"""

from __future__ import annotations

import time
from typing import List, Tuple, Dict

import pyautogui
import pyperclip

from clients.feishu_client import FeishuBrowserClient
from config import (
    COL_AMOUNT,
    COL_TRACKING,
    FEISHU_TAB_NUMBER,
    MAX_ROWS,
    SKIP_FILLED,
)
from sources.sf_source import SFSource
from utils.progress import load_progress, save_progress, save_failed
from utils.data_models import OrderData


class FreightService:
    """顺丰运费查询服务"""

    def __init__(self):
        self.feishu = FeishuBrowserClient(tab_number=FEISHU_TAB_NUMBER)
        self.sf_source = SFSource()
        self.completed_set = load_progress()

    def read_all_data(self) -> Tuple[List[Tuple[int, str, str]], int, int]:
        """读取飞书表格中的所有数据（包括已填充金额的行）"""
        print("[读取飞书表格]")
        self.feishu.switch_to_feishu()
        tracking_col, amount_col = self.feishu.find_columns(COL_TRACKING, COL_AMOUNT)
        print(f"  「{COL_TRACKING}」= 第 {tracking_col + 1} 列")
        print(f"  「{COL_AMOUNT}」= 第 {amount_col + 1} 列")

        rows = self.feishu.read_all_rows(tracking_col, amount_col)
        print(f"  共读取 {len(rows)} 行数据")

        return rows, amount_col, tracking_col

    def process_all_rows_batch(self, rows: List[Tuple[int, str, str]]) -> Tuple[List[str], int, int, int]:
        """批量处理所有行，生成金额列表
        
        金额计算逻辑：
        - 如果一个单号出现多次，用总金额除以出现次数，平均分到每一行
        - 已完成或已有金额的行跳过
        """
        from collections import Counter

        tn_counter = Counter()
        for row_num, tn, existing_amount in rows:
            if tn and tn not in self.completed_set:
                if not (SKIP_FILLED and existing_amount):
                    tn_counter[tn] += 1

        results = []
        success = 0
        fail = 0
        skipped = 0

        for row_num, tn, existing_amount in rows:
            if not tn:
                results.append("")
                continue

            if tn in self.completed_set:
                results.append(existing_amount)
                skipped += 1
                continue

            if SKIP_FILLED and existing_amount:
                results.append(existing_amount)
                skipped += 1
                continue

            count = tn_counter.get(tn, 1)

            try:
                order_data = self.sf_source.query_freight(tn)
            except Exception as exc:
                print(f"  ✗ [{tn}] 查询异常: {exc}")
                save_failed(tn, f"查询异常: {exc}")
                results.append("")
                fail += 1
                continue

            if not order_data or not order_data.freight_amount:
                print(f"  ✗ [{tn}] 未提取到金额")
                save_failed(tn, "未提取到金额")
                results.append("")
                fail += 1
                continue

            try:
                total_amount = float(order_data.freight_amount)
            except ValueError:
                print(f"  ✗ [{tn}] 金额格式错误: {order_data.freight_amount}")
                save_failed(tn, f"金额格式错误: {order_data.freight_amount}")
                results.append("")
                fail += 1
                continue

            per_amount = round(total_amount / count, 2)
            amount_str = f"{per_amount:.2f}"

            if count > 1:
                print(f"  ✓ [{tn}] 总金额: {total_amount:.2f}，{count}行均分: {amount_str}")

            results.append(amount_str)
            save_progress(tn)
            success += 1

        return results, success, fail, skipped

    def write_column_batch(self, column_index: int, values: List[str]):
        """批量写入整列数据"""
        print("\n[写入飞书表格]")
        print(f"  定位到第 {column_index + 1} 列...")

        self.feishu.switch_to_feishu()
        time.sleep(0.5)

        pyautogui.press("escape")
        time.sleep(0.2)
        self.feishu.click_page_center()
        time.sleep(0.3)

        pyautogui.hotkey("ctrl", "home")
        time.sleep(0.5)

        for _ in range(column_index):
            pyautogui.press("right")
            time.sleep(0.01)
        pyautogui.press("down", presses=1, interval=0.04)
        time.sleep(0.3)

        print("  复制数据到剪贴板...")
        text = "\n".join(values)
        pyperclip.copy(text)
        time.sleep(0.3)

        print("  粘贴数据...")
        pyautogui.hotkey("ctrl", "v")
        time.sleep(1.0)

        print("  ✓ 整列数据已粘贴")

    def run(self) -> Tuple[int, int, int]:
        """执行完整的运费查询流程（批量模式）"""
        print("=" * 60)
        print("顺丰运费自动查询 - CSV批量版")
        print("=" * 60)
        print(f"\n飞书文档: 标签页 {FEISHU_TAB_NUMBER}")
        print(f"数据来源: excel_source/客户账单.csv")
        print()

        if self.completed_set:
            print(f"断点续传：已完成 {len(self.completed_set)} 个单号\n")

        print("[1/4] 查找Chrome浏览器窗口...")
        browser = self.feishu.find_browser_window()
        if not browser:
            print("错误：未找到Chrome浏览器窗口，请确保Chrome已打开")
            return 0, 0, 0
        print(f"  找到: {browser.title[:60]}")

        print("\n[2/4] 读取飞书表格数据...")
        rows, amount_col, tracking_col = self.read_all_data()

        if not rows:
            print("\n没有数据可处理 ✓")
            return 0, 0, 0

        print(f"\n[3/4] 批量查询金额...（共 {len(rows)} 行）")
        results, success, fail, skipped = self.process_all_rows_batch(rows)

        print(f"\n  成功: {success}")
        print(f"  失败: {fail}")
        print(f"  跳过(已有/已完成): {skipped}")

        print(f"\n[4/4] 批量写入飞书表格...")
        self.write_column_batch(amount_col, results)

        print(f"\n{'=' * 50}")
        print(f"执行完毕!")
        print(f"  成功: {success}")
        print(f"  失败: {fail}")
        print(f"  跳过(已有/已完成): {skipped}")
        print(f"  进度文件: .sf_progress.json")
        print(f"  失败记录: .sf_failed.json")
        print("=" * 60)

        return success, fail, skipped
