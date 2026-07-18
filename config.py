"""配置项，优先从环境变量读取。"""

import os

from dotenv import load_dotenv

load_dotenv()

COL_TRACKING = "顺丰号"
COL_AMOUNT = "实付顺丰邮费"

FEISHU_TAB_NUMBER = int(os.getenv("FEISHU_TAB_NUMBER", "1"))
FEISHU_DAILY_TAB_NUMBER = int(os.getenv("FEISHU_DAILY_TAB_NUMBER", "3"))

MAX_ROWS = int(os.getenv("MAX_ROWS", "0"))
SKIP_FILLED = os.getenv("SKIP_FILLED", "true").lower() in ("1", "true", "yes")

FEISHU_CELL_BOX_X = int(os.getenv("FEISHU_CELL_BOX_X", "0"))
FEISHU_CELL_BOX_Y = int(os.getenv("FEISHU_CELL_BOX_Y", "0"))
