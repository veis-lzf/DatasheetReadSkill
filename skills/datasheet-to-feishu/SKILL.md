---
name: datasheet-to-feishu
description: Use when the user provides an IC datasheet PDF and wants a Feishu (Lark) cloud document generated with chip analysis. Triggers on "生成飞书文档", "生成云文档", "总结成文档", "整理到飞书", "写成报告", "出一份分析文档". Combines datasheet PDF parsing with lark-doc document creation into one end-to-end pipeline.
---

# Datasheet → 飞书云文档 端到端生成器

读取 IC 数据手册 PDF，深度分析所有技术维度，自动生成结构完整、图文并茂的飞书云文档。

---

## 前置条件

执行前必须确认：

1. **`datasheet` skill 可用** — 负责 PDF 解析、图片导出、文本提取
2. **`lark-doc` skill 可用** — 负责飞书文档创建与更新
3. **已完成飞书登录** — 运行 `lark-cli auth login` 并完成授权
4. **datasheet venv 已初始化** — 运行 `python .agents/skills/datasheet/scripts/setup_env.py`
5. **PDF 文件路径有效** — 确认文件存在且可读

🔴 **CHECKPOINT · 🛑 STOP：以上任一未满足，立即告知用户并等待处理，不要继续执行。**

---

## 触发条件

**触发本 skill（满足任一）：**
- 用户提供 PDF 路径 + 说「生成飞书文档/云文档/报告」
- 「总结成文档」「整理到飞书」「写成云文档」「出分析报告」
- 「打包成报告发到飞书」「做成文档」

**不触发（转其他 skill）：**
- 仅问芯片参数 → 用 `datasheet` skill
- 仅建普通飞书文档 → 用 `lark-doc` skill

---

## 完整执行流程

### 阶段一：Datasheet 全量分析

按以下 10 个维度提取信息，**每项必须标注来源页码**：

| # | 提取维度 | 具体内容 | 失败处理 |
|---|---------|---------|---------|
| 1 | **芯片概述** | 型号、制造商、产品定位、核心功能 | 若首页无概述 → 从 Features + Description 合并推断 |
| 2 | **关键特性** | Features 章节全量，含电压/电流/温度范围 | 若无独立章节 → 从 Electrical Characteristics 提取 |
| 3 | **应用场景** | Applications 逐条分析使用方式 | 若无此章节 → 标注「数据手册未列出，基于功能推断」 |
| 4 | **引脚配置** | 每个引脚名称、方向、功能（所有封装） | 若引脚图为扫描图像 → 导出图片用视觉分析 |
| 5 | **逻辑功能表** | 完整真值表/功能表，含所有工作模式 | 若无表格 → 从文字描述重建 |
| 6 | **绝对最大额定值** | 电压/电流/温度极限 | 若缺失 → 警告用户「此项未找到，设计时参考推荐工作条件上限」 |
| 7 | **推荐工作条件** | 工作电压/输入输出特性参数表 | 若无独立章节 → 从 Electrical Characteristics 筛选 |
| 8 | **开关特性** | tpd/tpZH/tpZL 等时序参数 | 若无此章节 → 标注「数据手册未提供时序参数」 |
| 9 | **封装信息** | 所有封装类型、尺寸、引脚数 | 若无尺寸图 → 导出封装图页为图片分析 |
| 10 | **版本历史** | Revision History，当前版本关键变更 | 若无此章节 → 跳过并在文档注明 |

**图表页处理：**
- 发现图表/框图/时序图页面 → 导出为图片，用视觉能力分析
- 每张图写一条**图片说明**：`📊 [原文 Figure/Table N]：<内容描述> — <工程意义>`

### 阶段二：飞书文档创建

🔴 **执行前必读（缺一不可）：**
- `.agents/skills/lark-doc/references/lark-doc-xml.md`
- `.agents/skills/lark-doc/references/style/lark-doc-style.md`
- `.agents/skills/lark-doc/references/style/lark-doc-create-workflow.md`

**四波并行策略（Code-Act Loop）：**

**第一波（串行）— 建骨架：**
```bash
lark-cli docs +create --api-version v2 --content '<title>{芯片型号} 数据手册深度分析报告</title>
<callout emoji="📌" background-color="light-blue">
<p><b>摘要：</b>{一句话芯片描述，含关键参数}</p>
</callout>
<h1>一、芯片概述</h1><p>占位</p>
<h1>二、关键电气特性</h1><p>占位</p>
<h1>三、引脚配置与功能</h1><p>占位</p>
<h1>四、工作原理与逻辑分析</h1><p>占位</p>
<h1>五、封装选型指南</h1><p>占位</p>
<h1>六、典型应用场景深度分析</h1><p>占位</p>
<h1>七、电路设计要点</h1><p>占位</p>
<h1>八、与同类芯片对比</h1><p>占位</p>
<h1>九、设计总结与选型建议</h1><p>占位</p>'
```
> ⚠️ `--content` 只传骨架，**绝不**把完整章节内容一次性塞入。

**第二波（并行）— 写正文：**
- spawn Agent 并行写入各章节（用 `block_insert_after`）

**第三波（串行）— 审查：**
```bash
lark-cli docs +fetch --api-version v2 --doc {token} --detail with-ids
```

**第四波（并行）— 插图 + 润色：**
- SVG SubAgent 绘制功能框图
- 主 Agent 写 Mermaid 决策树

**图表类型对照：**

| 内容类型 | 插入方式 |
|---------|---------|
| 内部功能框图 | `<whiteboard type="svg">` SubAgent |
| 选型决策树 | `<whiteboard type="mermaid">` 内嵌 |
| 电气参数表 | `<table>` 带表头背景色 |
| 注意事项 | `<callout>` emoji + 背景色 |
| 两方案对比 | `<grid>` 双栏 |
| 电路连接示意 | `<pre lang="text">` |

---

## 失败模式与恢复

| 触发条件 | 一线修复 | 仍失败时兜底 |
|---------|---------|------------|
| PDF 路径不存在 | 提示用户确认路径 | 请用户重新提供完整路径 |
| `setup_env.py` 失败 | 检查 Python 版本（需 3.8+） | 手动安装：`pip install pymupdf` |
| PDF 文字提取乱码 | 对该页切换为图片模式 | 全文用图片模式处理 |
| 飞书未登录（401） | 运行 `lark-cli auth login` | 确认 `lark-cli config init` |
| `docs +create` 内容超限 | 只传骨架，正文用 `append` 写入 | 拆分为更小的 `block_insert_after` 批次 |
| SVG SubAgent 失败 | 改用 `<whiteboard type="mermaid">` | 降级为 `<table>` |
| 竞品数据无法获取 | 从通用知识推断，标注「基于公开资料」 | 跳过该章节，在文档中注明 |
| `docs +fetch` 超时 | 等待 5 秒后重试 | 跳过第三波，直接进入第四波 |

---

## ❌ 反模式黑名单

| # | 不要做 | 后果 | 正确做法 |
|---|--------|------|---------|
| 1 | 完整章节内容塞入 `--content` | lark-cli 参数超限，失败 | 第一波只建骨架，正文分批写入 |
| 2 | 跳过 `lark-doc-xml.md` 直接写 XML | 格式错误，文档创建失败 | 执行前必读 XML 语法文件 |
| 3 | `str_replace --old-str` 替换多行 | 不支持跨 block，报错 | 改用 `block_replace --block-id` |
| 4 | 图片模式处理 500+ 页全文 | 超时，磁盘爆满 | TOC 路由定位目标章节，只导出必要页 |
| 5 | 并行写入同一章节的多个段落 | block 顺序混乱 | 同章节内串行，不同章节才并行 |
| 6 | 编造竞品具体参数 | 工程师按错误参数设计电路 | 未知参数标注「请查阅原厂手册」 |
| 7 | PDF 解析失败时静默继续 | 文档内容残缺无警告 | 失败章节写入 `<callout emoji="⚠️">` |

---

## 质量自检清单

文档生成后必须逐项检查（**全部通过才算完成**）：

- [ ] 每章 h1/h2 下至少有 1 个非纯文本 block
- [ ] 连续纯文本 `<p>` 不超过 3 段
- [ ] 文档开头有 `<callout>` front-load 结论
- [ ] 数据手册中有意义的图/表均有图片说明段落
- [ ] 关键参数值用颜色标注（含 ↑↓ 方向符号）
- [ ] 竞品对比表优势用 green、劣势用 red
- [ ] 各主题章节间有 `<hr/>`
- [ ] 最终章节有 Mermaid 选型决策树
- [ ] 所有提取失败项已用 warning callout 标注

🔴 **CHECKPOINT · 🛑 STOP：清单有任一未通过，修复后再交付。**

---

## 调用接口（供其他 Agent 使用）

```
@datasheet_to_feishu(
  pdf:          "<path>",
  parent_token: "<token>",             // 可选：目标文件夹 token
  depth:        "overview" | "full",   // 默认 full
  competitor:   "<chip1>,<chip2>",     // 可选：指定竞品
)
// 返回：{"url": "https://xxx.feishu.cn/docx/xxx", "status": "ok"}
```

---

## 依赖关系

```
datasheet-to-feishu
├── datasheet          PDF 解析 · 图片导出 · 文本/表格提取
└── lark-doc           飞书文档创建/更新/SVG 画板
    ├── lark-doc-xml.md        （必读）
    ├── lark-doc-style.md      （必读）
    └── lark-doc-create-workflow.md  （必读）
```
