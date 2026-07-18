"""统一数据模型"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OrderData:
    """统一订单数据模型"""

    order_number: str = ""
    freight_amount: str = ""
    buyer_username: str = ""
    buyer_nickname: str = ""
    tracking_number: str = ""
    raw_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "订单号": self.order_number,
            "邮费": self.freight_amount,
            "Buyer Username": self.buyer_username,
            "Buyer Nickname": self.buyer_nickname,
            "顺丰号": self.tracking_number,
        }

    @classmethod
    def from_dict(cls, data: dict) -> OrderData:
        return cls(
            order_number=data.get("订单号", ""),
            freight_amount=data.get("邮费", ""),
            buyer_username=data.get("Buyer Username", ""),
            buyer_nickname=data.get("Buyer Nickname", ""),
            tracking_number=data.get("顺丰号", ""),
            raw_data=data,
        )