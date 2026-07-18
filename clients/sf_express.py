"""顺丰查询页面 Selenium WebDriver 自动化客户端"""

from __future__ import annotations

import atexit
import os
import re
import subprocess
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from config import (
    SF_URL,
    SELENIUM_TIMEOUT,
    CHROME_USER_DATA_DIR,
    KEEP_BROWSER_OPEN,
    WAIT_FOR_USER,
)

PROJECT_DIR = Path(__file__).parent.parent
CHROME_DATA_DIR = PROJECT_DIR / "sf_browser_data"


def get_chrome_version() -> str | None:
    """获取 Chrome 浏览器版本号。"""
    import winreg

    registry_paths = [
        r"SOFTWARE\Google\Chrome\BLBeacon",
        r"SOFTWARE\Wow6432Node\Google\Chrome\BLBeacon",
    ]

    for reg_path in registry_paths:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ)
            version, _ = winreg.QueryValueEx(key, "version")
            winreg.CloseKey(key)
            return version
        except Exception:
            pass

        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_READ)
            version, _ = winreg.QueryValueEx(key, "version")
            winreg.CloseKey(key)
            return version
        except Exception:
            pass

    chrome_paths = [
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe"),
    ]
    for path in chrome_paths:
        if os.path.exists(path):
            try:
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                match = re.search(r"Chrome (\d+\.\d+\.\d+\.\d+)", result.stdout)
                if match:
                    return match.group(1)
            except Exception:
                continue

    return None


def find_chromedriver() -> str | None:
    """根据 Chrome 版本在 drivers/ 目录下查找匹配的 chromedriver。"""
    chrome_version = get_chrome_version()
    if not chrome_version:
        print("[警告] 无法获取 Chrome 版本号")
        return None

    major_version = chrome_version.split(".")[0]
    print(f"[调试] Chrome 版本: {chrome_version} (主版本: {major_version})")

    drivers_dir = PROJECT_DIR / "drivers"
    if not drivers_dir.exists():
        print(f"[警告] drivers 目录不存在: {drivers_dir}")
        return None

    driver_path = drivers_dir / major_version / "chromedriver.exe"
    if driver_path.exists():
        print(f"[✓] 找到匹配的 chromedriver: {driver_path}")
        return str(driver_path)

    print(f"[警告] 未找到版本 {major_version} 的 chromedriver，检查可用版本...")
    for version_dir in sorted(drivers_dir.iterdir()):
        if version_dir.is_dir():
            candidate = version_dir / "chromedriver.exe"
            if candidate.exists():
                print(f"  - 可用版本: {version_dir.name}")

    return None


class SFExpressBrowserClient:
    """通过 Selenium WebDriver 操作顺丰查询页面。

    接口兼容旧版 PyAutoGUI 实现：
    - __init__(tab_number) 接受但忽略 tab_number
    - query_amount(tracking_number) -> str | None
    """

    def __init__(self, tab_number: int = 2):
        # tab_number 保留用于接口兼容，Selenium 版本不需要
        self.tab_number = tab_number
        self.driver: webdriver.Chrome | None = None
        if not KEEP_BROWSER_OPEN:
            atexit.register(self.close)

    # ------------------------------------------------------------------
    # 浏览器生命周期
    # ------------------------------------------------------------------

    def _ensure_browser(self):
        """懒启动浏览器，首次调用时初始化。"""
        if self.driver is not None:
            return

        if not SF_URL:
            raise RuntimeError("SF_URL 未配置，请在 .env 中设置顺丰查询页面地址")

        print("[启动浏览器] 初始化 Selenium WebDriver...")

        CHROME_DATA_DIR.mkdir(parents=True, exist_ok=True)
        user_data_dir = CHROME_DATA_DIR / "user_data"
        cache_dir = str(CHROME_DATA_DIR / "cache")
        tmp_dir = str(CHROME_DATA_DIR / "tmp")
        os.makedirs(user_data_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)
        os.makedirs(tmp_dir, exist_ok=True)

        is_first_run = not self._has_profile_data(user_data_dir)

        # os.environ["TMP"] = tmp_dir
        # os.environ["TEMP"] = tmp_dir

        options = Options()

        options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument(f"--disk-cache-dir={cache_dir}")
        options.add_argument(f"--crash-dumps-dir={tmp_dir}")
        options.add_argument("--disable-features=VizDisplayCompositor")

        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        # options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        # service_args = [
        #     f"--tmpdir={tmp_dir}",
        # ]

        print(f"[调试] user-data-dir: {user_data_dir}")
        print(f"[调试] cache-dir: {cache_dir}")
        print(f"[调试] tmp-dir: {tmp_dir}")

        driver_path = find_chromedriver()

        try:
            if driver_path:
                print(f"[调试] 使用本地 chromedriver: {driver_path}")
                service = Service(driver_path)
            else:
                print("[调试] 使用 Selenium Manager 自动管理驱动...")
                service = Service()

            print("[调试] 创建 Service...")
            self.driver = webdriver.Chrome(
                service=service,
                options=options,
            )

            self.driver.maximize_window()
            print("[✓] Chrome 浏览器启动成功")

        except Exception as exc:
            print(f"[✗] 启动失败: {exc}")
            if driver_path:
                print("[调试] 尝试使用 Selenium Manager 回退方案...")
                try:
                    service = Service()
                    self.driver = webdriver.Chrome(service=service, options=options)
                    self.driver.maximize_window()
                    print("[✓] 使用 Selenium Manager 启动成功")
                except Exception as exc2:
                    raise RuntimeError(f"Chrome 启动失败: {exc}\nSelenium Manager 回退方案也失败: {exc2}")
            else:
                raise RuntimeError(f"Chrome 启动失败: {exc}")

        # chrome_version = get_chrome_version()
        # print(f"[调试] Chrome 浏览器版本: {chrome_version}")

        # try:
        #     from webdriver_manager.chrome import ChromeDriverManager
        #
        #     if chrome_version:
        #         print(f"[调试] 使用 webdriver_manager 下载 ChromeDriver {chrome_version}...")
        #         service = Service(ChromeDriverManager(driver_version=chrome_version).install(), service_args=service_args)
        #     else:
        #         print("[调试] 使用 webdriver_manager 自动检测版本...")
        #         service = Service(ChromeDriverManager().install(), service_args=service_args)
        #
        #     self.driver = webdriver.Chrome(service=service, options=options)
        #     self.driver.maximize_window()
        #     print("[✓] Chrome 浏览器启动成功")
        # except Exception as exc:
        #     print(f"[✗] webdriver_manager 方案失败: {exc}")
        #     print("  尝试使用内置 Selenium Manager...")
        #     try:
        #         service = Service(service_args=service_args)
        #         print("[调试] 正在启动 Chrome...")
        #         self.driver = webdriver.Chrome(service=service, options=options)
        #         self.driver.maximize_window()
        #         print("[✓] 使用内置 Selenium Manager 启动成功")
        #     except Exception as exc2:
        #         raise RuntimeError(f"Chrome 启动失败: {exc}\n备用方案失败: {exc2}\n请确保已安装 Chrome 浏览器且版本与 ChromeDriver 匹配")

        print(f"[打开顺丰页面] {SF_URL}")
        self.driver.get(SF_URL)

        if is_first_run:
            print("\n" + "=" * 60)
            print("⚠️  首次运行 - 需要手动登录")
            print("=" * 60)
            print("请在弹出的 Chrome 浏览器中：")
            print("  1. 登录顺丰账号")
            print("  2. 导航到查询运费的页面")
            print("  3. 确认页面已准备就绪")
            print("\n完成后，请返回终端按 Enter 键继续...")
            print("=" * 60)
            input()
            self._mark_login_done(user_data_dir)
            print("[✓] 已确认，继续自动执行...")
        else:
            print("[等待页面就绪] 等待输入框出现...")
            try:
                WebDriverWait(self.driver, 120).until(
                    EC.presence_of_element_located((By.ID, "searchForm_waybillNo"))
                )
            except Exception as exc:
                raise RuntimeError(f"等待输入框超时，请检查页面是否需要登录或 URL 是否正确: {exc}")
            print("[页面就绪] 输入框已出现")

            print()
            if WAIT_FOR_USER:
                print()
                print("=" * 60)
                print("请先完成以下操作：")
                print("1. 登录顺丰")
                print("2. 进入交易查询页面")
                print("3. 修改查询日期")
                print("4. 确认日期修改完成")
                print("=" * 60)

                input("全部完成后，请按 Enter 开始自动查询...")

    @staticmethod
    def _has_profile_data(user_data_dir: Path) -> bool:
        """检查是否已存在用户配置文件（判断是否首次运行）。"""
        login_marker = user_data_dir / ".login_done"
        if login_marker.exists():
            return True

        profile_dir = user_data_dir / "Default"
        if not profile_dir.exists():
            return False
        key_files = ["Cookies", "Login Data", "Preferences", "Web Data"]
        found = 0
        for key_file in key_files:
            if (profile_dir / key_file).exists():
                found += 1
        return found >= 2

    @staticmethod
    def _mark_login_done(user_data_dir: Path) -> None:
        """标记登录已完成。"""
        login_marker = user_data_dir / ".login_done"
        login_marker.touch()

    def close(self):
        """关闭浏览器。"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    # ------------------------------------------------------------------
    # 核心查询接口
    # ------------------------------------------------------------------

    def query_amount(self, tracking_number: str) -> str | None:
        """查询单个顺丰单号的交易金额（元）。

        Returns:
            成功: "27.20"
            失败: None
        """
        results = self.query_amounts_batch([tracking_number])
        return results.get(tracking_number)

    def query_amounts_batch(self, tracking_numbers: list[str]) -> dict[str, str]:
        """批量查询多个顺丰单号的交易金额（一次最多10个）。

        Args:
            tracking_numbers: 顺丰单号列表（最多10个）

        Returns:
            字典: {单号: 实付金额}
        """
        batch_size = min(len(tracking_numbers), 10)
        batch = tracking_numbers[:batch_size]
        print(f"\n[批量查询] {len(batch)} 个单号: {batch}")

        try:
            self._ensure_browser()
        except Exception as exc:
            print(f"  ✗ 浏览器启动失败: {exc}")
            return {}

        try:
            input_el = WebDriverWait(self.driver, SELENIUM_TIMEOUT).until(
                EC.presence_of_element_located((By.ID, "searchForm_waybillNo"))
            )
            print("  [✓] 找到输入框")

            input_el.click()

            input_el.send_keys(Keys.CONTROL, "a")

            input_el.send_keys(Keys.DELETE)

            input_text = "\n".join(batch)

            input_el.send_keys(input_text)

            print(f"  [输入单号] {input_text}")

            # ==========================
            # 关闭日期选择器
            # ==========================

            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ESCAPE)
                print("  [✓] 已关闭日期选择框")
            except Exception:
                pass

            btn = WebDriverWait(self.driver, SELENIUM_TIMEOUT).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.search-button"))
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                btn
            )

            self.driver.execute_script(
                "arguments[0].click();",
                btn
            )

            time.sleep(0.5)

            # print("  [✓] 已点击查询")
            #
            # print("  [等待旧数据清空]")
            #
            # def table_empty(driver):
            #     rows = driver.find_elements(
            #         By.CSS_SELECTOR,
            #         "tbody tr"
            #     )
            #
            #     return len(rows) == 0
            #
            # try:
            #     WebDriverWait(
            #         self.driver,
            #         10
            #     ).until(table_empty)
            #
            #     print("  [旧数据已清空]")
            #
            # except Exception:
            #     print("  [旧数据未清空，继续等待新结果]")
            #
            # WebDriverWait(
            #     self.driver,
            #     60
            # ).until(
            #     lambda d:
            #     len(
            #         d.find_elements(
            #             By.CSS_SELECTOR,
            #             "tbody tr"
            #         )
            #     ) > 0
            # )
            #
            # print("  [✓] 查询结果加载完成")

            print("  [✓] 已点击查询")

            # 直接等待查询结果出现（表格行数 > 0）
            print("  [等待查询结果...]")
            WebDriverWait(
                self.driver,
                60
            ).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "tbody tr")) > 0
            )
            print("  [✓] 查询结果加载完成")

            print("  [等待解析] 等待金额出现...")
            print("  [等待解析] 开始解析金额...")

            results = {}

            for i in range(3):

                print(f"\n===== 第 {i + 1} 次解析 =====")

                results = self._extract_all_amounts_from_dom(batch)

                if results:
                    print(f"[✓] 第 {i + 1} 次解析成功")

                    return results

                print("[×] 本次没有解析到金额")

                time.sleep(0.5)

            print("[✗] 连续20秒都没有解析到金额")

            input("浏览器保持打开，请检查页面后按Enter继续...")

            return {}


        except Exception as exc:

            print(f"  [✗ 查询异常] {exc}")

            print("=" * 60)

            print("浏览器保持打开，请检查顺丰页面。")

            print("检查内容：")

            print("1. 日期是否正确")

            print("2. 查询按钮是否真的点到了")

            print("3. 页面有没有数据")

            print("4. 金额有没有显示")

            print("=" * 60)

            input("检查完成后按 Enter 返回程序...")

            return {}

    # ------------------------------------------------------------------
    # DOM 金额提取
    # ------------------------------------------------------------------

    def _extract_amount_from_dom(self) -> str | None:
        """从 DOM 中提取「交易金额(元)」的值。"""
        results = self._extract_all_amounts_from_dom([])
        return next(iter(results.values()), None)

    def _extract_all_amounts_from_dom(self, tracking_numbers: list[str]) -> dict[str, str]:
        """从 DOM 中提取所有单号的金额，处理金额类型（扣款、优惠券返款）。

        处理逻辑：
        - 同一单号可能有多个记录（扣款、优惠券返款）
        - 实付金额 = 扣款金额 - 优惠券返款金额
        """
        if not self.driver:
            return {}

        rows_data = self._extract_all_rows_data()
        if not rows_data:
            print("  [调试] 当前DOM没有解析出任何数据")

            print(self.driver.page_source[:5000])

            return {}

        amount_map = {}
        for row in rows_data:
            tn = row.get('tracking', '').strip().upper()
            if not tn:
                continue

            if tracking_numbers and tn not in [t.upper() for t in tracking_numbers]:
                continue

            amount_map.setdefault(tn, {'deduction': 0, 'coupon': 0})

            amount = self._parse_amount(row.get('amount', ''))
            if amount is None:
                continue

            row_type = row.get('type', '').strip()
            if '优惠券返款' in row_type:
                amount_map[tn]['coupon'] += amount
            else:
                amount_map[tn]['deduction'] += amount

        results = {}
        for tn, amounts in amount_map.items():
            actual = amounts['deduction'] - amounts['coupon']
            if actual > 0:
                results[tn] = f"{actual:.2f}"
                print(f"    [{tn}] 扣款: {amounts['deduction']:.2f}, 优惠券返款: {amounts['coupon']:.2f}, 实付: {results[tn]}")
            else:
                results[tn] = f"{amounts['deduction']:.2f}"
                print(f"    [{tn}] 扣款: {amounts['deduction']:.2f}, 优惠券返款: {amounts['coupon']:.2f}, 实付: {results[tn]}")

        return results

    def _extract_all_rows_data(self) -> list[dict]:
        """提取顺丰交易表真实数据"""

        rows = []

        try:
            data_rows = self.driver.find_elements(
                By.CSS_SELECTOR,
                "tbody tr"
            )

            # print("\n" + "=" * 80)
            # print(f"[调试] 找到 {len(data_rows)} 行数据")

            for row_index, row in enumerate(data_rows, start=1):
                cells = row.find_elements(By.TAG_NAME, "td")
                values = [
                    cell.text.strip()
                    for cell in cells
                ]
                # print(f"\n------ 第 {row_index} 行 ------")
                #
                # for i, v in enumerate(values):
                #     print(f"第{i}列：{repr(v)}")
                #
                # # ===============================
                # # 过滤空白虚拟行
                # # ===============================

                if len(values) < 6:
                    continue

                # 第一列必须是序号
                if not values[0].isdigit():
                    continue

                # 顺丰号必须存在
                tracking = values[4]

                if not tracking.startswith("SF"):
                    continue

                row_data = {

                    # 第3列：扣款/优惠券返款
                    "type": values[3],
                    # 第4列：顺丰号
                    "tracking": tracking,
                    # 第5列：金额
                    "amount": values[5],
                }

                rows.append(row_data)

            print("=" * 80)

        except Exception as exc:
            print(
                f"[调试] 提取表格失败: {exc}"
            )

        print(
            f"[调试] 有效交易记录: {len(rows)} 条"
        )

        if not rows:
            try:
                all_divs = self.driver.find_elements(By.TAG_NAME, 'div')
                current_row = {}
                for div in all_divs:
                    text = div.text.strip()
                    if text in ['扣款', '优惠券返款']:
                        if current_row:
                            rows.append(current_row)
                        current_row = {'type': text}
                    elif text.startswith('SF') or (text.isdigit() and len(text) >= 10):
                        if 'tracking' not in current_row:
                            current_row['tracking'] = text
                    elif re.match(r'^\d+\.?\d*$', text):
                        if 'amount' not in current_row:
                            current_row['amount'] = text
                if current_row:
                    rows.append(current_row)
            except Exception:
                pass

        print("=" * 80 + "\n")

        return rows

    def _parse_amount(self, text: str) -> float | None:
        """解析金额字符串为浮点数。"""
        val = text.strip().replace(',', '').replace('¥', '').replace('￥', '')
        if re.match(r'^\d+\.?\d*$', val):
            return float(val)
        return None

    def _extract_amount_strategy1(self) -> str | None:
        """策略1: 标准 th/td 表格结构。

        查找包含「交易金额」的表头，获取列索引，再提取数据行对应列的值。
        """
        try:
            headers = self.driver.find_elements(By.TAG_NAME, 'th')
            col_index = -1
            for i, header in enumerate(headers):
                header_text = header.text.strip()
                if '交易金额' in header_text:
                    col_index = i
                    break

            if col_index == -1:
                return None

            rows = self.driver.find_elements(By.CSS_SELECTOR, 'tbody tr')
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, 'td')
                if col_index < len(cells):
                    text = cells[col_index].text.strip()
                    if text and text != '--' and text != '':
                        return self._clean_amount(text)
        except Exception:
            pass
        return None

    def _extract_amount_strategy2(self) -> str | None:
        """策略2: 通过 div 文本定位表头。

        查找文本为「交易金额(元)」的 div，定位其所属单元格，计算列索引后提取数据。
        """
        try:
            all_divs = self.driver.find_elements(By.TAG_NAME, 'div')
            for div in all_divs:
                text = div.text.strip()
                if text == '交易金额(元)' or text == '交易金额（元）':
                    header_cell = self._find_closest_header_cell(div)
                    if not header_cell:
                        continue

                    col_index = self._count_previous_siblings(header_cell)

                    table = self._find_closest_table(header_cell)
                    if not table:
                        continue

                    data_rows = table.find_elements(By.CSS_SELECTOR, 'tbody tr')
                    for row in data_rows:
                        cells = row.find_elements(By.TAG_NAME, 'td')
                        if col_index < len(cells):
                            val = cells[col_index].text.strip()
                            if val and val != '--' and val != '':
                                return self._clean_amount(val)
        except Exception:
            pass
        return None

    def _find_closest_header_cell(self, element) -> webdriver.remote.webelement.WebElement | None:
        """查找元素最近的表头单元格（th 或带 cell 类的元素）。"""
        try:
            for tag in ['th', '[class*="cell"]']:
                try:
                    return element.find_element(By.XPATH, f'./ancestor-or-self::{tag}')
                except Exception:
                    continue
            return element.find_element(By.XPATH, './parent::*')
        except Exception:
            return None

    def _find_closest_table(self, element) -> webdriver.remote.webelement.WebElement | None:
        """查找元素最近的 table 祖先。"""
        try:
            return element.find_element(By.XPATH, './ancestor::table')
        except Exception:
            return None

    def _count_previous_siblings(self, element) -> int:
        """计算元素的前兄弟元素数量（用于确定列索引）。"""
        try:
            siblings = element.find_elements(By.XPATH, './preceding-sibling::*')
            return len(siblings)
        except Exception:
            return 0

    def _clean_amount(self, text: str) -> str | None:
        """清理金额文本，去除货币符号和千分位分隔符。"""
        val = text.strip().replace(',', '').replace('¥', '').replace('￥', '')
        if re.match(r'^\d+\.?\d*$', val):
            return f"{float(val):.2f}"
        return None
