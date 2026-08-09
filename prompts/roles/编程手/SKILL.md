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
3. **P1 竞争对比表**（候选模型指标对比 + 淘汰决策）
4. 三类图（`raw_`/`process_`/`result_`），每类 ≥3 张，覆盖全部子问题，共 ≥9 张
5. `results/复现清单.json`

## 执行顺序
1. **环境检查**：`python check_env.py --features <所需功能>`
2. **P1 质量门（竞争淘汰）**：在同一 mini-batch 数据集上，运行建模手产出的全部候选模型（2-3 个）。
   - 产出 **竞争对比表**（核心指标 + 运行时间 + 数据假设满足度）。
   - 根据定量结果淘汰：复杂模型全指标不如简单基准则淘汰；指标接近（差距 < 10%）则全部保留；物理意义错误则立即淘汰。
   - 若所有候选均不满足要求 → 触发**二阶回退**，通知建模手重建候选池。
   - 须包含数据筛选的领域理由说明。
   - 竞争对比表作为后续论文中"模型选择依据"的素材保留。
3. **实现模型** → 运行 → 校验结果合理性。
4. **结果可靠性与稳健性分析**：根据题目类型选择合适方式——测量类做不确定度合成，预测类做误差分析与交叉验证，优化类做灵敏度分析。对关键参数做敏感性扫描，验证结论在参数波动范围内是否稳定。**若敏感性扫描发现结论在合理参数范围内不稳定，或关键结果与已知事实矛盾，触发二阶回退。**
5. **可视化**（P1 之后执行数据剖析）：
   - 每图先写"一图一句结论"（figure contract）
   - raw_ 图须标注被筛选剔除的数据区域及理由
   - 调用 `utils/visual.py` 或直接使用 matplotlib，应用出版级样式
   - 保存 PNG（≥300 DPI）+ SVG 双格式
   - 运行 `python references/roles/编程手/scripts/figure_audit.py figures/`
6. **生成复现清单**：`python references/roles/编程手/scripts/repro_manifest.py`
7. **P2 质量门**：派发只读 Subagent 核验代码、图、表、复现清单。
8. 按 P2 回执返工。
9. **更新 AI 使用台账**：填写 `references/AI使用台账模板.md` 编程阶段行。

## 教练核验点

在以下节点暂停，切换旁观视角自检：

1. **P1 通过后**：输出数量级合理吗？数据筛选的领域理由充分吗？竞争淘汰的决策有数据支撑吗？保留的候选间差异是否足够形成论文中的模型对比？
2. **稳健性分析后**：关键参数敏感性扫描覆盖了吗？结论在波动范围内稳定吗？
3. **交付前**：图和表格能独立讲清故事吗？复现清单完整吗？

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
