# 数据库 DDL + Alembic 迁移草案（PostgreSQL 优先）

> 说明：以下 DDL 以 **PostgreSQL** 为主（推荐用于 jsonb / GIN 索引 / 分区）。  
> 若使用 MySQL 8.0：json 字段与索引策略需调整（详见文末差异说明）。

---

## 1) 核心表清单

- 用户与权限
  - `sys_user`
  - `sys_role`
  - `sys_user_role`

- 导入审计
  - `import_batch`

- 维度/指标元数据
  - `dim_metric`
  - `dim_geo`
  - `dim_company`
  - `dim_warehouse`

- 事实表（统一观测长表）
  - `fact_observation`

---

## 2) PostgreSQL DDL（可直接执行）

> 建议 schema：`hogprice`（可改）

```sql
-- 0. schema
CREATE SCHEMA IF NOT EXISTS hogprice;
SET search_path TO hogprice;

-- 1. 用户表
CREATE TABLE IF NOT EXISTS sys_user (
  id              BIGSERIAL PRIMARY KEY,
  username        VARCHAR(64) NOT NULL UNIQUE,
  password_hash   VARCHAR(255) NOT NULL,
  display_name    VARCHAR(64),
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. 角色表
CREATE TABLE IF NOT EXISTS sys_role (
  id          BIGSERIAL PRIMARY KEY,
  code        VARCHAR(64) NOT NULL UNIQUE, -- admin / analyst / viewer
  name        VARCHAR(64) NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. 用户-角色关联
CREATE TABLE IF NOT EXISTS sys_user_role (
  user_id BIGINT NOT NULL REFERENCES sys_user(id) ON DELETE CASCADE,
  role_id BIGINT NOT NULL REFERENCES sys_role(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, role_id)
);

-- 4. 导入批次审计
CREATE TABLE IF NOT EXISTS import_batch (
  id            BIGSERIAL PRIMARY KEY,
  filename      VARCHAR(255) NOT NULL,
  file_hash     VARCHAR(64), -- sha256，可空
  uploader_id   BIGINT REFERENCES sys_user(id),
  status        VARCHAR(20) NOT NULL DEFAULT 'success', -- success/failed/partial
  total_rows    BIGINT DEFAULT 0,
  success_rows  BIGINT DEFAULT 0,
  failed_rows   BIGINT DEFAULT 0,
  error_json    JSONB, -- 错误清单（sheet/row/col/reason）
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_import_batch_created_at ON import_batch(created_at DESC);

-- 5. 指标元数据
CREATE TABLE IF NOT EXISTS dim_metric (
  id                BIGSERIAL PRIMARY KEY,
  metric_group      VARCHAR(32) NOT NULL,  -- province/group/warehouse/spread/profit
  metric_name       VARCHAR(64) NOT NULL,  -- 出栏价/出栏均价/区域价差/利润/猪粮比...
  unit              VARCHAR(32),
  freq              VARCHAR(16) NOT NULL,  -- daily/weekly
  raw_header        TEXT NOT NULL,         -- 原始“指标名称”
  sheet_name        VARCHAR(64),           -- 来源 sheet，建议记录
  source_updated_at VARCHAR(64),           -- 原表“更新时间”行字符串（先不强转时间）
  parse_json        JSONB,                 -- 解析结果（pig_type, weight_range, geo, company...）
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (raw_header, COALESCE(sheet_name, ''))
);

CREATE INDEX IF NOT EXISTS idx_dim_metric_group_freq ON dim_metric(metric_group, freq);
CREATE INDEX IF NOT EXISTS idx_dim_metric_name ON dim_metric(metric_name);

-- 6. 地区维度（省/区域）
CREATE TABLE IF NOT EXISTS dim_geo (
  id         BIGSERIAL PRIMARY KEY,
  province   VARCHAR(32) NOT NULL,
  region     VARCHAR(32),          -- 东北/华北/华东...
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (province)
);

-- 7. 企业维度
CREATE TABLE IF NOT EXISTS dim_company (
  id           BIGSERIAL PRIMARY KEY,
  company_name VARCHAR(128) NOT NULL,
  province     VARCHAR(32),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (company_name)
);

-- 8. 交割库/库点维度
CREATE TABLE IF NOT EXISTS dim_warehouse (
  id             BIGSERIAL PRIMARY KEY,
  warehouse_name VARCHAR(128) NOT NULL,
  province       VARCHAR(32),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (warehouse_name)
);

-- 9. 事实表：统一观测（长表）
CREATE TABLE IF NOT EXISTS fact_observation (
  id           BIGSERIAL PRIMARY KEY,
  batch_id     BIGINT REFERENCES import_batch(id) ON DELETE SET NULL,
  metric_id    BIGINT NOT NULL REFERENCES dim_metric(id) ON DELETE CASCADE,
  obs_date     DATE NOT NULL,
  value        NUMERIC(18, 6),     -- 价格/价差/比例/利润等统一 numeric
  geo_id       BIGINT REFERENCES dim_geo(id),
  company_id   BIGINT REFERENCES dim_company(id),
  warehouse_id BIGINT REFERENCES dim_warehouse(id),
  tags_json    JSONB,              -- pig_type/weight_range/ma/window/price_type...
  raw_value    VARCHAR(64),        -- 可选：保留原始字符串（异常时排查）
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  -- 去重：一个日期下同一维度组合只保留一条
  CONSTRAINT uq_fact_obs UNIQUE (metric_id, obs_date, COALESCE(geo_id,0), COALESCE(company_id,0), COALESCE(warehouse_id,0), COALESCE(tags_json::text,''))
);

-- 常用索引
CREATE INDEX IF NOT EXISTS idx_fact_metric_date ON fact_observation(metric_id, obs_date);
CREATE INDEX IF NOT EXISTS idx_fact_geo_date ON fact_observation(geo_id, obs_date);
CREATE INDEX IF NOT EXISTS idx_fact_company_date ON fact_observation(company_id, obs_date);
CREATE INDEX IF NOT EXISTS idx_fact_warehouse_date ON fact_observation(warehouse_id, obs_date);

-- JSONB GIN（tags_json 过滤很常用时建议）
CREATE INDEX IF NOT EXISTS idx_fact_tags_gin ON fact_observation USING GIN (tags_json);

-- 如数据量大（>千万），建议按月分区（后续加）
```

---

## 3) Alembic 迁移草案（核心结构）

### 3.1 `alembic/env.py`（关键点）
- target_metadata 指向 SQLAlchemy models 的 Base.metadata
- 设置 schema（hogprice）的话，需要在 Base 或 Table 上显式 schema；或连接后执行 `SET search_path`.

### 3.2 迁移脚本草案（`alembic/versions/0001_init.py`）

```py
\"\"\"init schema

Revision ID: 0001_init
Revises:
Create Date: 2026-02-01
\"\"\"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = "hogprice"

def upgrade():
    op.execute(sa.text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))

    # sys_user
    op.create_table(
        "sys_user",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(64)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("username", name="uq_sys_user_username"),
        schema=SCHEMA,
    )

    # sys_role
    op.create_table(
        "sys_role",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("code", name="uq_sys_role_code"),
        schema=SCHEMA,
    )

    # sys_user_role
    op.create_table(
        "sys_user_role",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.sys_user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], [f"{SCHEMA}.sys_role.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
        schema=SCHEMA,
    )

    # import_batch
    op.create_table(
        "import_batch",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_hash", sa.String(64)),
        sa.Column("uploader_id", sa.BigInteger()),
        sa.Column("status", sa.String(20), nullable=False, server_default="success"),
        sa.Column("total_rows", sa.BigInteger(), server_default="0"),
        sa.Column("success_rows", sa.BigInteger(), server_default="0"),
        sa.Column("failed_rows", sa.BigInteger(), server_default="0"),
        sa.Column("error_json", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["uploader_id"], [f"{SCHEMA}.sys_user.id"]),
        schema=SCHEMA,
    )
    op.create_index("idx_import_batch_created_at", "import_batch", ["created_at"], schema=SCHEMA)

    # dim_metric
    op.create_table(
        "dim_metric",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("metric_group", sa.String(32), nullable=False),
        sa.Column("metric_name", sa.String(64), nullable=False),
        sa.Column("unit", sa.String(32)),
        sa.Column("freq", sa.String(16), nullable=False),
        sa.Column("raw_header", sa.Text(), nullable=False),
        sa.Column("sheet_name", sa.String(64)),
        sa.Column("source_updated_at", sa.String(64)),
        sa.Column("parse_json", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema=SCHEMA,
    )
    op.create_index("idx_dim_metric_group_freq", "dim_metric", ["metric_group", "freq"], schema=SCHEMA)
    op.create_index("idx_dim_metric_name", "dim_metric", ["metric_name"], schema=SCHEMA)
    op.create_unique_constraint(
        "uq_dim_metric_raw_sheet",
        "dim_metric",
        ["raw_header", "sheet_name"],
        schema=SCHEMA,
    )

    # dim_geo
    op.create_table(
        "dim_geo",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("province", sa.String(32), nullable=False),
        sa.Column("region", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("province", name="uq_dim_geo_province"),
        schema=SCHEMA,
    )

    # dim_company
    op.create_table(
        "dim_company",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("company_name", sa.String(128), nullable=False),
        sa.Column("province", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("company_name", name="uq_dim_company_name"),
        schema=SCHEMA,
    )

    # dim_warehouse
    op.create_table(
        "dim_warehouse",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("warehouse_name", sa.String(128), nullable=False),
        sa.Column("province", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("warehouse_name", name="uq_dim_warehouse_name"),
        schema=SCHEMA,
    )

    # fact_observation
    op.create_table(
        "fact_observation",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("batch_id", sa.BigInteger()),
        sa.Column("metric_id", sa.BigInteger(), nullable=False),
        sa.Column("obs_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(18, 6)),
        sa.Column("geo_id", sa.BigInteger()),
        sa.Column("company_id", sa.BigInteger()),
        sa.Column("warehouse_id", sa.BigInteger()),
        sa.Column("tags_json", postgresql.JSONB()),
        sa.Column("raw_value", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["batch_id"], [f"{SCHEMA}.import_batch.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["metric_id"], [f"{SCHEMA}.dim_metric.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["geo_id"], [f"{SCHEMA}.dim_geo.id"]),
        sa.ForeignKeyConstraint(["company_id"], [f"{SCHEMA}.dim_company.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], [f"{SCHEMA}.dim_warehouse.id"]),
        schema=SCHEMA,
    )
    op.create_index("idx_fact_metric_date", "fact_observation", ["metric_id", "obs_date"], schema=SCHEMA)
    op.create_index("idx_fact_geo_date", "fact_observation", ["geo_id", "obs_date"], schema=SCHEMA)
    op.create_index("idx_fact_company_date", "fact_observation", ["company_id", "obs_date"], schema=SCHEMA)
    op.create_index("idx_fact_warehouse_date", "fact_observation", ["warehouse_id", "obs_date"], schema=SCHEMA)
    op.create_index("idx_fact_tags_gin", "fact_observation", ["tags_json"], postgresql_using="gin", schema=SCHEMA)

def downgrade():
    op.drop_index("idx_fact_tags_gin", table_name="fact_observation", schema=SCHEMA)
    op.drop_table("fact_observation", schema=SCHEMA)
    op.drop_table("dim_warehouse", schema=SCHEMA)
    op.drop_table("dim_company", schema=SCHEMA)
    op.drop_table("dim_geo", schema=SCHEMA)
    op.drop_table("dim_metric", schema=SCHEMA)
    op.drop_table("import_batch", schema=SCHEMA)
    op.drop_table("sys_user_role", schema=SCHEMA)
    op.drop_table("sys_role", schema=SCHEMA)
    op.drop_table("sys_user", schema=SCHEMA)
    op.execute(sa.text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
```

> 注意：Alembic 中如果想要 `BIGSERIAL` 的自增效果，需将 `id` 用 `sa.BigInteger()` + `server_default=sa.text("nextval('...')")`，或者直接用 `sa.Identity()`（Postgres 10+）。实际实现时建议 SQLAlchemy Model 里用 `sa.BigInteger, primary_key=True` + `sa.Identity()`。

---

## 4) MySQL 8.0 差异（简要）

- `JSONB` 改为 `JSON`
- `GIN` 索引不可用：可改为**生成列 + BTREE**（比如把常用 tag 提升为独立列），或在业务侧减少对 json 条件过滤
- `NUMERIC(18,6)` 同样可用
- `schema` 概念不同：用 database 替代；不需要 `CREATE SCHEMA`

---

## 5) 建议的后续增强（非必须）
- `fact_observation` 按月分区（obs_date）
- `dim_metric` 增加 `metric_code`（便于前端稳定引用）
- 新增 `dim_region`（若 region 体系复杂）
- 新增 `dim_tag_kv`（把 tags_json 的高频字段规范化）

