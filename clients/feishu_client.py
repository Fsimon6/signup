"""飞书文档浏览器操作客户端 - GUI自动化版"""

from __future__ import annotations

import re
import time

import pyautogui
import pygetwindow as gw
import pyperclip

from config import (
    FEISHU_CELL_BOX_X,
    FEISHU_CELL_BOX_Y,
)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.15


class FeishuBrowserClient:
    """通过PyAutoGUI操作Chrome浏览器中的飞书文档。"""

    def __init__(self, tab_number: int = 1):
        self.tab_number = tab_number
        self.browser_window = None
        self._last_cell_ref = None
        self._last_amount_col = None       # 记录上次写入的行号，用于后续定位

    def find_browser_window(self):
        """查找Chrome浏览器窗口。"""
        windows = gw.getWindowsWithTitle("")
        for w in windows:
            if "Chrome" in w.title:
                self.browser_window = w
                return w
        return None

    def activate_window(self):
        """激活Chrome浏览器窗口。"""
        if not self.browser_window:
            self.find_browser_window()
        if self.browser_window:
            if self.browser_window.isMinimized:
                self.browser_window.restore()
            self.browser_window.activate()
            time.sleep(0.5)

    def switch_to_feishu(self):
        """切换到飞书文档标签页。"""
        self.activate_window()
        pyautogui.hotkey("ctrl", str(self.tab_number))
        time.sleep(1.0)

    def click_page_center(self):
        """点击页面中心位置。"""
        if self.browser_window:
            x = self.browser_window.left + self.browser_window.width // 2
            y = self.browser_window.top + self.browser_window.height // 3
            pyautogui.click(x, y)
        else:
            pyautogui.click()
        time.sleep(0.3)

    def copy_all_text(self) -> str:
        """全选并复制页面文本。"""
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.4)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.8)
        try:
            return pyperclip.paste() or ""
        except Exception:
            return ""

    def parse_table(self, text: str) -> list[list[str]]:
        """解析复制的表格文本为二维列表。"""
        lines = text.strip().split("\n")
        data = []
        for line in lines:
            cells = [c.strip() for c in line.split("\t")]
            if any(cells):
                data.append(cells)
        return data

    def find_columns(self, tracking_name: str, amount_name: str) -> tuple[int, int]:
        """通过文本识别查找列索引。"""
        print("  正在查找列位置...")
        self.click_page_center()
        time.sleep(0.5)

        text = self.copy_all_text()
        if not text:
            time.sleep(1)
            text = self.copy_all_text()

        table = self.parse_table(text)
        if not table:
            raise RuntimeError("无法读取表格数据")

        header = table[0]
        tracking_col = None
        amount_col = None

        for i, cell in enumerate(header):
            if tracking_name in cell:
                tracking_col = i
            if amount_name in cell:
                amount_col = i

        if tracking_col is None:
            raise RuntimeError(f"未找到「{tracking_name}」列")
        if amount_col is None:
            raise RuntimeError(f"未找到「{amount_name}」列")

        return tracking_col, amount_col

    def read_all_rows(self, tracking_col: int, amount_col: int) -> list[tuple[int, str, str]]:
        """读取所有行数据，返回 (行号, 单号, 金额)。"""
        self.click_page_center()
        time.sleep(0.5)

        text = self.copy_all_text()
        table = self.parse_table(text)

        if len(table) < 2:
            return []

        rows = []
        for row_num, cells in enumerate(table[1:], start=2):
            while len(cells) <= max(tracking_col, amount_col):
                cells.append("")

            tn = cells[tracking_col].strip()
            tn = self.normalize_tracking(tn)
            if not tn:
                continue

            amt = cells[amount_col].strip() if amount_col < len(cells) else ""
            rows.append((row_num, tn, amt))

        return rows


    # def write_amount(self, row_num: int, amount_col: int, amount: str) -> None:
    #     """通过方向键导航到指定单元格并写入金额。"""
    #     self.switch_to_feishu()
    #     time.sleep(1.0)
    #
    #     print(f"  [写回飞书] 行:{row_num}, 列索引:{amount_col}, 金额:{amount}")
    #
    #     # 确保表格焦点，退出可能的编辑状态
    #     pyautogui.press("escape")
    #     time.sleep(0.2)
    #     self.click_page_center()
    #     time.sleep(0.3)
    #
    #     # 回到 A1
    #     pyautogui.hotkey("ctrl", "home")
    #     time.sleep(0.5)
    #
    #     # 移动到目标列（amount_col 是列索引，如 11 表示 L 列）
    #     for _ in range(amount_col):
    #         pyautogui.press("right")
    #         time.sleep(0.01)
    #
    #     # 移动到目标行（第1行是标题，数据行从第2行开始）
    #     pyautogui.press("down", presses=row_num - 1, interval=0.04)
    #     time.sleep(0.3)
    #
    #     # 写入金额
    #     pyperclip.copy(str(amount))
    #     pyautogui.hotkey("ctrl", "v")
    #     time.sleep(0.3)
    #     pyautogui.press("enter")
    #     time.sleep(0.2)
    #     print(f"    ✓ 已填写: {amount} 元")

    def write_amount(self, row_num: int, amount_col: int, amount: str) -> None:
        """写入金额：首次方向键导航，后续通过定位框跳转到单元格后粘贴"""
        self.switch_to_feishu()
        time.sleep(1.0)

        col_letter = self._col_index_to_letter(amount_col)
        cell_ref = f"{col_letter}{row_num}"
        print(f"  [写回飞书] 单元格:{cell_ref}, 金额:{amount}")

        # 确保表格焦点，退出可能存在的编辑状态
        pyautogui.press("escape")
        time.sleep(0.2)
        self.click_page_center()
        time.sleep(0.3)

        # 判断是否需要重新导航（首次写入或列发生变化）
        if self._last_cell_ref is None or self._last_amount_col != amount_col:
            # 首次：用方向键从 A1 定位
            pyautogui.hotkey("ctrl", "home")
            time.sleep(0.5)
            for _ in range(amount_col):
                pyautogui.press("right")
                time.sleep(0.01)
            pyautogui.press("down", presses=row_num - 1, interval=0.04)
            time.sleep(0.3)
        else:
            # 后续：通过点击定位框输入地址跳转
            if FEISHU_CELL_BOX_X > 0 and FEISHU_CELL_BOX_Y > 0:
                # ① 点击定位框
                pyautogui.click(FEISHU_CELL_BOX_X, FEISHU_CELL_BOX_Y)
                time.sleep(0.3)
                # ② 全选原有地址
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.1)
                # ③ 输入新地址（如 L3）
                pyautogui.typewrite(cell_ref)
                time.sleep(0.2)
                # ④ 回车，焦点跳转到目标单元格
                pyautogui.press("enter")
                time.sleep(0.5)  # 等待页面响应，确保焦点已离开定位框
            else:
                # 未配置坐标时回退到方向键导航
                pyautogui.hotkey("ctrl", "home")
                time.sleep(0.5)
                for _ in range(amount_col):
                    pyautogui.press("right")
                    time.sleep(0.01)
                pyautogui.press("down", presses=row_num - 1, interval=0.04)
                time.sleep(0.3)

        # 粘贴金额（此时焦点已位于目标单元格）
        pyperclip.copy(str(amount))
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.2)

        # 记录本次写入信息
        self._last_cell_ref = cell_ref
        self._last_amount_col = amount_col

        print(f"    ✓ 已填写: {amount} 元")


    @staticmethod
    def normalize_tracking(value: str) -> str:
        """清理顺丰单号。"""
        cleaned = value.strip().replace(" ", "")
        m = re.search(r"(SF\d{10,}|SF\d+[A-Za-z0-9]+|\d{10,})", cleaned, re.IGNORECASE)
        return m.group(1).upper() if m else cleaned

    @staticmethod
    def _col_index_to_letter(index: int) -> str:
        """将列索引转换为字母（0->A, 1->B, 26->AA）。"""
        result = ""
        num = index + 1
        while num > 0:
            num, rem = divmod(num - 1, 26)
            result = chr(65 + rem) + result
        return result