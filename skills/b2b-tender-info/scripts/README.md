# scripts/

可执行代码（Python / Shell）。

## 约定
- 每个脚本必须有 `if __name__ == "__main__":` 入口
- 参数通过 argparse / 环境变量传递
- 输出到 stdout（不写文件除非显式指定）
- 配套的 README 写在本目录（如 `scripts/README.md`）说明调用方式

## 本 skill 可用脚本
（暂无 — 待按需添加）

### 候选脚本需求
- `tender_scraper.py` — 按关键词对指定招标平台执行批量搜索并输出结构化 JSON
- `tender_filter.py` — 按品类/预算/地区/截止日期对招标列表做二次筛选
- `tender_monitor.py` — 定时扫描特定关键词的新招标，增量输出（配套 cronjob 使用）
