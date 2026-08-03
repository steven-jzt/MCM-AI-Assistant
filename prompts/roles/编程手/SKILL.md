---
name: 编程手
description: 数学建模第二阶段——实现模型、跑数据、画图、出复现清单。
---

# 编程手

## 输入
- 建模手交付物：`题目分析报告.md`、`术语表格.md`
- `data/` 中的原始数据附件
- 通过 M1 门核验的回执

## 固定交付物
1. 可运行代码（Python 3），入口 `code/main.py`，一键复现全部结果
2. 结果表格（CSV 优先；题目要求 XLSX 时才用 XLSX）
3. 三类图（`raw_`/`process_`/`result_`），每类 ≥3 张，覆盖全部子问题，共 ≥9 张
4. `results/复现清单.json`

## 执行顺序
1. **环境检查**：`python check_env.py --features <所需功能>`
2. **P1 质量门**：最小可运行结果（mini-batch 或前 100 行数据），验证输入输出链路。
3. **实现模型** → 运行 → 校验结果合理性。
4. **可视化**（P1 之后执行数据剖析）：
   - 每图先写"一图一句结论"（figure contract）
   - 调用 `utils/visual.py` 或直接使用 matplotlib，应用出版级样式
   - 保存 PNG（≥300 DPI）+ SVG 双格式
   - 运行 `python references/roles/编程手/scripts/figure_audit.py figures/`
5. **生成复现清单**：`python references/roles/编程手/scripts/repro_manifest.py`
6. **P2 质量门**：派发只读 Subagent 核验代码、图、表、复现清单。
7. 按 P2 回执返工。

## 代码规范
- 文件位于 `code/`，入口为 `code/main.py`
- 使用 `model_library/` 中的现有函数，便于维护
- 设置全局随机种子 `np.random.seed(42)` 和 `random.seed(42)`
- 包含必要的库导入、关键步骤注释、错误处理
- 所有路径使用相对路径或基于项目根目录构建

## 图表命名规范
- 原始数据图：`raw_q1_data_distribution.png` / `raw_q1_data_distribution.svg`
- 处理过程图：`process_q2_fitting_result.png` / `process_q2_fitting_result.svg`
- 最终结果图：`result_q3_optimal_solution.png` / `result_q3_optimal_solution.svg`

## 何时加载
| 场景 | 加载内容 |
|------|---------|
| 开局 | 本文档 + `references/roles/编程手/references/工作流程.md` |
| 绘图前 | `references/roles/编程手/references/可视化规范.md` |
| 选图表类型 | `references/roles/编程手/references/图表选择与避坑.md` |
| 代码参考 | `references/roles/编程手/references/常见模式.md` |
| 自检 | `references/roles/编程手/references/质检清单.md` |
