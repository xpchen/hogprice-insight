# 生猪价格洞察平台 — Windows 安装手册

> 适用系统：Windows 10 / Windows 11（64位）

---

## 目录

1. [环境要求](#1-环境要求)
2. [安装基础软件](#2-安装基础软件)
3. [获取项目文件](#3-获取项目文件)
4. [导入数据库](#4-导入数据库)
5. [配置并启动后端](#5-配置并启动后端)
6. [配置并启动前端](#6-配置并启动前端)
7. [验证安装](#7-验证安装)
8. [日常数据更新](#8-日常数据更新)
9. [常见问题](#9-常见问题)

---

## 1. 环境要求

| 软件 | 版本要求 | 说明 |
|------|---------|------|
| Python | **3.11 或以上** | 后端运行环境 |
| Node.js | **18 或以上** | 前端构建工具 |
| MySQL | **8.0** | 数据库 |
| Git | 任意版本 | 可选，用于克隆项目 |

---

## 2. 安装基础软件

### 2.1 安装 Python 3.11+

1. 访问 https://www.python.org/downloads/windows/
2. 下载 **Python 3.11.x** 的 Windows installer（64-bit）
3. 运行安装包，**务必勾选** `Add Python to PATH`
4. 点击 "Install Now" 完成安装

**验证：**
```cmd
python --version
```
应输出 `Python 3.11.x` 或更高版本。

---

### 2.2 安装 Node.js 18+

1. 访问 https://nodejs.org/zh-cn/
2. 下载 **LTS 版本**（18.x 或 20.x）
3. 运行安装包，全部默认选项，一路 Next

**验证：**
```cmd
node --version
npm --version
```

---

### 2.3 安装 MySQL 8.0

1. 访问 https://dev.mysql.com/downloads/installer/
2. 下载 **MySQL Installer for Windows**（推荐完整版 ~450MB）
3. 运行安装包，选择 **"Developer Default"** 或 **"Server only"**
4. 配置步骤中设置 root 密码为 `root`（或自定义，需与后续配置一致）
5. 完成安装

**验证：**
```cmd
mysql -uroot -proot -e "SELECT VERSION();"
```
应输出 MySQL 版本号。

> 💡 如果 mysql 命令不可用，将 MySQL 的 bin 目录加入 PATH：
> 通常路径为 `C:\Program Files\MySQL\MySQL Server 8.0\bin`

---

## 3. 获取项目文件

将项目文件夹 `hogprice-insight` 解压/复制到本地，例如：

```
D:\hogprice-insight\
├── backend\         ← 后端代码
├── frontend\        ← 前端代码
├── docs\            ← 文档与数据库备份
└── import_data.py   ← 数据导入脚本
```

> 本手册以 `D:\hogprice-insight` 为例，请根据实际路径替换。

---

## 4. 导入数据库

### 4.1 创建数据库并导入数据

打开命令提示符（CMD），执行以下命令：

```cmd
REM 导入数据库（包含建库、建表、全量数据）
mysql -uroot -proot < D:\hogprice-insight\docs\hogprice_v3_20260302.sql.gz
```

> 如果 mysql 无法识别 .gz 文件，先解压再导入：

```cmd
REM 方法一：使用 7-Zip 解压后导入
"C:\Program Files\7-Zip\7z.exe" e D:\hogprice-insight\docs\hogprice_v3_20260302.sql.gz -oD:\hogprice-insight\docs\
mysql -uroot -proot < D:\hogprice-insight\docs\hogprice_v3_20260302.sql

REM 方法二：PowerShell 解压
powershell -Command "& { Add-Type -Assembly 'System.IO.Compression.FileSystem'; [System.IO.Compression.GZipStream]::new([System.IO.File]::OpenRead('D:\hogprice-insight\docs\hogprice_v3_20260302.sql.gz'), [System.IO.Compression.CompressionMode]::Decompress) | ForEach-Object { $_ } }"
```

### 4.2 验证数据库

```cmd
mysql -uroot -proot hogprice_v3 -e "SELECT table_name, table_rows FROM information_schema.tables WHERE table_schema='hogprice_v3' ORDER BY table_rows DESC LIMIT 5;"
```

应看到 `fact_price_daily` 等表有数据。

### 4.3 初始化管理员账户

> ⚠️ **必须执行此步骤**，否则登录时会出现 401 错误。

先完成第 5.1 ~ 5.3 步创建并激活虚拟环境，再回来执行：

```cmd
cd D:\hogprice-insight\backend
env\Scripts\activate
python init_admin_user.py
```

看到以下输出表示成功：

```
✅ 初始化完成！
==================================================
默认登录账户：
  用户名: admin
  密码: Admin@123
==================================================
```

---

## 5. 配置并启动后端

### 5.1 进入后端目录

```cmd
cd D:\hogprice-insight\backend
```

### 5.2 创建 Python 虚拟环境

```cmd
python -m venv env
```

### 5.3 激活虚拟环境

```cmd
env\Scripts\activate
```

命令行提示符前会出现 `(env)` 表示激活成功。

### 5.4 安装依赖

```cmd
pip install -r requirements.txt
```

> ⏳ 首次安装约需 3-5 分钟，请耐心等待。

### 5.5 创建配置文件

在 `D:\hogprice-insight\backend\` 目录下新建 `.env` 文件，内容如下：

```env
QUICK_CHART_INTERNAL_SECRET=hogprice-internal-secret-2024
```

> 使用记事本创建：右键 → 新建 → 文本文档，将文件名改为 `.env`（注意去掉 `.txt` 后缀）

如果 MySQL 密码不是 `root`，还需要添加：

```env
DATABASE_URL=mysql+pymysql://root:你的密码@localhost:3306/hogprice_v3?charset=utf8mb4
```

### 5.6 启动后端服务

```cmd
REM 确保在 backend 目录且虚拟环境已激活
env\Scripts\activate
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

或直接双击运行已有的启动脚本：

```cmd
run.bat
```

> 注意：如果 `run.bat` 中的路径是 `D:\Workspace\hogprice-insight`，需要用文本编辑器打开修改为实际路径。

**看到以下输出说明后端启动成功：**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

访问 http://localhost:8000/health 应返回 `{"status":"ok"}`

---

## 6. 配置并启动前端

### 6.1 新开一个命令提示符窗口

```cmd
cd D:\hogprice-insight\frontend
```

### 6.2 安装前端依赖

```cmd
npm install
```

> ⏳ 首次安装约需 2-3 分钟。

### 6.3 启动前端开发服务器

```cmd
npm run dev
```

**看到以下输出说明前端启动成功：**
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://你的IP:5173/
```

---

## 7. 验证安装

打开浏览器访问 http://localhost:5173

默认登录账号：
- **用户名**：`admin`
- **密码**：`Admin@123`

登录后应能看到 Dashboard 页面，图表正常加载即表示安装成功。

---

## 8. 日常数据更新

每次有新 Excel 数据文件时，运行项目根目录的 `import_data.py` 脚本来更新数据并刷新缓存。

### 8.1 确保后端服务已启动

（参见第 5.6 节）

### 8.2 运行数据导入脚本

打开命令提示符（**不需要**激活后端虚拟环境）：

```cmd
cd D:\hogprice-insight

REM 增量导入（默认目录）
python import_data.py

REM 增量导入（指定数据文件夹）
python import_data.py D:\数据文件\生猪数据\

REM 全量导入（清空重建，慎用）
python import_data.py --mode bulk
```

脚本会自动完成：
1. ✅ 扫描并导入 9 个 Excel 数据文件（增量，只插入新数据）
2. ✅ 清除相关页面的 API 缓存
3. ✅ 预热 11 个关键接口缓存（需要后端运行中）

> **注意**：如果提示找不到模块，需要先激活虚拟环境：
> ```cmd
> D:\hogprice-insight\backend\env\Scripts\activate
> python import_data.py
> ```

---

## 9. 常见问题

### Q1：`python` 命令不存在
```
'python' 不是内部或外部命令
```
**解决**：重新安装 Python，安装时勾选 `Add Python to PATH`，或手动将 Python 目录加入系统 PATH。

---

### Q2：MySQL 连接失败
```
Can't connect to MySQL server on 'localhost'
```
**解决**：
1. 确认 MySQL 服务已启动：`Win + R` → `services.msc` → 找到 `MySQL80` → 启动
2. 确认密码正确，默认配置是 `root/root`
3. 如果密码不同，修改 `backend/.env` 中的 `DATABASE_URL`

---

### Q3：pip install 报错（SSL/网络问题）
**解决**：使用国内镜像源：
```cmd
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

### Q4：npm install 很慢
**解决**：使用淘宝镜像：
```cmd
npm install --registry=https://registry.npmmirror.com
```

---

### Q5：前端页面空白或接口报错
**原因**：后端未启动或端口被占用。

**检查**：
```cmd
curl http://localhost:8000/health
```
应返回 `{"status":"ok"}`，否则检查后端是否正常启动。

---

### Q6：端口 8000 或 5173 被占用
```cmd
REM 查找占用端口的进程
netstat -ano | findstr :8000
netstat -ano | findstr :5173

REM 根据 PID 结束进程（将 XXXX 替换为实际 PID）
taskkill /PID XXXX /F
```

---

### Q7：登录提示 401（用户名或密码错误）
**原因**：未执行管理员账户初始化步骤，数据库中没有用户数据。

**解决**：
```cmd
cd D:\hogprice-insight\backend
env\Scripts\activate
python init_admin_user.py
```

执行完成后重新用 `admin` / `Admin@123` 登录即可。

---

### Q8：import_data.py 预热失败（401 Unauthorized）
**原因**：`backend/.env` 文件未创建或后端未重启加载配置。

**解决**：
1. 确认 `backend/.env` 文件存在且包含 `QUICK_CHART_INTERNAL_SECRET=hogprice-internal-secret-2024`
2. 重启后端服务
3. 再次运行 `python import_data.py`

---

### Q9：run.bat 路径错误
用文本编辑器打开 `backend\run.bat`，将第 6 行的路径：
```bat
set "PROJ=D:\Workspace\hogprice-insight\backend"
```
修改为实际路径，例如：
```bat
set "PROJ=D:\hogprice-insight\backend"
```

---

## 快速启动（每日使用）

安装完成后，每次使用只需：

**第一步：启动后端**（保持此窗口不关闭）
```cmd
cd D:\hogprice-insight\backend
env\Scripts\activate
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**第二步：启动前端**（保持此窗口不关闭）
```cmd
cd D:\hogprice-insight\frontend
npm run dev
```

**第三步：打开浏览器**
访问 http://localhost:5173

---

*生成日期：2026-03-02*
