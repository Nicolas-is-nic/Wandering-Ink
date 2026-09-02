# 诗词行旅（Wandering-Ink）

纯叙事沉浸式 Web 游戏：以一生为卷轴，跟随历史文人走过关键人生节点，在处境中遇见诗词。首发内容为「苏轼 · 黄州」一章。

设计文档见 `claude_docs/2026-09-02-诗词行旅-设计文档.md`。

## 快速开始

依赖：[uv](https://docs.astral.sh/uv/)、Python 3.11+（环境由 uv 管理，不用系统 Python）。

```bash
# 初始化环境（首次）
uv venv .venv
uv pip install --python .venv/bin/python pyyaml

# 构建静态站
.venv/bin/python build/build.py

# 本地预览（任选其一）
cd dist && python3 -m http.server 8741
# 或直接双击 dist/index.html（数据已内联，file:// 可玩，无任何网络请求）
```

## 目录结构

```
figures/                 人物包（多人物框架核心：加人物 = 加目录）
  su-shi/
    metadata.yaml        人物元数据 + places 古今地名对照表
    chapters/huangzhou.yaml   黄州章（27 场景，9 篇诗文）
  li-bai/ xin-qiji/      planned 占位包（验证框架，首页置灰展示）
build/build.py           构建脚本：schema 强校验 + 渲染 + 校对清单 + 占位 SVG
site/templates/          页面骨架模板（首页 / 人物页 / 章节页）
site/css/ site/js/       美学 token 与交互（零依赖，无框架）
dist/                    构建产物（纯静态，可直接托管）
claude_docs/             设计文档
```

## 构建产物

| 文件 | 用途 |
|---|---|
| `dist/index.html` | 首页人物星空（published 可入，planned 置灰） |
| `dist/figures/<id>/index.html` | 人物页：简介 + SVG 足迹卷轴 + 章节列表 |
| `dist/figures/<id>/chapters/<章>.html` | 章节页：左右翻页场景流（箭头/方向键/滑动，明度反转、诗词展品式排版） |
| `dist/proof-list.md` | 校对清单：文本与出处并列，交其他模型交叉校对 |
| `dist/placeholder-list.md` | 占位图清单：后期 AI 插画批量替换的依据 |
| `dist/data/*.json` | 数据副本（页面本身不依赖，供外部工具消费） |

## 校验规则（构建期强制，违反即失败）

1. 每个场景 `source` 必填（出处可溯是硬约束）。
2. `type` 仅限 narrative / poem / event / letter。
3. `tone` 仅限 light / dark（明度反转 = 情绪节奏）。
4. `place` 必须能在 `metadata.places` 查到坐标。
5. poem 场景必须有 `poem_title`，建议提供 `keyline`。

## 校对工作流

1. 构建产出 `dist/proof-list.md`（当前 92 条已全部校对，2026-09-02 交叉校对报告见 `claude_docs/`）。
2. 校对核对诗词原文逐字、系年、叙事史实，修正后回填 YAML 并置 `proofed: true`。
3. 后续新增内容默认 `proofed: false`，须先交叉校对再发布。

## 已知限制（第一版）

- 插画均为占位 SVG（`placeholder/` 前缀），后期按设计文档 3.4 节风格模板用即梦批量生成替换。
- 字体走系统栈（思源宋体/黑体优先回退宋体/黑体），webfont 子集化后续再做。
- 人物页地图为零依赖 SVG 水墨卷轴（三级方案之兜底级）；高德 JS API 与 Leaflet 底图待接。
- 诗词与系年已完成一轮交叉校对（2026-09-02，修正 3 处错误），后续新增内容仍需走校对流程。
