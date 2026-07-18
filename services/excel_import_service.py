"""Excel数据导入服务 - 读取Excel并写入飞书表格"""

from __future__ import annotations

import pyperclip
import pyautogui
import time
from typing import List, Dict

from clients.feishu_client import FeishuBrowserClient
from config import FEISHU_TAB_NUMBER
from sources.excel_source import ExcelSource


class ExcelImportService:
    """Excel数据导入服务"""

    FEISHU_COLUMN_MAPPING = [
        {"excel_col": "Order Channel", "feishu_col": "直播or商品卡", "transform": True},
        {"excel_col": "Order ID", "feishu_col": "订单号", "transform": False},
        {"excel_col": "Buyer Nickname", "feishu_col": "顾客名", "transform": False},
        {"excel_col": "Product Name", "feishu_col": "产品", "transform": False},
        {"excel_col": "Seller SKU", "feishu_col": "直播序号", "transform": False},
        {"excel_col": "SKU Subtotal After Discount", "feishu_col": "拍卖实付（$）", "transform": False},
        {"excel_col": "Tracking ID", "feishu_col": "顺丰号", "transform": False},
        {"excel_col": "Shipping Fee After Discount", "feishu_col": "平台邮费（$）", "transform": False},
        {"excel_col": "Order Amount", "feishu_col": "顾客总实付（$）", "transform": False},
        {"excel_col": "_shop_", "feishu_col": "店铺", "transform": False},
        {"excel_col": "_session_", "feishu_col": "场次", "transform": False},
    ]

    def __init__(self):
        self.feishu = FeishuBrowserClient(tab_number=FEISHU_TAB_NUMBER)
        self.excel_source = ExcelSource()

    def transform_order_channel(self, value) -> str:
        """转换Order Channel列：LIVE->直播，其他->商品卡"""
        if value is None:
            return ""
        val = str(value).strip().upper()
        return "直播" if val == "LIVE" else "商品卡"

    def transform_column(self, values: List, transform: bool) -> List[str]:
        """根据规则转换列数据"""
        if transform:
            return [self.transform_order_channel(v) for v in values]
        return [str(v) if v is not None else "" for v in values]

    def copy_column_to_clipboard(self, values: List[str]) -> None:
        """将整列数据复制到剪贴板，每行一个值"""
        text = "\n".join(values)
        pyperclip.copy(text)
        time.sleep(0.3)

    def paste_to_feishu_column(self, column_name: str, column_index: int) -> None:
        """定位到飞书表格指定列并粘贴数据"""
        print(f"  定位到「{column_name}」列 (索引: {column_index})")

        pyautogui.hotkey("ctrl", "home")
        time.sleep(0.5)

        for _ in range(column_index):
            pyautogui.press("right")
            time.sleep(0.01)

        pyautogui.press("down")
        time.sleep(0.3)

        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.5)

        print(f"  ✓ 已粘贴到「{column_name}」列")

    def get_all_column_indices(self) -> Dict[str, int]:
        """一次性获取所有飞书表格列索引"""
        print("[获取飞书表格列索引]")
        self.feishu.click_page_center()
        time.sleep(0.5)

        text = self.feishu.copy_all_text()
        table = self.feishu.parse_table(text)

        if not table:
            raise RuntimeError("无法读取表格数据")

        header = table[0]
        col_indices = {}

        for i, cell in enumerate(header):
            col_indices[cell.strip()] = i
            print(f"  列「{cell.strip()}」= 索引 {i}")

        return col_indices

    def run(self) -> int:
        """执行完整的Excel导入流程"""
        print("=" * 60)
        print("Excel数据导入 - 批量写入飞书表格")
        print("=" * 60)
        print(f"\n飞书文档: 标签页 {FEISHU_TAB_NUMBER}")
        print(f"Excel文件: {self.excel_source.file_path.name if self.excel_source.file_path else '未找到'}")
        print()

        print("[1/4] 查找Chrome浏览器窗口...")
        browser = self.feishu.find_browser_window()
        if not browser:
            print("错误：未找到Chrome浏览器窗口，请确保Chrome已打开")
            return 1
        print(f"  找到: {browser.title[:60]}")

        print("\n[2/4] 读取Excel数据...")
        try:
            with self.excel_source as source:
                print(f"  文件: {source.file_path.name}")
                row_count = source.get_row_count()
                print(f"  数据行数: {row_count}")

                data = source.read_all_data()
                print(f"  已读取 {len(data)} 列")

                print("\n[3/4] 获取飞书表格列索引...")
                self.feishu.switch_to_feishu()
                time.sleep(1.0)
                feishu_col_indices = self.get_all_column_indices()

                print("\n[4/4] 写入飞书表格...")
                shop_name = source.get_shop_name()
                print(f"  店铺名称: {shop_name}")

                for col_info in self.FEISHU_COLUMN_MAPPING:
                    excel_col_name = col_info["excel_col"]
                    feishu_col_name = col_info["feishu_col"]
                    transform = col_info["transform"]

                    print(f"\n{'─' * 40}")
                    print(f"处理: {excel_col_name} → {feishu_col_name}")

                    if excel_col_name == "_shop_":
                        if not shop_name:
                            print(f"  ✗ 无法从文件名识别店铺")
                            continue
                        values = [shop_name] * row_count
                        transformed_values = values
                    elif excel_col_name == "_session_":
                        product_col_data = next((d for d in data if d["excel_column"] == "Product Name"), None)
                        if not product_col_data:
                            print(f"  ✗ Excel中未找到列: Product Name")
                            continue
                        values = [source.extract_session_number(p) for p in product_col_data["values"]]
                        transformed_values = values
                    else:
                        col_data = next((d for d in data if d["excel_column"] == excel_col_name), None)
                        if not col_data:
                            print(f"  ✗ Excel中未找到列: {excel_col_name}")
                            continue

                        values = col_data["values"]
                        transformed_values = self.transform_column(values, transform)

                    feishu_col_idx = feishu_col_indices.get(feishu_col_name)
                    if feishu_col_idx is None:
                        print(f"  ✗ 飞书中未找到列: {feishu_col_name}")
                        continue

                    print(f"  数据量: {len(transformed_values)} 行")

                    if transform:
                        live_count = sum(1 for v in transformed_values if v == "直播")
                        card_count = sum(1 for v in transformed_values if v == "商品卡")
                        print(f"  转换结果: 直播={live_count}, 商品卡={card_count}")

                    if excel_col_name == "_shop_":
                        print(f"  店铺值: {shop_name}")

                    self.copy_column_to_clipboard(transformed_values)
                    self.paste_to_feishu_column(feishu_col_name, feishu_col_idx)

                print("\n" + "=" * 60)
                print("导入完成!")
                print("=" * 60)

        except FileNotFoundError as exc:
            print(f"\n错误：{exc}")
            return 1
        except Exception as exc:
            print(f"\n程序出错: {exc}")
            import traceback
            traceback.print_exc()
            return 1

        return 0