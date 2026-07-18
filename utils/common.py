"""公共工具函数"""

from __future__ import annotations

import re
import time


def normalize_tracking(value: str) -> str:
    """清理单号，提取有效的单号格式。"""
    if not value:
        return ""
    cleaned = value.strip().replace(" ", "")
    m = re.search(r"(SF\d{10,}|SF\d+[A-Za-z0-9]+|\d{10,})", cleaned, re.IGNORECASE)
    return m.group(1).upper() if m else cleaned


def parse_amount(text: str) -> float | None:
    """解析金额字符串为浮点数。"""
    if not text:
        return None
    val = text.strip().replace(',', '').replace('¥', '').replace('￥', '')
    if re.match(r'^\d+\.?\d*$', val):
        return float(val)
    return None


def format_amount(amount: float | str, decimal_places: int = 2) -> str:
    """格式化金额为字符串。"""
    if isinstance(amount, str):
        amount = parse_amount(amount)
    if amount is None:
        return ""
    return f"{amount:.{decimal_places}f}"


def wait_for(seconds: float) -> None:
    """等待指定秒数。"""
    time.sleep(seconds)


def retry(func, max_retries: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """重试装饰器。"""
    def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except exceptions as exc:
                last_exception = exc
                if attempt < max_retries - 1:
                    wait_for(delay)
        raise last_exception
    return wrapper