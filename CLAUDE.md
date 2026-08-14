# CLAUDE.md

> 本仓库已迁移为 **Claude Code 原生 Skill**（v1.6.0）。编排逻辑与系统指令已从本文件迁移至根目录 `SKILL.md`。

## 安装为技能（推荐）

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 复制到用户技能目录（与第三方 math-modeling 技能并存，不冲突）
cp -r . ~/.claude/skills/mcm-ai-assistant

# 3.（可选）注册质量门 Subagent，便于按名原生派发
mkdir -p ~/.claude/agents && cp .claude/agents/*.md ~/.claude/agents/
```

安装后，在任意赛题项目目录启动 `claude`，对 AI 说「用 mcm-ai-assistant 处理这道赛题」即可触发完整三角色流水线。

## 关键入口

- 技能入口：`SKILL.md`（10 条强制约束 + 三角色路由 + 渐进加载 + 质量门 + 竞争/回退机制 + 模型速查）
- 角色文档：`references/roles/{建模手,编程手,论文手}/SKILL.md`
- 质量门 Subagent：`.claude/agents/{m1,p1,p2,w1,w2}-gate.md`
- 详细说明：`README.md`

若你仍想把本仓库当作工作项目直接使用（在仓库内做题），完整系统指令见 `SKILL.md`；旧版 `CLAUDE.md` 全文见 git 历史（v1.5.0 及之前）。
