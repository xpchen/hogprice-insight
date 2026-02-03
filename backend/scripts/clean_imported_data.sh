#!/bin/bash
# 清理导入数据脚本

echo "================================================================================"
echo "清理导入数据脚本"
echo "================================================================================"
echo ""
echo "此脚本将清理以下数据："
echo "  - 期货日度数据 (fact_futures_daily)"
echo "  - 期权日度数据 (fact_options_daily)"
echo "  - 指标时序数据 (fact_indicator_ts)"
echo "  - 指标metrics (fact_indicator_metrics)"
echo "  - 导入批次 (import_batch)"
echo "  - 导入错误 (ingest_error)"
echo "  - 导入映射 (ingest_mapping)"
echo ""
echo "默认保留合约维度表数据 (dim_contract, dim_option)"
echo "如需清理合约维度表，请使用: python scripts/clean_imported_data.py --remove-contracts"
echo ""

cd "$(dirname "$0")/.."
python scripts/clean_imported_data.py
