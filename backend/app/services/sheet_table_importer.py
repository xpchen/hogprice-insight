"""Sheet表导入器 - 批量导入数据到指定表"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from sqlalchemy.exc import IntegrityError


class SheetTableImporter:
    """Sheet表导入器"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def import_to_table(
        self,
        table_name: str,
        records: List[Dict],
        unique_key: List[str],
        batch_size: int = 1000
    ) -> Dict[str, int]:
        """
        导入数据到指定表
        
        Args:
            table_name: 目标表名
            records: 记录列表
            unique_key: 唯一键字段列表
        
        Returns:
            {
                "inserted": int,
                "updated": int,
                "errors": int
            }
        """
        if not records:
            return {"inserted": 0, "updated": 0, "errors": 0}
        
        # 检查表是否存在
        if not self._table_exists(table_name):
            raise ValueError(f"Table {table_name} does not exist")
        
        inserted_count = 0
        updated_count = 0
        error_count = 0
        
        # 批量处理
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            try:
                result = self._batch_upsert(table_name, batch, unique_key)
                inserted_count += result["inserted"]
                updated_count += result["updated"]
                error_count += result["errors"]
                # 每批提交一次
                self.db.commit()
            except Exception as e:
                self.db.rollback()
                error_count += len(batch)
                # 记录错误但继续处理下一批
                continue
        
        return {
            "inserted": inserted_count,
            "updated": updated_count,
            "errors": error_count
        }
    
    def _table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        inspector = inspect(self.db.bind)
        return table_name in inspector.get_table_names()
    
    def _batch_upsert(
        self,
        table_name: str,
        records: List[Dict],
        unique_key: List[str]
    ) -> Dict[str, int]:
        """批量upsert记录"""
        if not records:
            return {"inserted": 0, "updated": 0, "errors": 0}
        
        inserted_count = 0
        updated_count = 0
        error_count = 0
        
        # 获取表的所有列名
        inspector = inspect(self.db.bind)
        columns = [col["name"] for col in inspector.get_columns(table_name)]
        
        # 构建INSERT ... ON DUPLICATE KEY UPDATE语句
        # 注意：这里使用动态SQL，需要确保安全性
        
        for record in records:
            try:
                # 过滤掉不存在的列
                filtered_record = {k: v for k, v in record.items() if k in columns}
                
                if not filtered_record:
                    error_count += 1
                    continue
                
                # 构建列名和值（插入优先：有重复则跳过，不更新）
                col_names = list(filtered_record.keys())
                col_placeholders = [f":{col}" for col in col_names]
                
                # 使用 INSERT IGNORE：重复键时跳过，不报错
                insert_sql = f"""
                    INSERT IGNORE INTO {table_name} ({', '.join(col_names)})
                    VALUES ({', '.join(col_placeholders)})
                """
                
                # 执行SQL
                params = {col: filtered_record[col] for col in col_names}
                result = self.db.execute(text(insert_sql), params)
                
                if result.rowcount == 1:
                    inserted_count += 1
                # rowcount=0：INSERT IGNORE 下为重复键跳过，不计数
                
            except IntegrityError:
                # 插入优先：INSERT IGNORE 已处理重复，此处多为外键等错误
                error_count += 1
            except Exception:
                error_count += 1
        
        return {
            "inserted": inserted_count,
            "updated": updated_count,
            "errors": error_count
        }
