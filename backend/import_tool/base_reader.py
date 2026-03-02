"""BaseSheetReader - 所有 Excel reader 的基类"""
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


class BaseSheetReader:
    """
    每个子类对应一个 Excel 数据源文件。
    核心方法：
      read_file(filepath) -> {table_name: [record_dict, ...]}
    """

    FILE_PATTERN = ""  # 子类覆盖：文件名匹配关键字

    def __init__(self, engine: Engine, batch_id: int):
        self.engine = engine
        self.batch_id = batch_id

    def read_file(self, filepath: str) -> dict[str, list[dict]]:
        """读取 Excel 文件，返回 {table_name: [records]}"""
        raise NotImplementedError

    def bulk_insert(self, table_name: str, records: list[dict]) -> int:
        """批量 INSERT IGNORE（用于 bulk import，自动处理 UNIQUE KEY 冲突）"""
        if not records:
            return 0
        df = pd.DataFrame(records)
        # 去重：按非 batch_id 列去重
        dedup_cols = [c for c in df.columns if c not in ("batch_id", "id")]
        df = df.drop_duplicates(subset=dedup_cols, keep="last")
        # 通过临时表 + INSERT IGNORE 处理跨文件重复
        tmp_table = f"_tmp_{table_name}"
        df.to_sql(tmp_table, self.engine, if_exists="replace", index=False, method="multi", chunksize=2000)
        cols = ", ".join(f"`{c}`" for c in df.columns)
        with self.engine.connect() as conn:
            conn.execute(text(f"INSERT IGNORE INTO `{table_name}` ({cols}) SELECT {cols} FROM `{tmp_table}`"))
            conn.execute(text(f"DROP TABLE IF EXISTS `{tmp_table}`"))
            conn.commit()
        return len(df)

    def incremental_insert(self, table_name: str, records: list[dict], date_column: str) -> int:
        """增量 INSERT：只插入比库中 MAX(date_column) 更新的记录"""
        if not records:
            return 0

        with self.engine.connect() as conn:
            result = conn.execute(text(f"SELECT MAX(`{date_column}`) FROM `{table_name}`"))
            max_date = result.scalar()

        if max_date:
            new_records = [r for r in records if r.get(date_column) and r[date_column] > max_date]
        else:
            new_records = records

        if not new_records:
            return 0

        df = pd.DataFrame(new_records)
        tmp_table = f"_tmp_{table_name}"
        df.to_sql(tmp_table, self.engine, if_exists="replace", index=False, method="multi", chunksize=2000)
        cols = ", ".join(f"`{c}`" for c in df.columns)
        with self.engine.connect() as conn:
            conn.execute(text(f"INSERT IGNORE INTO `{table_name}` ({cols}) SELECT {cols} FROM `{tmp_table}`"))
            conn.execute(text(f"DROP TABLE IF EXISTS `{tmp_table}`"))
            conn.commit()

        return len(new_records)

    def insert_all(self, results: dict[str, list[dict]], mode: str = "bulk") -> dict[str, int]:
        """将 read_file 的结果写入数据库"""
        counts = {}
        for table_name, records in results.items():
            if not records:
                counts[table_name] = 0
                continue
            if mode == "bulk":
                counts[table_name] = self.bulk_insert(table_name, records)
            else:
                date_col = self._guess_date_column(table_name)
                counts[table_name] = self.incremental_insert(table_name, records, date_col)
        return counts

    @staticmethod
    def _guess_date_column(table_name: str) -> str:
        if "weekly" in table_name:
            return "week_end"
        if "monthly" in table_name:
            return "month_date"
        if "quarterly" in table_name:
            return "quarter_date"
        return "trade_date"
