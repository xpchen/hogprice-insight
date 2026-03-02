"""数据库连接与建表 DDL"""
from sqlalchemy import create_engine, text

DATABASE_URL = "mysql+pymysql://root:root@localhost:3306/hogprice_v3?charset=utf8mb4"

def get_engine():
    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={
            "connect_timeout": 60,
            "read_timeout": 600,
            "write_timeout": 600,
            "charset": "utf8mb4",
        },
    )

DDL_STATEMENTS = [
    # ── 维度表 ──
    """
    CREATE TABLE IF NOT EXISTS dim_region (
        region_code  VARCHAR(32)  PRIMARY KEY,
        region_name  VARCHAR(64)  NOT NULL,
        region_level TINYINT      NOT NULL DEFAULT 2,
        parent_code  VARCHAR(32),
        INDEX idx_level (region_level)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS dim_company (
        company_code VARCHAR(32)  PRIMARY KEY,
        company_name VARCHAR(128) NOT NULL,
        short_name   VARCHAR(32),
        INDEX idx_name (company_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS dim_contract (
        contract_code VARCHAR(16) PRIMARY KEY,
        instrument    VARCHAR(8)  NOT NULL DEFAULT 'LH',
        delivery_month DATE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # ── 管理表 ──
    """
    CREATE TABLE IF NOT EXISTS import_batch (
        id          BIGINT       AUTO_INCREMENT PRIMARY KEY,
        filename    VARCHAR(255) NOT NULL,
        file_hash   VARCHAR(64),
        mode        VARCHAR(16)  NOT NULL DEFAULT 'bulk',
        status      VARCHAR(16)  NOT NULL DEFAULT 'processing',
        row_count   INT          DEFAULT 0,
        duration_ms INT,
        error_msg   TEXT,
        created_at  DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # ── 系统表 ──
    """
    CREATE TABLE IF NOT EXISTS sys_user (
        id            BIGINT       AUTO_INCREMENT PRIMARY KEY,
        username      VARCHAR(64)  NOT NULL UNIQUE,
        password_hash VARCHAR(256) NOT NULL,
        is_active     TINYINT      NOT NULL DEFAULT 1,
        created_at    DATETIME     DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS sys_role (
        id        BIGINT      AUTO_INCREMENT PRIMARY KEY,
        role_name VARCHAR(32) NOT NULL UNIQUE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS sys_user_role (
        id      BIGINT AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT NOT NULL,
        role_id BIGINT NOT NULL,
        UNIQUE KEY uq_user_role (user_id, role_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # ── F1: 日度价格 ──
    """
    CREATE TABLE IF NOT EXISTS fact_price_daily (
        id          BIGINT       AUTO_INCREMENT PRIMARY KEY,
        trade_date  DATE         NOT NULL,
        region_code VARCHAR(32)  NOT NULL,
        price_type  VARCHAR(32)  NOT NULL,
        source      VARCHAR(16)  NOT NULL DEFAULT 'YONGYI',
        value       DECIMAL(10,2),
        unit        VARCHAR(16)  NOT NULL DEFAULT '元/公斤',
        batch_id    BIGINT,
        UNIQUE KEY uq_price (trade_date, region_code, price_type, source),
        INDEX idx_date (trade_date),
        INDEX idx_region_date (region_code, trade_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # ── F2: 日度价差 ──
    """
    CREATE TABLE IF NOT EXISTS fact_spread_daily (
        id          BIGINT       AUTO_INCREMENT PRIMARY KEY,
        trade_date  DATE         NOT NULL,
        region_code VARCHAR(32)  NOT NULL,
        spread_type VARCHAR(32)  NOT NULL,
        source      VARCHAR(16)  NOT NULL DEFAULT 'YONGYI',
        value       DECIMAL(10,2),
        unit        VARCHAR(16)  NOT NULL DEFAULT '元/公斤',
        batch_id    BIGINT,
        UNIQUE KEY uq_spread (trade_date, region_code, spread_type, source),
        INDEX idx_date (trade_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # ── F3: 日度屠宰量 ──
    """
    CREATE TABLE IF NOT EXISTS fact_slaughter_daily (
        id          BIGINT       AUTO_INCREMENT PRIMARY KEY,
        trade_date  DATE         NOT NULL,
        region_code VARCHAR(32)  NOT NULL,
        source      VARCHAR(16)  NOT NULL DEFAULT 'YONGYI',
        volume      INT,
        batch_id    BIGINT,
        UNIQUE KEY uq_slaughter (trade_date, region_code, source),
        INDEX idx_date (trade_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # ── F4: 周度指标 ──
    """
    CREATE TABLE IF NOT EXISTS fact_weekly_indicator (
        id             BIGINT       AUTO_INCREMENT PRIMARY KEY,
        week_end       DATE         NOT NULL,
        week_start     DATE,
        region_code    VARCHAR(32)  NOT NULL,
        indicator_code VARCHAR(64)  NOT NULL,
        source         VARCHAR(16)  NOT NULL DEFAULT 'YONGYI',
        value          DECIMAL(18,4),
        unit           VARCHAR(32),
        batch_id       BIGINT,
        UNIQUE KEY uq_weekly (week_end, region_code, indicator_code, source),
        INDEX idx_indicator_date (indicator_code, week_end),
        INDEX idx_region_date (region_code, week_end)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # ── F5: 月度指标 ──
    """
    CREATE TABLE IF NOT EXISTS fact_monthly_indicator (
        id             BIGINT       AUTO_INCREMENT PRIMARY KEY,
        month_date     DATE         NOT NULL,
        region_code    VARCHAR(32)  NOT NULL DEFAULT 'NATION',
        indicator_code VARCHAR(64)  NOT NULL,
        sub_category   VARCHAR(64)  DEFAULT '',
        source         VARCHAR(16)  NOT NULL,
        value          DECIMAL(18,6),
        value_type     VARCHAR(16)  NOT NULL DEFAULT 'abs',
        unit           VARCHAR(32),
        batch_id       BIGINT,
        UNIQUE KEY uq_monthly (month_date, region_code, indicator_code, sub_category, source, value_type),
        INDEX idx_indicator_date (indicator_code, month_date),
        INDEX idx_source (source)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # ── F6: 集团企业日度 ──
    """
    CREATE TABLE IF NOT EXISTS fact_enterprise_daily (
        id           BIGINT       AUTO_INCREMENT PRIMARY KEY,
        trade_date   DATE         NOT NULL,
        company_code VARCHAR(32)  NOT NULL,
        region_code  VARCHAR(32)  NOT NULL DEFAULT 'NATION',
        metric_type  VARCHAR(32)  NOT NULL DEFAULT 'output',
        value        DECIMAL(18,4),
        unit         VARCHAR(16),
        batch_id     BIGINT,
        UNIQUE KEY uq_enterprise (trade_date, company_code, region_code, metric_type),
        INDEX idx_company_date (company_code, trade_date),
        INDEX idx_date (trade_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # ── F7: 集团企业月度 ──
    """
    CREATE TABLE IF NOT EXISTS fact_enterprise_monthly (
        id           BIGINT       AUTO_INCREMENT PRIMARY KEY,
        month_date   DATE         NOT NULL,
        company_code VARCHAR(32)  NOT NULL,
        region_code  VARCHAR(32)  NOT NULL DEFAULT 'NATION',
        indicator    VARCHAR(64)  NOT NULL,
        value        DECIMAL(18,4),
        unit         VARCHAR(16),
        batch_id     BIGINT,
        UNIQUE KEY uq_ent_monthly (month_date, company_code, region_code, indicator),
        INDEX idx_company_date (company_code, month_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # ── F8: 白条市场 ──
    """
    CREATE TABLE IF NOT EXISTS fact_carcass_market (
        id          BIGINT       AUTO_INCREMENT PRIMARY KEY,
        trade_date  DATE         NOT NULL,
        region_code VARCHAR(32)  NOT NULL,
        metric_type VARCHAR(32)  NOT NULL,
        source      VARCHAR(16)  NOT NULL,
        value       DECIMAL(18,4),
        unit        VARCHAR(16),
        batch_id    BIGINT,
        UNIQUE KEY uq_carcass (trade_date, region_code, metric_type, source),
        INDEX idx_date (trade_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # ── F9: 期货日行情 ──
    """
    CREATE TABLE IF NOT EXISTS fact_futures_daily (
        id             BIGINT       AUTO_INCREMENT PRIMARY KEY,
        contract_code  VARCHAR(16)  NOT NULL,
        trade_date     DATE         NOT NULL,
        open           DECIMAL(10,2),
        high           DECIMAL(10,2),
        low            DECIMAL(10,2),
        close          DECIMAL(10,2),
        settle         DECIMAL(10,2),
        pre_settle     DECIMAL(10,2),
        chg            DECIMAL(10,2),
        volume         BIGINT,
        open_interest  BIGINT,
        oi_chg         BIGINT,
        turnover       DECIMAL(18,2),
        batch_id       BIGINT,
        UNIQUE KEY uq_futures (contract_code, trade_date),
        INDEX idx_date (trade_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # ── F10: 期权日行情 ──
    """
    CREATE TABLE IF NOT EXISTS fact_options_daily (
        id                   BIGINT       AUTO_INCREMENT PRIMARY KEY,
        underlying_contract  VARCHAR(16)  NOT NULL,
        option_type          CHAR(1)      NOT NULL,
        strike               DECIMAL(10,2) NOT NULL,
        option_code          VARCHAR(64)  NOT NULL,
        trade_date           DATE         NOT NULL,
        open                 DECIMAL(10,2),
        high                 DECIMAL(10,2),
        low                  DECIMAL(10,2),
        close                DECIMAL(10,2),
        settle               DECIMAL(10,2),
        pre_settle           DECIMAL(10,2),
        chg                  DECIMAL(10,2),
        delta                DECIMAL(8,4),
        iv                   DECIMAL(8,4),
        volume               BIGINT,
        open_interest        BIGINT,
        oi_chg               BIGINT,
        turnover             DECIMAL(18,2),
        exercise_volume      BIGINT,
        batch_id             BIGINT,
        UNIQUE KEY uq_options (option_code, trade_date),
        INDEX idx_underlying_date (underlying_contract, trade_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # ── F11: 期货基差/升贴水 ──
    """
    CREATE TABLE IF NOT EXISTS fact_futures_basis (
        id             BIGINT       AUTO_INCREMENT PRIMARY KEY,
        trade_date     DATE         NOT NULL,
        contract_code  VARCHAR(16),
        region_code    VARCHAR(32),
        indicator_code VARCHAR(64)  NOT NULL,
        value          DECIMAL(18,4),
        unit           VARCHAR(32),
        batch_id       BIGINT,
        UNIQUE KEY uq_basis (trade_date, contract_code, region_code, indicator_code),
        INDEX idx_indicator_date (indicator_code, trade_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # ── F12: 季度统计 ──
    """
    CREATE TABLE IF NOT EXISTS fact_quarterly_stats (
        id             BIGINT       AUTO_INCREMENT PRIMARY KEY,
        quarter_date   DATE         NOT NULL,
        indicator_code VARCHAR(64)  NOT NULL,
        region_code    VARCHAR(32)  NOT NULL DEFAULT 'NATION',
        value          DECIMAL(18,4),
        unit           VARCHAR(32),
        batch_id       BIGINT,
        UNIQUE KEY uq_quarterly (quarter_date, indicator_code, region_code),
        INDEX idx_indicator_date (indicator_code, quarter_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # ── 报表/图表模板表（保留现有） ──
    """
    CREATE TABLE IF NOT EXISTS chart_template (
        id          BIGINT       AUTO_INCREMENT PRIMARY KEY,
        name        VARCHAR(128) NOT NULL,
        config_json MEDIUMTEXT,
        created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
        updated_at  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS quick_chart_cache (
        id           BIGINT       AUTO_INCREMENT PRIMARY KEY,
        cache_key    VARCHAR(256) NOT NULL UNIQUE,
        cache_value  MEDIUMTEXT,
        expires_at   DATETIME,
        created_at   DATETIME     DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]

# 需要清空的 fact 表（bulk import 时使用）
FACT_TABLES = [
    "fact_price_daily",
    "fact_spread_daily",
    "fact_slaughter_daily",
    "fact_weekly_indicator",
    "fact_monthly_indicator",
    "fact_enterprise_daily",
    "fact_enterprise_monthly",
    "fact_carcass_market",
    "fact_futures_daily",
    "fact_options_daily",
    "fact_futures_basis",
    "fact_quarterly_stats",
]


def init_db(engine=None):
    """创建所有表"""
    if engine is None:
        engine = get_engine()
    with engine.connect() as conn:
        for ddl in DDL_STATEMENTS:
            conn.execute(text(ddl))
        conn.commit()
    print(f"✓ 已创建 {len(DDL_STATEMENTS)} 张表")


def truncate_fact_tables(engine):
    """清空所有 fact 表（bulk import 前调用）"""
    with engine.connect() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in FACT_TABLES:
            conn.execute(text(f"TRUNCATE TABLE {table}"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        conn.commit()
    print(f"✓ 已清空 {len(FACT_TABLES)} 张 fact 表")


def populate_dim_region(engine):
    """填充 dim_region 维度表"""
    regions = [
        # 全国
        ("NATION", "全国", 0, None),
        # 大区
        ("NORTHEAST", "东北", 1, "NATION"),
        ("NORTH", "华北", 1, "NATION"),
        ("EAST", "华东", 1, "NATION"),
        ("CENTRAL", "华中", 1, "NATION"),
        ("SOUTH", "华南", 1, "NATION"),
        ("SOUTHWEST", "西南", 1, "NATION"),
        ("NORTHWEST", "西北", 1, "NATION"),
        # 省份
        ("HEILONGJIANG", "黑龙江", 2, "NORTHEAST"),
        ("JILIN", "吉林", 2, "NORTHEAST"),
        ("LIAONING", "辽宁", 2, "NORTHEAST"),
        ("BEIJING", "北京", 2, "NORTH"),
        ("TIANJIN", "天津", 2, "NORTH"),
        ("HEBEI", "河北", 2, "NORTH"),
        ("SHANXI", "山西", 2, "NORTH"),
        ("NEIMENGGU", "内蒙古", 2, "NORTH"),
        ("SHANDONG", "山东", 2, "EAST"),
        ("JIANGSU", "江苏", 2, "EAST"),
        ("ZHEJIANG", "浙江", 2, "EAST"),
        ("ANHUI", "安徽", 2, "EAST"),
        ("FUJIAN", "福建", 2, "EAST"),
        ("SHANGHAI", "上海", 2, "EAST"),
        ("HENAN", "河南", 2, "CENTRAL"),
        ("HUBEI", "湖北", 2, "CENTRAL"),
        ("HUNAN", "湖南", 2, "CENTRAL"),
        ("JIANGXI", "江西", 2, "CENTRAL"),
        ("GUANGDONG", "广东", 2, "SOUTH"),
        ("GUANGXI", "广西", 2, "SOUTH"),
        ("HAINAN", "海南", 2, "SOUTH"),
        ("SICHUAN", "四川", 2, "SOUTHWEST"),
        ("CHONGQING", "重庆", 2, "SOUTHWEST"),
        ("GUIZHOU", "贵州", 2, "SOUTHWEST"),
        ("YUNNAN", "云南", 2, "SOUTHWEST"),
        ("XIZANG", "西藏", 2, "SOUTHWEST"),
        ("SHAANXI", "陕西", 2, "NORTHWEST"),
        ("GANSU", "甘肃", 2, "NORTHWEST"),
        ("QINGHAI", "青海", 2, "NORTHWEST"),
        ("NINGXIA", "宁夏", 2, "NORTHWEST"),
        ("XINJIANG", "新疆", 2, "NORTHWEST"),
    ]
    with engine.connect() as conn:
        for code, name, level, parent in regions:
            conn.execute(text(
                "INSERT IGNORE INTO dim_region (region_code, region_name, region_level, parent_code) "
                "VALUES (:code, :name, :level, :parent)"
            ), {"code": code, "name": name, "level": level, "parent": parent})
        conn.commit()
    print(f"✓ 已填充 {len(regions)} 条 dim_region")


if __name__ == "__main__":
    engine = get_engine()
    init_db(engine)
    populate_dim_region(engine)
