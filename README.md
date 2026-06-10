# DatasheetReadSkill

> 一行命令，将 IC 数据手册 PDF 秒变结构完整的飞书云文档。

[![Agent Skills Standard](https://img.shields.io/badge/Agent%20Skills-Standard-blue)](https://agentskills.io)
[![Multi-Runtime](https://img.shields.io/badge/Runtime-Multi--Runtime-green)](https://agentskills.io)

---

## 包含的 Skills

| Skill | 功能 |
|-------|------|
| [`datasheet`](skills/datasheet/) | 读取 IC 数据手册 PDF，提取电气参数、引脚定义、时序图等技术信息 |
| [`datasheet-to-feishu`](skills/datasheet-to-feishu/) | 端到端流水线：分析 datasheet → 生成飞书云文档（图文并茂） |

---

## 快速安装

```bash
# 安装全部 skills（推荐）
npx skills install https://github.com/veis-lzf/DatasheetReadSkill.git
```

支持的 runtime：Claude Code、Codex、Cursor、OpenClaw、Trae 等所有兼容 [Agent Skills Standard](https://agentskills.io) 的工具。

---

## 使用方式

### 仅分析 datasheet
```
这是 RS1G125.pdf，帮我提取引脚定义和电气特性
```

### 生成飞书云文档（完整流程）
```
C:\Downloads\STM32F103.pdf，帮我生成飞书云文档
```
```
把这个 datasheet 整理到飞书，要有竞品对比分析
```

---

## 生成文档包含

- 芯片概述（产品定位 + 核心优势 Grid 双栏）
- 关键电气特性（参数表格，关键值颜色标注）
- 引脚配置与功能（引脚表 + SVG 功能框图）
- 工作原理与逻辑分析（逻辑功能表）
- 封装选型指南（三种封装对比）
- 典型应用场景深度分析（逐场景分析）
- 电路设计要点（反模式黑名单 + 设计规则表）
- 与同类芯片对比（竞品对比表）
- 设计总结与选型建议（Mermaid 决策树）

示例：[RS1G125 分析结果](examples/RS1G125-sample-output.md)

---

## 前置要求

1. **Python 3.8+** — 用于 PDF 解析脚本
2. **飞书账号** — 需完成 `lark-cli auth login`
3. **lark-cli** — 飞书文档 CLI 工具

首次使用时，skill 会自动引导初始化 Python 虚拟环境。

---

## 仓库结构

```
DatasheetReadSkill/
├── README.md
├── skills/
│   ├── datasheet/
│   │   ├── SKILL.md
│   │   ├── references/workflow_guide.md
│   │   └── scripts/
│   │       ├── setup_env.py
│   │       ├── generate_context.py
│   │       ├── parse_toc.py
│   │       ├── extract_pages.py
│   │       ├── extract_tables.py
│   │       └── export_page_images.py
│   └── datasheet-to-feishu/
│       ├── SKILL.md
│       └── test-prompts.json
└── examples/
    └── RS1G125-sample-output.md
```

---

## License

MIT

---

## 更新日志

### v2.1.0 (2026-06-09) — Darwin 优化版

经 Darwin Skill 9 维度评估优化，评分从 **69.0/99 → 84.9/99**（+15.9）。

#### 新增 ✅
- **🔴 CHECKPOINT / 🛑 STOP 检查点**: Step 0（生成 context 前）、Step 0.5 Phase C（路由计划确认）、Step 2B Phase 1（提取计划确认）三处显式闸门
- **🚫 反例与黑名单**: 独立章节 12 条禁止行为（流程安全 5 条 + 输出质量 4 条 + 资源管理 3 条），每条含「禁止 → 原因 → 正确做法」
- **失败模式与异常处理**: 16 条三段式 fallback（触发条件 → 一线修复 → 仍失败兜底），覆盖环境/缓存/TOC/页面/表格/图像/路由全部关键路径
- **⚡ 快速路径豁免**: 单 PDF + 针对性问题跳过跨文档路由分析，直达 Step 1

#### 修复 🔧
- **资源路径一致性**: 8 处脚本路径从 `datasheet_reader/scripts/` 修正为 `datasheet/scripts/`，与安装目录名一致
- **Interface Spec 契约对齐**: `query` 和 `summarize` action 说明中明确快速路径 vs 完整路由的区别
- **内容去冗余**: 消除修复历史重复段落，重要 Notes 与失败模式表交叉引用

### v2.0.0
- 初始版本：双路径策略（≤15 页全图 / >15 页 TOC 定位）、跨文档预分析、citation 体系
