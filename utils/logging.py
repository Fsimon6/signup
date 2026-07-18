"""日志工具"""

from __future__ import annotations

import logging
import os
from pathlib import Path


def setup_logging(name: str = "signup", log_level: str = "INFO") -> logging.Logger:
    """配置日志记录器。"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    if logger.handlers:
        return logger

    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(
        logs_dir / f"{name}.log",
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()