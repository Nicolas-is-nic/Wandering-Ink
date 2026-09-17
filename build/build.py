#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诗词行旅（Wandering-Ink）静态站构建脚本。

用法：
    .venv/bin/python build/build.py

职责：
    1. 扫描 figures/ 下全部人物包（metadata.yaml + chapters/*.yaml）
    2. 按 schema 强校验（出处必填、type/tone 枚举、places 坐标查询、poem 字段）
    3. 渲染 dist/ 静态站：首页、人物页、章节页（数据内联，file:// 可直接打开）
    4. 产出校对清单 dist/proof-list.md 与占位图清单 dist/placeholder-list.md
    5. 为 placeholder/ 前缀图片自动生成占位 SVG

校验失败时列出全部错误并以非零码退出。
"""
import html
import json
import posixpath
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FIGURES_DIR = ROOT / "figures"
SITE_DIR = ROOT / "site"
DIST_DIR = ROOT / "dist"
ASSETS_DIR = DIST_DIR / "assets"

SCENE_TYPES = {"narrative", "poem", "event", "letter"}
TONES = {"light", "dark"}
STATUSES = {"published", "planned"}
DYNASTY_ORDER = ["唐", "宋", "元", "明", "清"]   # 首页朝代分组排序表；新增朝代时扩展

errors = []       # 致命错误：构建失败
warnings = []     # 警告：不阻断构建


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def load_yaml(path: Path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def esc(s):
    """HTML 转义"""
    return html.escape(str(s), quote=True)


def json_inline(data) -> str:
    """生成可安全内联进 <script> 的 JSON（防 </script> 提前闭合）"""
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------

def validate_metadata(meta: dict, pkg_dir: Path):
    fid = meta.get("id")
    if not fid:
        err(f"{pkg_dir}: metadata 缺少 id")
    status = meta.get("status", "published")
    if status not in STATUSES:
        err(f"{pkg_dir}: status 非法（{status}），仅允许 {sorted(STATUSES)}")
    for key in ("name", "one_liner", "born", "died"):
        if key not in meta:
            err(f"{pkg_dir}: metadata 缺少 {key}")
    dynasty = meta.get("dynasty", "")
    if dynasty not in DYNASTY_ORDER:
        err(f"{pkg_dir}: dynasty 非法（{dynasty or '缺失'}），仅允许 {DYNASTY_ORDER}")
    places = meta.get("places") or {}
    for name, coord in places.items():
        if not (isinstance(coord, dict) and "lng" in coord and "lat" in coord):
            err(f"{pkg_dir}: places[{name}] 缺少 lng/lat")
    for node in meta.get("route") or []:
        place = node.get("place")
        if place not in places:
            err(f"{pkg_dir}: route 引用了 places 中不存在的地名：{place}")
        if "year" not in node:
            err(f"{pkg_dir}: route[{place}] 缺少 year")
    return places


def validate_scene(sc: dict, idx: int, chapter: dict, places: dict, pkg_dir: Path):
    sid = sc.get("id", f"<第{idx}个场景缺id>")
    where = f"{pkg_dir}/{chapter.get('id')}#{sid}"
    stype = sc.get("type")
    if stype not in SCENE_TYPES:
        err(f"{where}: type 非法（{stype}），仅允许 {sorted(SCENE_TYPES)}")
    if sc.get("tone", "light") not in TONES:
        err(f"{where}: tone 非法（{sc.get('tone')}），仅允许 light/dark")
    if not sc.get("id"):
        err(f"{where}: 缺少 id")
    if not (sc.get("text") or "").strip():
        err(f"{where}: 缺少 text")
    if not (sc.get("source") or "").strip():
        # 设计文档 5.4 规则 1：出处必填，缺失即构建失败
        err(f"{where}: source 缺失或为空（出处强校验）")
    if "title" not in sc and stype != "poem":
        err(f"{where}: 非诗词场景缺少 title")
    if stype == "poem":
        if not (sc.get("poem_title") or "").strip():
            err(f"{where}: poem 场景缺少 poem_title")
        if not (sc.get("keyline") or "").strip():
            warn(f"{where}: poem 场景建议提供 keyline（点睛句）")
    place = sc.get("place")
    if place:
        if place not in places:
            # 设计文档 5.4 规则 6：place 必须能查到坐标，查不到即构建失败
            err(f"{where}: place「{place}」在 metadata.places 中不存在")
    if "year" not in sc:
        err(f"{where}: 缺少 year")
    img = sc.get("image")
    if img and not img.startswith("placeholder/"):
        real = pkg_dir / "assets" / img
        if not real.exists():
            err(f"{where}: 图片不存在：{img}")
    for note in sc.get("notes") or []:
        if not str(note).strip():
            err(f"{where}: notes 中有空条目")


# ---------------------------------------------------------------------------
# 占位 SVG 生成
# ---------------------------------------------------------------------------

def make_placeholder_svg(title: str, subtitle: str = "占位图 · 后期以 AI 水墨插画替换") -> str:
    """生成水墨风占位图：宣纸底 + 淡墨山影 + 场景标题 + 朱砂印"""
    t = esc(title)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500" viewBox="0 0 800 500">
  <defs>
    <linearGradient id="paper" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#F5F1E8"/>
      <stop offset="1" stop-color="#EAE3D4"/>
    </linearGradient>
    <linearGradient id="hill1" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#2C3E50" stop-opacity="0.35"/>
      <stop offset="1" stop-color="#2C3E50" stop-opacity="0.05"/>
    </linearGradient>
    <linearGradient id="hill2" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#1A1A1A" stop-opacity="0.28"/>
      <stop offset="1" stop-color="#1A1A1A" stop-opacity="0.03"/>
    </linearGradient>
  </defs>
  <rect width="800" height="500" fill="url(#paper)"/>
  <path d="M0,330 C120,240 200,300 300,250 C400,200 480,290 580,240 C660,200 730,260 800,230 L800,500 L0,500 Z" fill="url(#hill1)"/>
  <path d="M0,390 C140,320 260,380 400,340 C540,300 660,370 800,330 L800,500 L0,500 Z" fill="url(#hill2)"/>
  <circle cx="640" cy="110" r="46" fill="#1A1A1A" opacity="0.12"/>
  <text x="400" y="245" text-anchor="middle" font-family="Noto Serif SC, Songti SC, STSong, serif"
        font-size="44" fill="#1A1A1A" opacity="0.78" letter-spacing="10">{t}</text>
  <text x="400" y="286" text-anchor="middle" font-family="Noto Sans SC, PingFang SC, sans-serif"
        font-size="15" fill="#1A1A1A" opacity="0.45" letter-spacing="2">{esc(subtitle)}</text>
  <g transform="translate(716,414)">
    <rect width="52" height="52" fill="#C0392B" opacity="0.85" rx="4"/>
    <text x="26" y="24" text-anchor="middle" font-family="Noto Serif SC, serif"
          font-size="18" fill="#F5F1E8">占</text>
    <text x="26" y="44" text-anchor="middle" font-family="Noto Serif SC, serif"
          font-size="18" fill="#F5F1E8">位</text>
  </g>
</svg>
"""


def ensure_placeholder(rel_path: str, title: str) -> Path:
    """确保占位 SVG 存在，返回 dist 内绝对路径；非 placeholder/ 前缀的真实资产不生成"""
    if not rel_path.startswith("placeholder/"):
        return ASSETS_DIR / rel_path
    target = ASSETS_DIR / rel_path
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(make_placeholder_svg(title), encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# HTML 片段渲染
# ---------------------------------------------------------------------------

def render_text_paragraphs(text: str) -> str:
    paras = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    return "\n".join(f"      <p>{esc(p)}</p>" for p in paras)


def render_poem_lines(text: str) -> str:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    return "\n".join(f"        <p>{esc(ln)}</p>" for ln in lines)


def rel_from(page_path: str, asset_rel: str) -> str:
    """计算从页面到资源文件的相对路径"""
    return posixpath.relpath(asset_rel, posixpath.dirname(page_path))


def render_scene(sc: dict, page_path: str, fid: str) -> str:
    """渲染单个场景 section（静态 HTML，JS 仅负责淡入与浮签增强）"""
    stype = sc["type"]
    tone = sc.get("tone", "light")
    classes = f"scene scene-{stype} tone-{tone} pager-page"
    parts = [f'    <section class="{classes}" id="{esc(sc["id"])}">']
    parts.append('      <div class="scene-inner">')

    img = sc.get("image")
    if img:
        src = esc(rel_from(page_path, f"assets/figures/{fid}/{img}"))
        is_ph = img.startswith("placeholder/")
        alt = f"{esc(sc.get('title') or sc.get('poem_title'))}{' 占位插图' if is_ph else ' 场景插画'}"
        parts.append(
            f'        <figure class="scene-img"><img src="{src}" alt="{alt}" loading="lazy"></figure>'
        )

    meta_bits = []
    if sc.get("place"):
        # 地名小标记：地图降权后的章节内定位提示，点击浮签
        meta_bits.append(
            f'<button class="place-mark" type="button" data-place="{esc(sc["place"])}" data-year="{esc(sc.get("year", ""))}">'
            f'<svg class="icon" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1C5.2 1 3 3.2 3 6c0 3.5 5 9 5 9s5-5.5 5-9c0-2.8-2.2-5-5-5zm0 6.8A1.8 1.8 0 1 1 8 4.2a1.8 1.8 0 0 1 0 3.6z"/></svg>'
            f'{esc(sc["place"])}</button>'
        )
    if "year" in sc:
        meta_bits.append(f'<span class="scene-year">{esc(sc["year"])} 年</span>')

    if stype == "poem":
        lead = sc.get("lead_in")
        if lead:
            parts.append(f'        <p class="lead-in">{esc(lead)}</p>')
        parts.append(f'        <h3 class="poem-title">{esc(sc["poem_title"])}</h3>')
        if sc.get("excerpt"):
            parts.append(f'        <p class="excerpt-note">{esc("〔" + sc["excerpt"] + "〕")}</p>')
        parts.append('        <div class="poem-text">')
        parts.append(render_poem_lines(sc["text"]))
        parts.append("        </div>")
        if sc.get("keyline"):
            parts.append(f'        <div class="keyline"><span>{esc(sc["keyline"])}</span></div>')
        if sc.get("artifact"):
            if sc.get("artifact_image"):
                asrc = esc(rel_from(page_path, f"assets/figures/{fid}/{sc['artifact_image']}"))
                is_ph = sc["artifact_image"].startswith("placeholder/")
                cap = f'{esc(sc["artifact"])} · 真迹（占位图）' if is_ph else f'{esc(sc["artifact"])} · 真迹'
                parts.append(
                    f'        <figure class="artifact"><img src="{asrc}" alt="{cap}" loading="lazy">'
                    f'<figcaption>{cap}</figcaption></figure>'
                )
            else:
                parts.append(f'        <p class="artifact-name">传世法帖：{esc(sc["artifact"])}</p>')
    else:
        parts.append(f'        <h2 class="scene-title">{esc(sc.get("title", ""))}</h2>')
        if stype == "event":
            parts.append('        <div class="event-card">')
            parts.append(render_text_paragraphs(sc["text"]))
            parts.append("        </div>")
        else:
            parts.append(render_text_paragraphs(sc["text"]))

    if meta_bits:
        parts.append(f'        <div class="scene-meta">{"".join(meta_bits)}</div>')

    if sc.get("source"):
        parts.append(
            f'        <div class="source-wrap"><button class="source-mark" type="button" '
            f'data-source="{esc(sc["source"])}" title="点击查看出处">出</button></div>'
        )
    notes = sc.get("notes") or []
    if notes:
        items = "\n".join(f"          <li>{esc(n)}</li>" for n in notes)
        parts.append(
            '        <details class="notes" open><summary>注</summary><ul>\n' + items + "\n        </ul></details>"
        )

    parts.append("      </div>")
    parts.append("    </section>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 页面渲染
# ---------------------------------------------------------------------------

def load_template(name: str) -> str:
    return (SITE_DIR / "templates" / name).read_text(encoding="utf-8")


def build_page(template: str, title: str, description: str, page_data: dict,
               content: str, out_path: Path, extra_js: str = ""):
    page = template
    rel_dir = posixpath.dirname(str(out_path.relative_to(DIST_DIR)))
    page = page.replace("__TITLE__", esc(title))
    page = page.replace("__DESCRIPTION__", esc(description))
    page = page.replace("__PAGE_DATA__", json_inline(page_data))
    page = page.replace("__CONTENT__", content)
    page = page.replace("__CSS_HREF__", posixpath.relpath("assets/css/main.css", rel_dir) + "?v=" + BUILD_VER)
    page = page.replace("__JS_COMMON__", posixpath.relpath("assets/js/common.js", rel_dir) + "?v=" + BUILD_VER)
    page = page.replace("__EXTRA_JS__", (posixpath.relpath(extra_js, rel_dir) + "?v=" + BUILD_VER) if extra_js else "")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")


def render_home(figures: list) -> str:
    """首页：星野 + 朝代分组网格（组序按 DYNASTY_ORDER，组内按生年；移除章节胶囊，人物页有全量章节）"""
    # 装饰星位固定坐标（构图手工调过，避免随机漂移）
    deco = [(8, 18, 2), (14, 62, 3), (22, 30, 2), (30, 76, 2), (36, 12, 3), (46, 55, 2),
            (55, 24, 2), (63, 70, 3), (72, 40, 2), (80, 15, 2), (86, 66, 3), (92, 35, 2)]

    # 排序：朝代 → 生年（仅在首页渲染层排序，不改 page-data 原序）
    figs = sorted(
        figures,
        key=lambda f: (DYNASTY_ORDER.index(f.get("dynasty") or DYNASTY_ORDER[-1]), f.get("born", 0)),
    )

    groups_html = []
    for dynasty in DYNASTY_ORDER:
        members = [f for f in figs if f.get("dynasty") == dynasty]
        if not members:
            continue
        span = f"{members[0].get('born', '?')} — {members[-1].get('died', '?')}"
        cards = []
        for f in members:
            if f["status"] == "published":
                cards.append(
                    f'''        <a class="figure-star published" href="figures/{esc(f["id"])}/index.html">
        <span class="star-dot" aria-hidden="true"></span>
        <span class="star-name">{esc(f["name"])}</span>
        <span class="star-years">{esc(f["born"])}—{esc(f["died"])}</span>
        <span class="star-oneliner">{esc(f["one_liner"])}</span>
      </a>'''
                )
            else:
                cards.append(
                    f'''        <div class="figure-star planned" aria-disabled="true">
        <span class="star-dot" aria-hidden="true"></span>
        <span class="star-name">{esc(f["name"])}</span>
        <span class="star-years">{esc(f["born"])}—{esc(f["died"])}</span>
        <span class="star-oneliner">{esc(f["one_liner"])}</span>
        <span class="star-planned">待生成</span>
      </div>'''
                )
        groups_html.append(
            f'      <div class="dynasty-label"><span class="d-name">{esc(dynasty)}</span>'
            f'<span class="d-line"></span><span class="d-sub">{esc(span)}</span></div>\n'
            f'      <div class="figures-grid">\n' + "\n".join(cards) + "\n      </div>"
        )

    return (
        '    <section class="home-hero">\n'
        '      <h1 class="site-title">诗词行旅</h1>\n'
        '      <p class="site-subtitle">先走入他的处境，再遇见他的诗</p>\n'
        '      <p class="site-hint">选择一颗星，随他走过一生</p>\n'
        "    </section>\n"
        '    <section class="star-field" aria-label="人物星空">\n'
        + "\n".join(f'      <span class="deco-star" style="left:{x}%;top:{y}%;width:{r * 2}px;height:{r * 2}px"></span>'
                    for x, y, r in deco) + "\n"
        + "\n".join(groups_html) + "\n"
        "    </section>\n"
    )


def render_figure_page(meta: dict, chapters: list) -> str:
    """人物页：简介 + SVG 足迹卷轴挂载点 + 章节列表（地图由 map.js 依据内联数据绘制）"""
    route_meta = []
    for node in meta.get("route") or []:
        coord = meta["places"][node["place"]]
        route_meta.append({
            "place": node["place"],
            "year": node["year"],
            "label": node.get("label", ""),
            "lng": coord["lng"],
            "lat": coord["lat"],
        })
    chapter_cards = []
    for ch in chapters:
        chapter_cards.append(
            f'''      <a class="chapter-card" href="chapters/{esc(ch["id"])}.html">
        <span class="chapter-era">{esc(ch["era"])}</span>
        <h3 class="chapter-title">{esc(ch["title"])}</h3>
        <p class="chapter-subtitle">{esc(ch["subtitle"])}</p>
        <span class="chapter-enter" aria-label="进入本章">
          <svg class="icon" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2l6 6-6 6" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>
        </span>
      </a>'''
        )
    return (
        f'    <section class="figure-head">\n'
        f'      <p class="figure-kicker">人物卷</p>\n'
        f'      <h1 class="figure-name">{esc(meta["name"])}</h1>\n'
        f'      <p class="figure-names">字 {esc(meta.get("courtesy_name", "—"))} · 号 {esc(meta.get("art_name", "—"))}</p>\n'
        f'      <p class="figure-years">{esc(meta["born"])}—{esc(meta["died"])}</p>\n'
        f'      <p class="figure-oneliner">{esc(meta["one_liner"])}</p>\n'
        f"    </section>\n"
        f'    <section class="route-section" aria-label="一生足迹">\n'
        f'      <h2 class="section-title">一生足迹</h2>\n'
        f'      <p class="section-hint">卷轴自左向右为时间推进；悬停星点查看节点。</p>\n'
        f'      <div class="route-scroll" id="route-map" role="img" aria-label="{esc(meta["name"])}一生足迹图"></div>\n'
        f"    </section>\n"
        f'    <section class="chapters-section" aria-label="章节列表">\n'
        f'      <h2 class="section-title">章节</h2>\n'
        + "\n".join(chapter_cards) + "\n"
        "    </section>\n"
    )


def render_chapter_page(meta: dict, chapter: dict, next_chapter: dict | None = None) -> str:
    """章节页：场景流（build 期渲染静态 HTML）"""
    page_path = f"figures/{meta['id']}/chapters/{chapter['id']}.html"
    sections = []
    for sc in chapter["scenes"]:
        if sc.get("image"):
            ensure_placeholder(sc["image"], sc.get("title") or sc.get("poem_title", ""))
        if sc.get("artifact_image"):
            ensure_placeholder(sc["artifact_image"], sc.get("artifact", "真迹"))
        sections.append(render_scene(sc, page_path, meta["id"]))
    body = "\n".join(sections)
    head = (
        f'    <header class="pager-page chapter-head">\n'
        f'      <p class="chapter-kicker">{esc(meta["name"])} · {esc(chapter["era"])}</p>\n'
        f'      <h1 class="chapter-bigtitle">{esc(chapter["title"])}</h1>\n'
        f'      <p class="chapter-bigsubtitle">{esc(chapter["subtitle"])}</p>\n'
        f"    </header>\n"
    )
    next_html = ""
    if next_chapter:
        next_label = esc(next_chapter["title"])
        if next_chapter.get("subtitle"):
            next_label += f" · {esc(next_chapter['subtitle'])}"
        next_html = f'      <a class="next-link" href="{esc(next_chapter["id"])}.html">进入下一章　{next_label} →</a>\n'
    back_line = f'      <a class="back-link" href="../index.html">返回 {esc(meta["name"])} · 一生足迹</a>\n'
    tail = (
        '    <footer class="pager-page chapter-end">\n'
        '      <p class="end-line">卷终</p>\n'
        + next_html + back_line +
        '    </footer>\n'
    )
    return head + body + tail


# ---------------------------------------------------------------------------
# 校对清单与报告
# ---------------------------------------------------------------------------

def build_proof_list(proof_items: list) -> str:
    """校对清单：文本与出处并列，按 proofed 分组

    proof_items 元素：(figure_name, chapter_title, scene_dict)
    """
    lines = [
        "# 校对清单",
        "",
        "用途：交由其他模型交叉校对。核对范围以 excerpt 为准；诗词原文请逐字核对底本。",
        "",
    ]
    pending, done = [], []
    for figure_name, chapter_title, sc in proof_items:
        (pending if not sc.get("proofed", False) else done).append(
            {"figure": figure_name, "chapter": chapter_title, "sc": sc}
        )
    lines.append(f"待校对 {len(pending)} 条；已校对 {len(done)} 条。")
    lines.append("")

    def emit(bucket, label):
        lines.append(f"## {label}（{len(bucket)} 条）")
        lines.append("")
        for it in bucket:
            sc = it["sc"]
            lines.append(f"### {sc.get('title') or sc.get('poem_title')}（{it['figure']}·{it['chapter']}）")
            lines.append("")
            lines.append(f"- 类型：{sc['type']}　地点：{sc.get('place', '—')}　年份：{sc.get('year', '—')}")
            if sc.get("excerpt"):
                lines.append(f"- 核对范围：{sc['excerpt']}")
            lines.append("- 出处：")
            lines.append(f"  > {sc.get('source', '')}")
            lines.append("- 文本：")
            for ln in [l.strip() for l in sc["text"].strip().splitlines() if l.strip()]:
                lines.append(f"  > {ln}")
            lines.append("")

    emit(pending, "待校对")
    emit(done, "已校对")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    global BUILD_VER
    BUILD_VER = "v" + str(int(__import__("time").time()))  # 静态资源防缓存版本号
    BUILD_VER = "v" + str(int(__import__("time").time()))  # 静态资源防缓存版本号
    proof_items = []   # 校对清单数据：(人物名, 章节名, 场景)
    if not FIGURES_DIR.exists():
        print(f"错误：找不到人物包目录 {FIGURES_DIR}")
        return 1

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # 站点静态资源
    for sub in ("css", "js"):
        src = SITE_DIR / sub
        if src.exists():
            shutil.copytree(src, ASSETS_DIR / sub, dirs_exist_ok=True)

    template_index = load_template("index.html")
    template_figure = load_template("figure.html")
    template_chapter = load_template("chapter.html")

    figures = []
    for pkg_dir in sorted(p for p in FIGURES_DIR.iterdir() if p.is_dir()):
        meta_path = pkg_dir / "metadata.yaml"
        if not meta_path.exists():
            warn(f"跳过 {pkg_dir.name}：无 metadata.yaml")
            continue
        meta = load_yaml(meta_path)
        places = validate_metadata(meta, pkg_dir)
        status = meta.get("status", "published")

        entry = {
            "id": meta["id"], "name": meta["name"],
            "courtesy_name": meta.get("courtesy_name", ""),
            "art_name": meta.get("art_name", ""),
            "born": meta["born"], "died": meta["died"],
            "one_liner": meta["one_liner"], "status": status,
            "dynasty": meta.get("dynasty", ""),
            "chapters": [],
        }

        if status == "published":
            chapters_dir = pkg_dir / meta.get("chapters_ref", "chapters")
            chapter_files = sorted(
                chapters_dir.glob("*.yaml"),
                key=lambda f: load_yaml(f).get("era", ""),  # 按时代排序，保证章节时间顺序
            )
            if not chapter_files:
                err(f"{pkg_dir}: published 人物没有任何章节 YAML")
            for ch_path in chapter_files:
                chapter = load_yaml(ch_path)
                seen_ids = set()
                for idx, sc in enumerate(chapter.get("scenes") or [], 1):
                    validate_scene(sc, idx, chapter, places, pkg_dir)
                    if sc.get("id") in seen_ids:
                        err(f"{pkg_dir}/{chapter['id']}: 场景 id 重复：{sc.get('id')}")
                    seen_ids.add(sc.get("id"))
                entry["chapters"].append({
                    "id": chapter["id"], "title": chapter["title"],
                    "subtitle": chapter.get("subtitle", ""),
                    "era": chapter.get("era", ""),
                    "scene_count": len(chapter.get("scenes") or []),
                })
                for sc in chapter.get("scenes") or []:
                    proof_items.append((meta["name"], chapter["title"], sc))
        figures.append(entry)

    if errors:
        print("构建失败，共 %d 个错误：" % len(errors))
        for e in errors:
            print("  [错误]", e)
        for w in warnings:
            print("  [警告]", w)
        return 1

    # ---- 数据 JSON ----
    data_dir = DIST_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "figures.json").write_text(
        json.dumps(figures, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- 首页 ----
    build_page(
        template_index, "诗词行旅 · 先走入他的处境，再遇见他的诗",
        "以一生为卷轴的诗词沉浸叙事",
        {"page": "home", "figures": figures},
        render_home(figures), DIST_DIR / "index.html",
    )

    # ---- 人物页与章节页（仅 published）----
    proof_scenes = 0
    poem_count = 0
    placeholder_files = []
    for pkg_dir in sorted(p for p in FIGURES_DIR.iterdir() if p.is_dir()):
        meta_path = pkg_dir / "metadata.yaml"
        if not meta_path.exists():
            continue
        meta = load_yaml(meta_path)
        if meta.get("status", "published") != "published":
            continue
        fid = meta["id"]
        chapters = []
        chapters_dir = pkg_dir / meta.get("chapters_ref", "chapters")
        for ch_path in sorted(chapters_dir.glob("*.yaml"), key=lambda f: load_yaml(f).get("era", "")):
            chapter = load_yaml(ch_path)
            chapters.append(chapter)

        fdir = DIST_DIR / "figures" / fid
        (fdir / "chapters").mkdir(parents=True, exist_ok=True)

        # 人物包自有资源（真实插画等）拷入 dist/assets/figures/<fid>/
        pkg_assets = pkg_dir / "assets"
        if pkg_assets.exists():
            shutil.copytree(pkg_assets, ASSETS_DIR / "figures" / fid, dirs_exist_ok=True)

        # 人物页数据：metadata + 章节摘要（地图 SVG 所需的路线也一并内联）
        route_nodes = []
        for node in meta.get("route") or []:
            coord = meta["places"][node["place"]]
            route_nodes.append({
                "place": node["place"], "year": node["year"],
                "label": node.get("label", ""),
                "lng": coord["lng"], "lat": coord["lat"],
            })
        page_data = {
            "page": "figure", "figure": {
                "id": fid, "name": meta["name"], "route": route_nodes,
                "chapters": [{"id": c["id"], "title": c["title"]} for c in chapters],
            },
        }
        build_page(
            template_figure,
            f"{meta['name']} · 诗词行旅",
            meta["one_liner"], page_data,
            render_figure_page(meta, chapters), fdir / "index.html",
            extra_js="assets/js/map.js",
        )

        for ci, chapter in enumerate(chapters):
            chapter_data = {"page": "chapter", "figureName": meta["name"], "chapter": chapter}
            build_page(
                template_chapter,
                f"{chapter['title']} · {meta['name']} · 诗词行旅",
                chapter.get("subtitle", ""), chapter_data,
                render_chapter_page(meta, chapter, chapters[ci + 1] if ci + 1 < len(chapters) else None),
                fdir / "chapters" / f"{chapter['id']}.html",
            )
            (data_dir / fid).mkdir(parents=True, exist_ok=True)
            (data_dir / fid / f"{chapter['id']}.json").write_text(
                json.dumps(chapter, ensure_ascii=False, indent=2), encoding="utf-8")
            for sc in chapter["scenes"]:
                proof_scenes += 1
                if sc["type"] == "poem":
                    poem_count += 1
                # 占位清单只登记 placeholder/ 前缀的图；真实资产不登记
                if sc.get("image") and sc["image"].startswith("placeholder/"):
                    placeholder_files.append(sc["image"])
                if sc.get("artifact_image") and sc["artifact_image"].startswith("placeholder/"):
                    placeholder_files.append(sc["artifact_image"])

    # ---- 占位清单 ----
    if placeholder_files:
        ph_content = (
            "# 占位图清单\n\n以下图片为占位 SVG，后期按 3.4 节风格模板批量生成后，\n"
            "放入 figures/<人物>/assets/ 对应路径并在 YAML 中改为非 placeholder/ 前缀路径。\n\n"
            + "".join(f"- {p}\n" for p in placeholder_files)
        )
    else:
        ph_content = "# 占位图清单\n\n当前无占位图，全部为真实资产。\n"
    (DIST_DIR / "placeholder-list.md").write_text(ph_content, encoding="utf-8")

    # ---- 校对清单 ----
    (DIST_DIR / "proof-list.md").write_text(build_proof_list(proof_items), encoding="utf-8")

    print("构建完成")
    print(f"  人物包：{len(figures)}（published {sum(1 for f in figures if f['status'] == 'published')}）")
    print(f"  诗文节拍：{poem_count} 篇；场景总数：{proof_scenes}")
    print(f"  产物目录：{DIST_DIR}")
    if warnings:
        print(f"警告 {len(warnings)} 条：")
        for w in warnings:
            print("  [警告]", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
