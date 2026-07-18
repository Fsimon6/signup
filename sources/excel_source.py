"""Excel数据来源 - 从Excel文件读取订单数据"""

from __future__ import annotations

from typing import List, Dict, Any
from pathlib import Path

from clients.excel_client import ExcelClient
from utils.data_models import OrderData


class ExcelSource:
    """Excel数据来源 - 将Excel数据转换为统一数据模型"""

    COLUMN_MAPPING = {
        "order_channel": "Order Channel",
        "order_id": "Order ID",
        "buyer_nickname": "Buyer Nickname",
        "product_name": "Product Name",
        "seller_sku": "Seller SKU",
        "sku_subtotal_after_discount": "SKU Subtotal After Discount",
        "tracking_id": "Tracking ID",
        "shipping_fee_after_discount": "Shipping Fee After Discount",
        "order_amount": "Order Amount",
    }

    SHOP_MAPPING = [
        (("1店", "一店"), "Pine Linen"),
        (("2店", "二店"), "Blinkora"),
        (("3店", "三店"), "Vaynora"),
        (("4店", "四店"), "Hollow Unit"),
        (("5店", "五店"), "OSMOO Shop"),
    ]

    def __init__(self, file_path: str | Path | None = None):
        if file_path is None:
            file_path = ExcelClient.find_latest_excel("excel_source")
        self.file_path = Path(file_path) if file_path else None
        self.client = None

    def open(self):
        """打开Excel文件"""
        if not self.file_path:
            raise FileNotFoundError("未找到Excel文件")
        self.client = ExcelClient(self.file_path)
        self.client.open()

    def read_all_data(self) -> List[Dict[str, Any]]:
        """读取所有列数据，返回列表形式"""
        if not self.client:
            self.open()

        result = []
        row_count = self.client.get_row_count()

        for col_key, excel_col_name in self.COLUMN_MAPPING.items():
            try:
                values = self.client.read_column(excel_col_name)
            except ValueError:
                values = [None] * row_count
            result.append({
                "column_key": col_key,
                "excel_column": excel_col_name,
                "values": values,
            })

        return result

    def read_as_order_data(self) -> List[OrderData]:
        """读取数据并转换为统一的OrderData列表"""
        if not self.client:
            self.open()

        data_map = {}
        for col_key, excel_col_name in self.COLUMN_MAPPING.items():
            try:
                data_map[col_key] = self.client.read_column(excel_col_name)
            except ValueError:
                data_map[col_key] = []

        row_count = max(len(v) for v in data_map.values())
        order_list = []

        for i in range(row_count):
            order_data = OrderData(
                order_number=str(data_map.get("order_id", [None])[i] or ""),
                buyer_nickname=str(data_map.get("buyer_nickname", [None])[i] or ""),
                tracking_number=str(data_map.get("tracking_id", [None])[i] or ""),
                raw_data={
                    "order_channel": data_map.get("order_channel", [None])[i],
                    "product_name": data_map.get("product_name", [None])[i],
                    "sku_subtotal_after_discount": data_map.get("sku_subtotal_after_discount", [None])[i],
                    "shipping_fee_after_discount": data_map.get("shipping_fee_after_discount", [None])[i],
                    "order_amount": data_map.get("order_amount", [None])[i],
                }
            )
            order_list.append(order_data)

        return order_list

    def get_row_count(self) -> int:
        """获取数据行数"""
        if not self.client:
            self.open()
        return self.client.get_row_count()

    def get_shop_name(self) -> str:
        """根据文件名获取店铺名称"""
        if not self.file_path:
            return ""
        
        file_name = self.file_path.name
        
        for patterns, shop_name in self.SHOP_MAPPING:
            if any(pattern in file_name for pattern in patterns):
                return shop_name
        
        return ""

    def extract_session_number(self, product_name: str) -> str:
        """从产品名称中提取场次编号
        
        规则：提取产品名称中每个英文单词后的数字，返回"第几场"格式
        例如："Squishy Toy 1" → "第一场"，"Product A 3" → "第三场"
        """
        if not product_name:
            return ""
        
        import re
        product_name = str(product_name)
        matches = re.findall(r'[A-Za-z]+\s*(\d+)', product_name)
        
        if matches:
            num = int(matches[-1])
            return f"第{num}场"
        return ""

    def close(self):
        """关闭Excel文件"""
        if self.client:
            self.client.close()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()