import io
import os
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import xlsxwriter

from app.models import ReportTemplate, ReportRun
from app.services.query_service import query_timeseries
from app.services.seasonality_service import query_seasonality


def _generate_cover_sheet(
    workbook,
    worksheet,
    sheet_config: Dict,
    params: Dict,
    header_format
):
    """生成封面页"""
    title = sheet_config.get("title", "报告")
    subtitle = sheet_config.get("subtitle", "")
    
    # 写入标题
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 18,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    worksheet.write(0, 0, title, title_format)
    worksheet.merge_range(0, 0, 0, 3, title, title_format)
    
    if subtitle:
        subtitle_format = workbook.add_format({
            'font_size': 12,
            'align': 'center',
            'valign': 'vcenter'
        })
        worksheet.write(1, 0, subtitle, subtitle_format)
        worksheet.merge_range(1, 0, 1, 3, subtitle, subtitle_format)
    
    # 写入参数信息
    row = 3
    worksheet.write(row, 0, "生成时间:", header_format)
    worksheet.write(row, 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    if params.get("years"):
        row += 1
        worksheet.write(row, 0, "年份范围:", header_format)
        worksheet.write(row, 1, ", ".join(map(str, params["years"])))
    
    if params.get("date_range"):
        row += 1
        worksheet.write(row, 0, "日期范围:", header_format)
        date_range = params["date_range"]
        worksheet.write(row, 1, f"{date_range.get('start')} 至 {date_range.get('end')}")
    
    # 设置列宽
    worksheet.set_column(0, 0, 15)
    worksheet.set_column(1, 3, 20)


def generate_report(
    db: Session,
    template_id: int,
    params: Dict
) -> str:
    """
    生成报告
    
    Args:
        db: 数据库会话
        template_id: 报告模板ID
        params: 报告生成参数（年份/区间/地区等）
    
    Returns:
        输出文件路径
    """
    # 获取模板
    template = db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()
    if not template:
        raise ValueError(f"Template {template_id} not found")
    
    template_config = template.template_json
    
    # 创建报告运行记录
    report_run = ReportRun(
        template_id=template_id,
        params_json=params,
        status="running"
    )
    db.add(report_run)
    db.commit()
    db.refresh(report_run)
    
    try:
        # 创建输出目录
        output_dir = os.path.join("reports", str(report_run.id))
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成Excel文件
        output_path = os.path.join(output_dir, f"report_{report_run.id}.xlsx")
        
        # 创建Excel工作簿
        workbook = xlsxwriter.Workbook(output_path)
        
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
        
        # 根据模板配置生成各个sheet
        sheets = template_config.get("sheets", [])
        
        for sheet_config in sheets:
            sheet_name = sheet_config.get("name", "Sheet1")
            sheet_type = sheet_config.get("type")  # cover | summary | rank_table
            chart_type = sheet_config.get("chart_type")  # seasonality | timeseries
            
            # Excel sheet名称限制为31个字符
            excel_sheet_name = sheet_name[:31] if len(sheet_name) > 31 else sheet_name
            worksheet = workbook.add_worksheet(excel_sheet_name)
            
            # 保存原始sheet_name用于图表引用
            sheet_config["_excel_sheet_name"] = excel_sheet_name
            
            # 处理封面页
            if sheet_type == "cover":
                _generate_cover_sheet(
                    workbook, worksheet, sheet_config, params,
                    header_format
                )
            # 处理季节性图sheet
            elif chart_type == "seasonality":
                _generate_seasonality_sheet(
                    db, workbook, worksheet, sheet_config, params,
                    header_format, date_format, number_format
                )
            # 处理时间序列图sheet
            elif chart_type == "timeseries":
                _generate_timeseries_sheet(
                    db, workbook, worksheet, sheet_config, params,
                    header_format, date_format, number_format
                )
            # 处理摘要页
            elif sheet_type == "summary":
                worksheet.write(0, 0, "统计摘要")
                worksheet.write(1, 0, "此功能待实现")
            # 处理排名表
            elif sheet_type == "rank_table":
                worksheet.write(0, 0, "排名表")
                worksheet.write(1, 0, "此功能待实现")
        
        workbook.close()
        
        # 更新运行记录
        report_run.status = "success"
        report_run.output_path = output_path
        report_run.finished_at = datetime.now()
        db.commit()
        
        return output_path
    
    except Exception as e:
        # 更新运行记录为失败
        report_run.status = "failed"
        report_run.error_json = {"error": str(e)}
        report_run.finished_at = datetime.now()
        db.commit()
        raise


def _generate_seasonality_sheet(
    db: Session,
    workbook,
    worksheet,
    sheet_config: Dict,
    params: Dict,
    header_format,
    date_format,
    number_format
):
    """生成季节性图sheet"""
    # 支持metric_id或metric_code
    metric_id = sheet_config.get("metric_id")
    
    # 如果没有metric_id，尝试从metric_code解析
    if not metric_id:
        from app.models.metric_code_map import resolve_metric_id
        metric_code = sheet_config.get("metric_code")
        if metric_code:
            metric_id = resolve_metric_id(db, metric_code)
    
    years = params.get("years", [])
    
    if not metric_id:
        worksheet.write(0, 0, f"配置错误：无法解析metric_id (sheet_config: {sheet_config})")
        return
    
    if not years:
        worksheet.write(0, 0, "配置错误：缺少years参数")
        return
    
    # 查询季节性数据
    filters = {
        "geo_ids": params.get("geo_ids") or [],
        "company_ids": params.get("company_ids") or []
    }
    
    # 确保filters中的列表不为None
    if not filters["geo_ids"]:
        filters.pop("geo_ids", None)
    if not filters["company_ids"]:
        filters.pop("company_ids", None)
    
    result = query_seasonality(
        db=db,
        metric_id=metric_id,
        years=years,
        filters=filters if filters else None,
        x_mode=sheet_config.get("x_mode", "week_of_year"),
        agg=sheet_config.get("agg", "mean")
    )
    
    # 调试信息：记录查询结果
    if not result.get("x_values") or not result.get("series"):
        worksheet.write(1, 0, f"查询结果为空")
        worksheet.write(2, 0, f"metric_id: {metric_id}")
        worksheet.write(3, 0, f"years: {years}")
        worksheet.write(4, 0, f"filters: {filters}")
        return
    
    # 写入表头
    worksheet.write(0, 0, "X轴", header_format)
    col = 1
    for year in years:
        worksheet.write(0, col, f"{year}年", header_format)
        col += 1
    
    # 写入数据
    x_values = result.get("x_values", [])
    series = result.get("series", [])
    
    if not x_values or not series:
        worksheet.write(1, 0, "无数据：查询结果为空")
        worksheet.write(1, 1, f"metric_id={metric_id}, years={years}")
        return
    
    # query_seasonality返回的格式是: series = [{"year": 2021, "values": [val1, val2, ...]}, ...]
    # x_values和values数组长度相同，按索引对应
    
    for row_idx, x_val in enumerate(x_values, start=1):
        worksheet.write(row_idx, 0, x_val)
        
        for col_idx, year in enumerate(years, start=1):
            # 查找对应年份的series
            year_series = next((s for s in series if s.get("year") == year), None)
            if year_series:
                values = year_series.get("values", [])
                # x_values和values按索引对应
                if row_idx - 1 < len(values):
                    value = values[row_idx - 1]
                    if value is not None:
                        worksheet.write(row_idx, col_idx, value, number_format)
    
    # 生成图表
    if len(x_values) > 0 and len(series) > 0:
        chart = workbook.add_chart({'type': 'line'})
        
        # 添加数据系列（每年一条线）
        for col_idx, year in enumerate(years, start=1):
            year_series = next((s for s in series if s.get("year") == year), None)
            if year_series:
                # 数据范围：从第2行开始（第1行是表头），到数据结束
                # X轴：A列（第1列），从A2到A{数据行数+1}
                # Y轴：对应年份列，从B2到B{数据行数+1}（col_idx从1开始，对应B列）
                col_letter = chr(ord('A') + col_idx)
                excel_sheet_name = sheet_config.get("_excel_sheet_name", sheet_config.get("name", "Sheet1"))
                x_range = f"'{excel_sheet_name}'!$A$2:$A${len(x_values) + 1}"
                y_range = f"'{excel_sheet_name}'!${col_letter}$2:${col_letter}${len(x_values) + 1}"
                
                chart.add_series({
                    'name': f'{year}年',
                    'categories': x_range,
                    'values': y_range,
                    'line': {'width': 1.5}
                })
        
        # 设置图表属性
        chart.set_title({'name': sheet_config.get("title", "季节性分析图表")})
        chart.set_x_axis({
            'name': 'X轴' if sheet_config.get("x_mode") == "week_of_year" else "月-日",
            'name_font': {'size': 10}
        })
        chart.set_y_axis({
            'name': result.get("meta", {}).get("unit", "数值"),
            'name_font': {'size': 10}
        })
        chart.set_legend({'position': 'bottom'})
        chart.set_size({'width': 720, 'height': 480})
        
        # 插入图表（在数据表下方，留出一些空间）
        chart_row = len(x_values) + 3
        worksheet.insert_chart(f'A{chart_row}', chart)


def _generate_timeseries_sheet(
    db: Session,
    workbook,
    worksheet,
    sheet_config: Dict,
    params: Dict,
    header_format,
    date_format,
    number_format
):
    """生成时间序列图sheet"""
    # 支持多种配置方式：
    # 1. metric_ids: [1, 2, 3]
    # 2. metrics: [{"metric_id": 1}, {"metric_id": 2}]
    # 3. metric_id: 1 (单个指标)
    # 4. metric_code: "SPREAD_STANDARD_FATTY" (需要解析)
    
    metric_ids = []
    
    # 方式1: 直接使用metric_ids数组
    if "metric_ids" in sheet_config and sheet_config["metric_ids"]:
        metric_ids = sheet_config["metric_ids"]
    
    # 方式2: 从metrics数组中提取metric_id
    elif "metrics" in sheet_config and sheet_config["metrics"]:
        for metric_config in sheet_config["metrics"]:
            if "metric_id" in metric_config:
                metric_ids.append(metric_config["metric_id"])
    
    # 方式3: 单个metric_id
    elif "metric_id" in sheet_config:
        metric_ids = [sheet_config["metric_id"]]
    
    # 方式4: 从metric_code解析（如果模板中还有metric_code）
    if not metric_ids:
        from app.models.metric_code_map import resolve_metric_id
        metric_code = sheet_config.get("metric_code")
        if metric_code:
            metric_id = resolve_metric_id(db, metric_code)
            if metric_id:
                metric_ids = [metric_id]
    
    date_range = params.get("date_range")
    
    if not metric_ids:
        worksheet.write(0, 0, f"配置错误：无法解析metric_id (sheet_config: {sheet_config})")
        return
    
    if not date_range:
        worksheet.write(0, 0, "配置错误：缺少date_range参数")
        return
    
    # 查询时间序列数据
    geo_ids = params.get("geo_ids") or []
    company_ids = params.get("company_ids") or []
    
    result = query_timeseries(
        db=db,
        date_range=date_range,
        metric_ids=metric_ids,
        geo_ids=geo_ids if geo_ids else None,
        company_ids=company_ids if company_ids else None,
        time_dimension=sheet_config.get("time_dimension", "daily")
    )
    
    # 调试信息：记录查询结果
    if not result.get("categories") or not result.get("series"):
        worksheet.write(1, 0, f"查询结果为空")
        worksheet.write(2, 0, f"metric_ids: {metric_ids}")
        worksheet.write(3, 0, f"date_range: {date_range}")
        return
    
    # 写入表头
    worksheet.write(0, 0, "日期", header_format)
    col = 1
    for series in result.get("series", []):
        worksheet.write(0, col, series.get("name", ""), header_format)
        col += 1
    
    # 写入数据
    categories = result.get("categories", [])
    series_list = result.get("series", [])
    
    if not categories or not series_list:
        worksheet.write(1, 0, "无数据：查询结果为空")
        worksheet.write(1, 1, f"metric_ids={metric_ids}, date_range={date_range}")
        return
    
    # query_timeseries返回的格式是: series = [{"name": "...", "data": [[date_str, value], ...]}, ...]
    # categories是所有日期列表，series中每个系列的data是[[date_str, value], ...]格式
    
    for row_idx, date_str in enumerate(categories, start=1):
        worksheet.write(row_idx, 0, date_str, date_format)
        
        for col_idx, series in enumerate(series_list, start=1):
            value = None
            data_points = series.get("data", [])
            # data_points格式: [[date_str, value], [date_str, value], ...]
            for point in data_points:
                if isinstance(point, (list, tuple)) and len(point) >= 2:
                    if point[0] == date_str:
                        value = point[1]
                        break
            
            if value is not None:
                worksheet.write(row_idx, col_idx, value, number_format)
    
    # 设置列宽
    worksheet.set_column(0, 0, 12)  # 日期列
    for i in range(1, len(series_list) + 1):
        worksheet.set_column(i, i, 15)
    
    # 生成图表
    if len(categories) > 0 and len(series_list) > 0:
        chart = workbook.add_chart({'type': 'line'})
        
        # 添加数据系列
        excel_sheet_name = sheet_config.get("_excel_sheet_name", sheet_config.get("name", "Sheet1"))
        for col_idx, series in enumerate(series_list, start=1):
            col_letter = chr(ord('A') + col_idx)
            x_range = f"'{excel_sheet_name}'!$A$2:$A${len(categories) + 1}"
            y_range = f"'{excel_sheet_name}'!${col_letter}$2:${col_letter}${len(categories) + 1}"
            
            chart.add_series({
                'name': series.get("name", f"系列{col_idx}"),
                'categories': x_range,
                'values': y_range,
                'line': {'width': 1.5}
            })
        
        # 设置图表属性
        chart.set_title({'name': sheet_config.get("title", "时间序列图表")})
        chart.set_x_axis({
            'name': '日期',
            'name_font': {'size': 10}
        })
        chart.set_y_axis({
            'name': '数值',
            'name_font': {'size': 10}
        })
        chart.set_legend({'position': 'bottom'})
        chart.set_size({'width': 720, 'height': 480})
        
        # 插入图表（在数据表下方）
        chart_row = len(categories) + 3
        worksheet.insert_chart(f'A{chart_row}', chart)
