# Signup - 飞书表格数据自动化工具

从不同数据来源获取数据，并统一写入飞书表格指定列。

## 功能模块

### 模块一：顺丰运费查询 (`freight`)

从客户账单 CSV 文件读取运费数据，根据顺丰单号匹配后写入飞书表格。

**数据来源**：`excel_source/客户账单.csv`

**填充列**：
- 实付顺丰邮费

**金额计算逻辑**：
- 如果一个单号对应多条记录，将所有金额相加
- 如果一个单号在飞书表格中出现多次，总金额均分到每一行

### 模块二：Excel数据导入 (`excel`)

读取 Excel 文件数据，批量导入到飞书表格。

**数据来源**：`excel_source/*.xlsx`（自动选择最新文件）

**填充列**：

| 飞书列 | Excel来源列 | 特殊处理 |
|--------|------------|----------|
| 直播or商品卡 | Order Channel | LIVE→直播，其他→商品卡 |
| 订单号 | Order ID | 直接复制 |
| 顾客名 | Buyer Nickname | 直接复制 |
| 产品 | Product Name | 直接复制 |
| 直播序号 | Seller SKU | 直接复制 |
| 拍卖实付（$） | SKU Subtotal After Discount | 直接复制 |
| 顺丰号 | Tracking ID | 直接复制 |
| 平台邮费（$） | Shipping Fee After Discount | 直接复制 |
| 顾客总实付（$） | Order Amount | 直接复制 |
| 店铺 | 文件名识别 | 根据"X店"匹配店铺名 |
| 场次 | Product Name | 提取数字，转为"第几场" |

**店铺名称映射**：
- 1店/一店 → Pine Linen
- 2店/二店 → Blinkora
- 3店/三店 → Vaynora
- 4店/四店 → Hollow Unit
- 5店/五店 → OSMOO Shop

### 模块三：飞书表格同步 (`feishu_sync`)

从飞书"捏捏每日出单表"匹配款号，写入总表格。

**填充列**：
- 款号

**匹配逻辑**：
- 根据"买家昵称"查找，用"直播序号"辅助验证

## 快速开始

### 安装

```bash
pip install -r requirements.txt
```

### 配置

复制 `.env.example` 为 `.env`，填写配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `FEISHU_TAB_NUMBER` | `1` | 飞书文档所在的夸克浏览器标签页编号 |
| `FEISHU_DAILY_TAB_NUMBER` | `3` | 捏捏每日出单表所在标签页编号 |
| `MAX_ROWS` | `0` | 限制处理行数，0 表示全部 |
| `SKIP_FILLED` | `true` | 跳过已有金额的行 |

### 使用前准备

1. 打开夸克浏览器，登录飞书账号
2. 在标签页 1 打开飞书总表格（确保表格可见）
3. 如有需要，在标签页 3 打开"捏捏每日出单表"
4. 确保浏览器窗口未最小化且可见

### 运行

```bash
# 运行模块一：顺丰运费查询
python main.py freight

# 运行模块二：Excel数据导入
python main.py excel

# 运行模块三：飞书表格同步
python main.py feishu_sync

# 一键运行所有模块（模块二→模块一）
python main.py all
```

## 项目结构

```
signup/
├── main.py                 # 项目统一入口
├── config.py               # 配置项
├── clients/                # 外部交互层
│   ├── feishu_client.py    # 飞书浏览器客户端
│   ├── sf_express.py       # 顺丰Selenium客户端（保留）
│   └── excel_client.py     # Excel文件读取客户端
├── sources/                # 数据来源层
│   ├── sf_source.py        # 顺丰数据源（从CSV读取）
│   └── excel_source.py     # Excel数据源
├── services/               # 业务服务层
│   ├── freight_service.py  # 运费查询服务
│   ├── excel_import_service.py  # Excel导入服务
│   └── feishu_sync_service.py   # 飞书同步服务
├── utils/                  # 工具层
│   ├── data_models.py      # 统一数据模型
│   ├── common.py           # 公共函数
│   ├── logging.py          # 日志工具
│   └── progress.py         # 进度管理
├── excel_source/           # 用户数据目录（不上传）
├── logs/                   # 日志目录（不上传）
├── .env                    # 环境变量（不上传）
└── requirements.txt
```

## 架构设计

### 分层职责

| 层 | 职责 | 说明 |
|----|------|------|
| **clients** | 外部交互 | 飞书、Selenium、Excel 的操作封装 |
| **sources** | 数据读取 | 将不同来源的数据转换为统一格式 |
| **services** | 业务流程 | 流程编排、数据匹配、调用 clients 写入 |
| **utils** | 公共工具 | 日志、等待、异常处理、数据模型 |

### 数据模型

所有 Source 最终返回统一的 `OrderData` 对象：

```python
{
    "订单号": "...",
    "邮费": "...",
    "Buyer Username": "...",
    "Buyer Nickname": "...",
}
```

## 扩展指南

新增数据来源时，只需：

1. **新增 Client**（如需）：在 `clients/` 下创建新的客户端文件
2. **新增 Source**：在 `sources/` 下创建新的数据来源，返回统一的 `OrderData` 对象
3. **新增 Service**：在 `services/` 下创建业务服务，编排流程
4. **注册到 main.py**：在 `main.py` 中添加新模块的运行函数

## 故障排除

**未找到夸克浏览器窗口**: 确保夸克浏览器已打开，且窗口标题包含"夸克"

**未找到对应列**: 确保飞书表格表头包含正确的列名

**Excel文件读取失败**: 确保 Excel 文件放在 `excel_source/` 目录下

**粘贴失败**: 确保飞书表格页面处于可见状态，且没有被其他窗口遮挡

## 注意事项

- 三个模块不会同时运行，每次只执行其中一个
- 使用 pyautogui 进行 GUI 自动化，需要保持浏览器窗口可见
- 运行前请确保飞书表格已打开并处于可编辑状态
- `excel_source/` 目录包含用户数据，不会上传到 GitHub
