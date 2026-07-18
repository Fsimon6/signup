"""配置项，优先从环境变量读取。"""

import os

from dotenv import load_dotenv

load_dotenv()

COL_TRACKING = "顺丰号"
COL_AMOUNT = "实付顺丰邮费"

FEISHU_TAB_NUMBER = int(os.getenv("FEISHU_TAB_NUMBER", "1"))
SF_TAB_NUMBER = int(os.getenv("SF_TAB_NUMBER", "2"))
FEISHU_DAILY_TAB_NUMBER = int(os.getenv("FEISHU_DAILY_TAB_NUMBER", "3"))

QUERY_DELAY_SECONDS = float(os.getenv("QUERY_DELAY_SECONDS", "2"))
SF_RESULT_WAIT_SECONDS = float(os.getenv("SF_RESULT_WAIT_SECONDS", "3.5"))
MAX_ROWS = int(os.getenv("MAX_ROWS", "0"))
SKIP_FILLED = os.getenv("SKIP_FILLED", "true").lower() in ("1", "true", "yes")

# Selenium 配置
SF_URL = os.getenv("SF_URL", "")
SELENIUM_TIMEOUT = int(os.getenv("SELENIUM_TIMEOUT", "10"))
CHROME_USER_DATA_DIR = os.getenv("CHROME_USER_DATA_DIR", "")

# 调试配置
KEEP_BROWSER_OPEN = os.getenv("KEEP_BROWSER_OPEN", "true").lower() in ("1", "true", "yes")
WAIT_FOR_USER = os.getenv(
    "WAIT_FOR_USER",
    "true"
).lower() == "true"

FEISHU_CELL_BOX_X = int(os.getenv("FEISHU_CELL_BOX_X", "0"))
FEISHU_CELL_BOX_Y = int(os.getenv("FEISHU_CELL_BOX_Y", "0"))