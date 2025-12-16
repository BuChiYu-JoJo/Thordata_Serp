# Thordata_Serp

## 使用方法

### 基本参数
- `-k/--api-key`：必填，Thordata/SerpAPI 密钥
- `-e/--engines`：要测试的引擎列表；或使用 `--all-engines` 运行全部支持引擎
- `-t/--duration`：每个引擎的运行时长（秒）
- `-c/--concurrency`：并发数（默认 5）
- `--concurrency-steps`：连续执行的并发列表（如 `--concurrency-steps 20 50`），会按顺序跑多组并发并汇总统计
- `-q/--query`：固定关键词；未指定时按引擎的关键词池自动选择
- `--save-details`：输出每个请求的详细 CSV
- `-o/--output`：汇总统计 CSV 文件名（默认 `serpapi_summary_statistics.csv`）

### 示例
```bash
# 单并发
python Thordata_serp.py -k YOUR_API_KEY -e google -t 120 -c 10 --save-details

# 多并发序列（先 20 再 50），每档运行 3 分钟
python Thordata_serp.py -k YOUR_API_KEY -e google --concurrency-steps 20 50 -t 180 --save-details

# 所有引擎，默认并发 5，时长 60 秒
python Thordata_serp.py -k YOUR_API_KEY --all-engines -t 60
```
