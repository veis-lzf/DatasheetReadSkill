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
