"""飞书表格同步服务 - 从飞书表格A+B同步数据到飞书表格C"""

from __future__ import annotations

import re
import time
from typing import List, Dict, Any, Optional

from clients.feishu_client import FeishuBrowserClient
from config import FEISHU_TAB_NUMBER, FEISHU_DAILY_TAB_NUMBER


class FeishuSyncService:
    """飞书表格同步服务"""

    def __init__(self):
        self.master_client = FeishuBrowserClient(tab_number=FEISHU_TAB_NUMBER)
        self.daily_client = FeishuBrowserClient(tab_number=FEISHU_DAILY_TAB_NUMBER)

    def extract_session_number(self, product_name: str) -> str:
        """从产品名称中提取场次编号
        
        规则：提取产品名称中每个英文单词后的数字，返回"第几场"格式
        例如："Squishy Toy 1" → "第一场"，"Product A 3" → "第三场"
        """
        if not product_name:
            return ""
        
        product_name = str(product_name)
        matches = re.findall(r'[A-Za-z]+\s*(\d+)', product_name)
        
        if matches:
            num = int(matches[-1])
            return f"第{num}场"
        return ""

    def read_master_table(self) -> Dict[str, Any]:
        """读取总表格数据"""
        print("[读取总表格数据]")
        self.master_client.switch_to_feishu()
        time.sleep(1.0)
        self.master_client.click_page_center()
        time.sleep(0.5)

        text = self.master_client.copy_all_text()
        table = self.master_client.parse_table(text)

        if len(table) < 2:
            return {"header": [], "rows": []}

        header = table[0]
        col_indices = {}

        for i, cell in enumerate(header):
            col_indices[cell.strip()] = i
            print(f"  列「{cell.strip()}」= 索引 {i}")

        rows = []
        for row_num, cells in enumerate(table[1:], start=2):
            row_data = {"row_num": row_num}
            for col_name, col_idx in col_indices.items():
                value = cells[col_idx].strip() if col_idx < len(cells) else ""
                row_data[col_name] = value
            rows.append(row_data)

        print(f"  共读取 {len(rows)} 行数据")
        return {"header": header, "col_indices": col_indices, "rows": rows}

    def read_daily_order_table(self) -> Dict[str, Any]:
        """读取捏捏每日出单表数据"""
        print("[读取捏捏每日出单表数据]")
        self.daily_client.switch_to_feishu()
        time.sleep(1.0)
        self.daily_client.click_page_center()
        time.sleep(0.5)

        text = self.daily_client.copy_all_text()
        table = self.daily_client.parse_table(text)

        if len(table) < 2:
            return {"header": [], "rows": []}

        header = table[0]
        col_indices = {}

        for i, cell in enumerate(header):
            col_indices[cell.strip()] = i
            print(f"  列「{cell.strip()}」= 索引 {i}")

        rows = []
        for row_num, cells in enumerate(table[1:], start=2):
            row_data = {"row_num": row_num}
            for col_name, col_idx in col_indices.items():
                value = cells[col_idx].strip() if col_idx < len(cells) else ""
                row_data[col_name] = value
            rows.append(row_data)

        print(f"  共读取 {len(rows)} 行数据")
        return {"header": header, "col_indices": col_indices, "rows": rows}

    def find_sku_by_buyer_and_live_id(self, daily_data: Dict[str, Any], buyer_name: str, live_id: str) -> Optional[str]:
        """根据买家昵称和直播序号查找编码
        
        在捏捏每日出单表中搜索买家昵称，可能出现多个结果（左右两个区域），
        需要用直播序号交叉验证找到正确的编码。
        
        列映射关系：
        - 总表"款号" → 捏捏每日出单表"编码"
        - 总表"顾客名" → 捏捏每日出单表"买家昵称"
        """
        if not buyer_name or not live_id:
            return None

        candidates = []
        for row in daily_data["rows"]:
            row_buyer_name = row.get("买家昵称", "").strip()
            row_live_id = row.get("直播序号", "").strip()
            
            if row_buyer_name == buyer_name:
                candidates.append(row)

        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0].get("编码", "")

        for candidate in candidates:
            candidate_live_id = candidate.get("直播序号", "").strip()
            if candidate_live_id == live_id:
                return candidate.get("编码", "")

        return candidates[0].get("编码", "")

    def write_single_cell(self, row_num: int, col_index: int, value: str) -> None:
        """写入单个单元格"""
        self.master_client.switch_to_feishu()
        time.sleep(1.0)

        col_letter = self.master_client._col_index_to_letter(col_index)
        cell_ref = f"{col_letter}{row_num}"
        print(f"  写入单元格:{cell_ref}, 值:{value}")

        pyautogui.press("escape")
        time.sleep(0.2)
        self.master_client.click_page_center()
        time.sleep(0.3)

        pyautogui.hotkey("ctrl", "home")
        time.sleep(0.5)

        for _ in range(col_index):
            pyautogui.press("right")
            time.sleep(0.01)

        pyautogui.press("down", presses=row_num - 1, interval=0.04)
        time.sleep(0.3)

        pyperclip.copy(str(value))
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.2)

        print(f"    ✓ 已填写: {value}")

    def write_column_batch(self, col_index: int, values: List[str]) -> None:
        """批量写入整列数据"""
        self.master_client.switch_to_feishu()
        time.sleep(1.0)

        col_letter = self.master_client._col_index_to_letter(col_index)
        print(f"  批量写入列 {col_letter}，共 {len(values)} 行")

        text = "\n".join(values)
        pyperclip.copy(text)
        time.sleep(0.3)

        pyautogui.press("escape")
        time.sleep(0.2)
        self.master_client.click_page_center()
        time.sleep(0.3)

        pyautogui.hotkey("ctrl", "home")
        time.sleep(0.5)

        for _ in range(col_index):
            pyautogui.press("right")
            time.sleep(0.01)

        pyautogui.press("down")
        time.sleep(0.3)

        pyautogui.hotkey("ctrl", "v")
        time.sleep(1.0)

        print(f"    ✓ 批量写入完成")

    def run(self) -> int:
        """执行完整的飞书表格同步流程"""
        print("=" * 60)
        print("飞书表格同步 - 飞书表格A+B → 飞书表格C")
        print("=" * 60)
        print(f"\n总表格: 标签页 {FEISHU_TAB_NUMBER}")
        print(f"捏捏每日出单表: 标签页 {FEISHU_DAILY_TAB_NUMBER}")
        print()

        print("[1/4] 查找夸克浏览器窗口...")
        quark = self.master_client.find_quark_window()
        if not quark:
            print("错误：未找到夸克浏览器窗口，请确保夸克已打开")
            return 1
        print(f"  找到: {quark.title[:60]}")

        print("\n[2/4] 读取总表格数据...")
        master_data = self.read_master_table()
        if not master_data["rows"]:
            print("  总表格没有数据")
            return 1

        print("\n[3/4] 读取捏捏每日出单表数据...")
        daily_data = self.read_daily_order_table()
        if not daily_data["rows"]:
            print("  捏捏每日出单表没有数据")
            return 1

        print("\n[4/4] 批量写入场次列...")
        
        session_col_idx = master_data["col_indices"].get("场次")
        sku_col_idx = master_data["col_indices"].get("款号")
        live_id_col_idx = master_data["col_indices"].get("直播序号")
        buyer_col_idx = master_data["col_indices"].get("顾客名")
        product_col_idx = master_data["col_indices"].get("产品")

        if session_col_idx is None:
            print("  警告：未找到「场次」列")
        if sku_col_idx is None:
            print("  警告：未找到「款号」列")

        if session_col_idx is not None and product_col_idx is not None:
            session_values = []
            for row in master_data["rows"]:
                product_name = row.get("产品", "")
                session_number = self.extract_session_number(product_name)
                session_values.append(session_number)
            
            self.write_column_batch(session_col_idx, session_values)

        print("\n[5/5] 逐行写入款号列...")
        
        success_count = 0
        fail_count = 0

        for row in master_data["rows"]:
            row_num = row["row_num"]
            live_id = row.get("直播序号", "")
            buyer_name = row.get("顾客名", "")

            print(f"\n{'─' * 40}")
            print(f"处理行 {row_num}:")
            print(f"  直播序号: {live_id}")
            print(f"  顾客名: {buyer_name}")

            try:
                sku = self.find_sku_by_buyer_and_live_id(daily_data, buyer_name, live_id)
                print(f"  查得款号: {sku if sku else '未找到'}")

                if sku_col_idx is not None and sku:
                    self.write_single_cell(row_num, sku_col_idx, sku)

                success_count += 1
            except Exception as exc:
                print(f"  ✗ 处理失败: {exc}")
                fail_count += 1

        print("\n" + "=" * 60)
        print("同步完成!")
        print(f"  成功: {success_count}")
        print(f"  失败: {fail_count}")
        print("=" * 60)

        return 0


import pyautogui
import pyperclip