import io
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import xlsxwriter

from app.services.query_service import query_timeseries


def export_excel(
    db: Session,
    date_range: Optional[Dict] = None,
    metric_ids: Optional[List[int]] = None,
    geo_ids: Optional[List[int]] = None,
    company_ids: Optional[List[int]] = None,
    warehouse_ids: Optional[List[int]] = None,
    tags_filter: Optional[Dict] = None,
    group_by: Optional[List[str]] = None,
    time_dimension: str = "daily",
    include_detail: bool = True,
    include_summary: bool = True,
    include_chart: bool = True,
    include_cover: bool = True
) -> io.BytesIO:
    """
    导出Excel文件
    
    Args:
        db: 数据库会话
        date_range: 日期范围
        metric_ids: 指标ID列表
        geo_ids: 地区ID列表
        company_ids: 企业ID列表
        warehouse_ids: 交割库ID列表
        tags_filter: tags过滤条件
        group_by: 分组字段
        include_detail: 是否包含明细数据
        include_summary: 是否包含汇总表
        include_chart: 是否包含图表
        include_cover: 是否包含封面
    
    Returns:
        BytesIO对象（Excel文件内容）
    """
    # 查询数据
    query_result = query_timeseries(
        db=db,
        date_range=date_range,
        metric_ids=metric_ids,
        geo_ids=geo_ids,
        company_ids=company_ids,
        warehouse_ids=warehouse_ids,
        tags_filter=tags_filter,
        group_by=group_by,
        time_dimension=time_dimension
    )
    
    # 创建Excel文件（内存中）
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    
    # 设置格式
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#366092',
        'font_color': 'white',
        'align': 'center',
        'valign': 'vcenter',
        'border': 1
    })
    
    date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
    number_format = workbook.add_format({'num_format': '#,##0.00'})
    
    sheet_index = 0
    
    # 封面
    if include_cover:
        cover_sheet = workbook.add_worksheet('封面')
        cover_sheet.write(0, 0, '猪价智盘数据报表', workbook.add_format({'bold': True, 'font_size': 16}))
        cover_sheet.write(2, 0, f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        cover_sheet.write(3, 0, f'时间范围: {date_range["start"]} 至 {date_range["end"]}')
        cover_sheet.write(4, 0, f'指标数量: {len(metric_ids) if metric_ids else "全部"}')
        sheet_index += 1
    
    # 明细数据表
    if include_detail and query_result["series"]:
        detail_sheet = workbook.add_worksheet('明细数据')
        
        # 写入表头
        detail_sheet.write(0, 0, '日期', header_format)
        col = 1
        for series in query_result["series"]:
            detail_sheet.write(0, col, series["name"], header_format)
            col += 1
        
        # 写入数据
        categories = query_result["categories"]
        for row_idx, date_str in enumerate(categories, start=1):
            detail_sheet.write(row_idx, 0, date_str, date_format)
            
            for col_idx, series in enumerate(query_result["series"], start=1):
                value = None
                for point in series["data"]:
                    if point[0] == date_str:
                        value = point[1]
                        break
                
                if value is not None:
                    detail_sheet.write(row_idx, col_idx, value, number_format)
        
        # 设置列宽
        detail_sheet.set_column(0, 0, 12)  # 日期列
        for i in range(1, len(query_result["series"]) + 1):
            detail_sheet.set_column(i, i, 15)
        
        sheet_index += 1
    
    # 汇总表（如果有group_by）
    if include_summary and group_by:
        summary_sheet = workbook.add_worksheet('汇总数据')
        
        # 写入表头
        summary_sheet.write(0, 0, '日期', header_format)
        col = 1
        for series in query_result["series"]:
            summary_sheet.write(0, col, series["name"], header_format)
            col += 1
        
        # 写入数据
        categories = query_result["categories"]
        for row_idx, date_str in enumerate(categories, start=1):
            summary_sheet.write(row_idx, 0, date_str, date_format)
            
            for col_idx, series in enumerate(query_result["series"], start=1):
                value = None
                for point in series["data"]:
                    if point[0] == date_str:
                        value = point[1]
                        break
                
                if value is not None:
                    summary_sheet.write(row_idx, col_idx, value, number_format)
        
        # 设置列宽
        summary_sheet.set_column(0, 0, 12)
        for i in range(1, len(query_result["series"]) + 1):
            summary_sheet.set_column(i, i, 15)
        
        sheet_index += 1
    
    # 图表
    if include_chart and query_result["series"]:
        chart_sheet = workbook.add_worksheet('图表')
        
        # 创建折线图
        chart = workbook.add_chart({'type': 'line'})
        
        # 添加数据系列
        categories_range = f'明细数据!$A$2:$A${len(query_result["categories"]) + 1}'
        
        for idx, series in enumerate(query_result["series"]):
            col_letter = chr(ord('B') + idx)
            values_range = f'明细数据!${col_letter}$2:${col_letter}${len(query_result["categories"]) + 1}'
            
            chart.add_series({
                'name': series["name"],
                'categories': categories_range,
                'values': values_range,
            })
        
        # 设置图表属性
        chart.set_title({'name': '时间序列图表'})
        chart.set_x_axis({'name': '日期'})
        chart.set_y_axis({'name': '数值'})
        chart.set_legend({'position': 'bottom'})
        chart.set_size({'width': 720, 'height': 480})
        
        # 插入图表
        chart_sheet.insert_chart('B2', chart)
    
    workbook.close()
    output.seek(0)
    
    return output
