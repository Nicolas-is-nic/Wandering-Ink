# AGENTS.md — 诗词行旅（Wandering-Ink）

## 项目简介

纯叙事沉浸式 Web 游戏：以一生为卷轴，跟随历史文人（首发：苏轼）走过关键人生节点，在处境中遇见诗词。核心体验 = 先被卷入人物的处境，再拿到诗词，让诗词成为情绪出口。

当前状态：**已上线**。苏轼七章 92 场景（眉州 → 名动京师 → 宦游 → 黄州 → 元祐 → 岭海 → 北归）、20 篇诗文、53 张水墨插画，全部内容交叉校对闭环。李白 / 辛弃疾为 planned 占位包，框架就绪未开发。

- 线上地址：https://nicolas-is-nic.github.io/Wandering-Ink/（GitHub Pages，源为 gh-pages 分支）
- 技术形态：多人物数据包框架（`figures/`）+ Python 构建脚本（`build/build.py`，schema 强校验与渲染）→ 零依赖静态站（`dist/`，不入库）
- 设计文档（唯一权威 spec）：`claude_docs/2026-09-02-诗词行旅-设计文档.md`

## 目录职责

| 目录/文件 | 说明 | 是否入库 |
|---|---|---|
| `figures/` | 人物数据包（加人物 = 加目录，前端零改动） | 入库 |
| `site/` | 页面模板、CSS、JS（零依赖无框架） | 入库 |
| `build/` | 构建脚本（schema 强校验 + 渲染 + 校对清单 + 占位 SVG） | 入库 |
| `scripts/deploy.sh` | 一键部署脚本 | 入库 |
| `dist/` | 构建产物（一键重建，部署走 gh-pages） | 不入库 |
| `.gh-pages-work/` | 部署脚本的工作副本（自动创建） | 不入库 |
| `claude_docs/`、`claude_scripts/` | AI 协作产物 | 不入库 |

## 开发与部署步骤

### 0. 首次环境搭建

```bash
cd Wandering-Ink
uv venv .venv
uv pip install --python .venv/bin/python pyyaml
```

### 1. 本地构建与预览

```bash
.venv/bin/python build/build.py     # 校验失败即报错退出
# 预览（二选一）：
open dist/index.html                # 数据内联，file:// 直接可玩
cd dist && python3 -m http.server 8741   # 或起本地服务
```

### 2. 日常内容更新（改文案 / 加场景 / 换图）

1. 修改 `figures/su-shi/chapters/*.yaml`（图片放 `figures/su-shi/assets/images/`，YAML 引用 `images/xxx.jpg`）
2. 重新构建：`.venv/bin/python build/build.py`
3. 本地验证：HTML 标签配对、抽查页面内容、校对清单有无新增
4. 部署上线：`./scripts/deploy.sh`（内含构建 + 推送 gh-pages，一两分钟后线上自动更新）
5. 提交源码到 main：`git add` 相关 YAML / 资源 → commit → push（注意 dist/ 已被忽略，不会进 main）

### 3. 部署机制（已配置，无需重设）

- `scripts/deploy.sh` = 构建 + 把 dist 同步到 `.gh-pages-work/`（gh-pages 分支工作副本）+ 推送 `origin/gh-pages`
- GitHub Pages 源已设置为 **gh-pages 分支 / root**；main 分支只有源码，不含构建产物
- 不要在 Pages 设置里切回 main；不要删除远程 gh-pages 分支

### 4. 新增场景的插画流程

1. 新场景 `image` 写 `placeholder/场景名.svg`（构建自动生成水墨占位图）
2. 生成真实图：提示词规范与模板见 `claude_docs/即梦提示词-第一章-眉州.md`（四色、水墨淡彩、东坡巾锁身份、面部不细节刻画、无文字）
3. 图放 `figures/su-shi/assets/images/场景名.jpg`（JPG，质量 60，长边 1280）
4. YAML 改为 `image: images/场景名.jpg`，重建；`dist/placeholder-list.md` 自动只登记剩余占位图

### 5. 校对流程

1. 新增内容默认 `proofed: false`，构建产出 `dist/proof-list.md`（仅列待校对项）
2. 交其他模型交叉校对：诗词原文逐字、系年、叙事史实、出处
3. 修订回填 YAML，置 `proofed: true`，重建

## 开发规则（后续所有改动必须遵循）

### 1. 美学基调：数字水墨 x 博物馆展签

- 色板锁死四色：宣纸白 `#F5F1E8`、墨黑 `#1A1A1A`、朱砂红 `#C0392B`、黛蓝 `#2C3E50`。允许同色相衍生色阶，禁止出现色板外高饱和色。
- 明度反转 = 情绪节奏：沉重场景（狱中、孤鸿、寒食）`tone: dark` 整页铺墨黑底、宣纸白字；豁然场景回归宣纸白。新场景定 tone 必须给出情绪依据。
- 8pt 网格；标题大字号、大留白。
- 图标一律 SVG 手绘，禁止用 emoji 充当图标。

### 2. 字体：三栈分层，字体切换即信号

| 用途 | 栈 |
|---|---|
| 大标题、诗词本体 | 衬线：Noto Serif SC / Songti SC / serif |
| 叙事正文 | 无衬线：Noto Sans SC / PingFang SC / sans-serif |
| 书信引文、keyline 点睛句 | 楷体：Kaiti SC / STKaiti / KaiTi |

诗词按"展品"处理，不按正文处理。字体切换本身就是"诗来了"的仪式感信号，不要加额外提示框。引入 webfont 必须子集化。

### 3. 文字风格（以黄州章 YAML 为基准，改文风先对照它）

- 叙事一律第二人称"你"，沉静、有画面、克制；不堆砌辞藻，不在结尾煽情评论，不替玩家总结感受。
- 诗词是情绪出口不是展品陈列：先铺垫处境到极致，再落诗；诗出现时不配图，画面安静。
- 史实锚定：时间、官职、事件以孔凡礼《苏轼年谱》为准；细节演绎必须在 `notes` 里标注"待校 / 演绎"；版本异文（如"樯橹一作强虏"）写进 notes，不改动正文。
- 每个场景 `source` 必填且落到具体卷次/条目（构建期强校验，缺失即失败）。诗词原文以底本为准，新增内容默认 `proofed: false`，校对走 `dist/proof-list.md` 交叉校对流程，校完回填 `proofed: true`。
- 诗文选目原则：不堆砌、不吝啬。凡难以取舍的，说明都是好作品，一律展示；但系年拿不准的一律不入选。
- 扩写时保持密度：narrative 场景 3-6 段，每段 60-120 字；event 卡 2-3 段 + 一句收束。

### 4. 动效与交互：文本是唯一主角，动效只做情绪渲染

- 章节页是左右翻页制（页数随章而定）：左右箭头按钮、`←`/`→`、PageUp/Down、移动端横滑、底部页码 `06 / 29`、hash 定位。禁止改回纯纵向滚动。
- 页面进入动画：0.55s 轻位移淡入（translateX 32px），起始态必须保持可读（opacity 起始 0.4 + `anim-done` JS 兜底），防止后台标签页动画冻结导致空白。
- 其他动效上限：位移 ≤32px、时长 ≤1.1s、opacity/transform 优先。禁止闪烁、弹跳、视差滚动这类抢戏效果。
- 插图低饱和弱化（`filter: saturate(.55) contrast(.92)`），poem 场景不放插画。
- 无 JS 环境必须可读：翻页显隐规则一律带 `.js` 前缀；页面无任何网络请求，file:// 直接可玩。改动后必须回归验证这一点。
- 顶部阅读进度线：首页/人物页按滚动，章节页按页码。

### 5. 地图

- 人物页当前是零依赖 SVG 水墨卷轴（三级底图方案的兜底级）：动态经纬边界、相邻弧线交替拱向 + 方向箭头、近址节点多轮分离、标签上下交替避让。改投影逻辑时保持这四点。
- 章节内地图降权为场景角落地名小标记，点击浮签。接入高德 JS API（主选）或 Leaflet（备选）时，SVG 卷轴保留为降级兜底，地图不得干扰叙事主体。

### 6. 数据包 schema（改 schema 比改内容严重得多）

- `type` 仅限 narrative / poem / event / letter；`tone` 仅限 light / dark；场景无分支无状态。
- `place` 一律引用 `metadata.yaml` 的 `places` 字典（全包唯一坐标源），scene 内不存坐标。
- poem 场景必须有 `poem_title`，建议 `keyline`（前端书法大字）；有节选必须写 `excerpt`（校对清单的核对范围）。
- 给 schema 加字段前先在设计文档登记；删字段前先确认无数据依赖。
- 构建期校验规则只增不减；改校验逻辑必须跑负测试（人为破坏 source/place/type 确认构建报错）。

### 7. 工作流约定

- Python 一律走 uv 全新环境（`.venv`），任何 pip 操作前确认目标环境。
- `claude_docs/`、`claude_scripts/`、`dist/`、`.gh-pages-work/` 不入 git；代码文件英文命名，生成文档中文命名，代码注释中文，禁止 emoji。
- 图片资产入库（`figures/<人物>/assets/images/`，JPG 质量 60-85、长边 1280-1600），压缩换格式统一处理，勿单张随意替换。
- 任何内容/模板/脚本改动后：重新构建 → 检查 HTML 标签配对 → 抽查页面关键内容 → 确认校对清单更新。改文案必须重跑构建，不要手改 dist。
