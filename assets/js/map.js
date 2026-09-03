/* 诗词行旅 · 人物页足迹卷轴
   兜底方案（设计文档 8 节三级方案之第三级）：零依赖自绘 SVG 水墨路线卷轴。
   动态经纬边界投影（卷轴铺满可视区，不留空域）；
   节点按地名聚合，半径随到访次数增大；相邻地点以交替弧线相连并带方向箭头，
   同向多次往返合并为一条边、线宽随次数加粗；近址节点自动横向分离避免重叠；
   悬停节点或边时高亮相关子图，其余置灰非聚焦。 */
(function () {
  "use strict";

  var mount = document.getElementById("route-map");
  var dataEl = document.getElementById("page-data");
  if (!mount || !dataEl) return;

  var data;
  try { data = JSON.parse(dataEl.textContent); } catch (e) { return; }
  var route = (data.figure && data.figure.route) || [];
  if (!route.length) return;

  // ---- 地名聚合：一个地名一个节点，count 驱动半径 ----
  var groups = [];                 // [{place,lng,lat,count,labels,yearMin,yearMin,firstIdx}]
  var byPlace = {};
  route.forEach(function (n, i) {
    var g = byPlace[n.place];
    if (!g) {
      g = byPlace[n.place] = {
        place: n.place, lng: n.lng, lat: n.lat,
        count: 0, labels: [], yearMin: n.year, yearMax: n.year, firstIdx: i
      };
      groups.push(g);
    }
    g.count++;
    if (n.label) g.labels.push(n.label);
    // 年份取数值范围（year 形如 "1037" 或 "1097-1100"）
    var ys = String(n.year).match(/\d{4}/g);
    if (ys) {
      g.yearMin = [g.yearMin, ys[0]].sort()[0];
      g.yearMax = [g.yearMax, ys[ys.length - 1]].sort()[1];
    }
  });

  // ---- 动态边界：以实际足迹范围为域，卷轴铺满，默认即有画面 ----
  var lngs = groups.map(function (g) { return g.lng; });
  var lats = groups.map(function (g) { return g.lat; });
  var lngMin = Math.min.apply(null, lngs), lngMax = Math.max.apply(null, lngs);
  var latMin = Math.min.apply(null, lats), latMax = Math.max.apply(null, lats);
  var lngPad = Math.max(1.2, (lngMax - lngMin) * 0.06);
  var latPad = Math.max(1.2, (latMax - latMin) * 0.10);
  lngMin -= lngPad; lngMax += lngPad; latMin -= latPad; latMax += latPad;

  var W = 1200;
  var H = Math.round(Math.min(520, Math.max(300, (latMax - latMin) * 42)));
  var PAD = 64;

  function projRaw(g) {
    var x = PAD + (g.lng - lngMin) / (lngMax - lngMin) * (W - PAD * 2);
    var y = H - PAD - (g.lat - latMin) / (latMax - latMin) * (H - PAD * 2);
    return { x: x, y: y };
  }

  // ---- 近址分离：组级两两检查，多轮迭代直至无重叠（卷轴为示意，允许脱离精确地理位置） ----
  var pts = groups.map(projRaw);
  var MIN_GAP = 64;
  for (var pass = 0; pass < 4; pass++) {
    var moved = false;
    for (var i = 1; i < pts.length; i++) {
      for (var j = 0; j < i; j++) {
        var a = pts[j], b = pts[i];
        var dx = b.x - a.x, dy = b.y - a.y;
        var dist = Math.sqrt(dx * dx + dy * dy);
        if (dist >= MIN_GAP) continue;
        if (dist < 1) {
          // 完全同址（坐标重合的不同地名）：沿右下 45 度阶梯排开
          dx = Math.SQRT1_2; dy = Math.SQRT1_2; dist = 1;
        }
        b.x += dx / dist * (MIN_GAP - dist) * 0.6;
        b.y += dy / dist * (MIN_GAP - dist) * 0.6;
        moved = true;
      }
    }
    if (!moved) break;
  }
  // 限回画布内
  for (var k = 0; k < pts.length; k++) {
    var p = pts[k];
    if (p.x > W - PAD / 2) p.x = W - PAD / 2;
    if (p.x < PAD / 2) p.x = PAD / 2;
    if (p.y < PAD * 0.6) p.y = PAD * 0.6;
    if (p.y > H - PAD * 0.6) p.y = H - PAD * 0.6;
  }

  var NS = "http://www.w3.org/2000/svg";
  var svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 " + W + " " + H);
  svg.setAttribute("width", W);
  svg.setAttribute("height", H);
  svg.setAttribute("font-family", "'Noto Sans SC','PingFang SC',sans-serif");
  svg.classList.add("route-svg");

  // 箭头定义：行进方向
  var defs = document.createElementNS(NS, "defs");
  var marker = document.createElementNS(NS, "marker");
  marker.setAttribute("id", "route-arrow");
  marker.setAttribute("viewBox", "0 0 10 10");
  marker.setAttribute("refX", "8");
  marker.setAttribute("refY", "5");
  marker.setAttribute("markerWidth", "7");
  marker.setAttribute("markerHeight", "7");
  marker.setAttribute("orient", "auto-start-reverse");
  var arrow = document.createElementNS(NS, "path");
  arrow.setAttribute("d", "M0,0 L10,5 L0,10 z");
  arrow.setAttribute("fill", "#2C3E50");
  arrow.setAttribute("fill-opacity", "0.7");
  marker.appendChild(arrow);
  defs.appendChild(marker);
  svg.appendChild(defs);

  // 底纹：淡墨水平线（卷轴纸纹意象，克制）
  for (var gy = 1; gy <= 3; gy++) {
    var gline = document.createElementNS(NS, "line");
    gline.setAttribute("x1", 0); gline.setAttribute("x2", W);
    gline.setAttribute("y1", H * gy / 4); gline.setAttribute("y2", H * gy / 4);
    gline.setAttribute("stroke", "#1A1A1A"); gline.setAttribute("stroke-opacity", "0.05");
    gline.setAttribute("stroke-width", "1");
    svg.appendChild(gline);
  }

  // ---- 边：按时间序扫相邻场景，同向多次往返合并为一条，线宽随次数加粗 ----
  var edgeMap = {};                // "甲→乙" -> {from,to,count,seq}
  var edgeList = [];
  for (var s = 1; s < route.length; s++) {
    var from = route[s - 1].place, to = route[s].place;
    if (from === to) continue;     // 连续同地，不出行
    var key = from + "→" + to;
    if (!edgeMap[key]) {
      edgeMap[key] = { from: from, to: to, count: 0, seq: edgeList.length };
      edgeList.push(edgeMap[key]);
    }
    edgeMap[key].count++;
  }

  var edgeEls = {};                // key -> 可见 path
  var hitEls = [];                 // 热区 path（透明宽描边，便于悬停）
  edgeList.forEach(function (e) {
    var gi = byPlace[e.from], gj = byPlace[e.to];
    var pa = pts[groups.indexOf(gi)], pb = pts[groups.indexOf(gj)];
    var mx = (pa.x + pb.x) / 2, my = (pa.y + pb.y) / 2;
    var ex = pb.x - pa.x, ey = pb.y - pa.y;
    var len = Math.sqrt(ex * ex + ey * ey);
    if (len < 1) return;
    // 法向单位向量；拱向交替；近距离小弧、远距离大弧但有上限
    var nx = -ey / len, ny = ex / len;
    var bow = Math.min(34, Math.max(12, len * 0.16)) * (e.seq % 2 === 0 ? 1 : -1);
    var cx = mx + nx * bow, cy = my + ny * bow;
    var d = "M" + pa.x.toFixed(1) + " " + pa.y.toFixed(1) +
            " Q" + cx.toFixed(1) + " " + cy.toFixed(1) +
            " " + pb.x.toFixed(1) + " " + pb.y.toFixed(1);

    var path = document.createElementNS(NS, "path");
    path.setAttribute("d", d);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "#2C3E50");
    path.setAttribute("stroke-opacity", "0.55");
    path.setAttribute("stroke-width", 2 + Math.min(e.count - 1, 3) * 0.9);
    path.setAttribute("stroke-linecap", "round");
    path.setAttribute("marker-end", "url(#route-arrow)");
    path.classList.add("edge");
    path.dataset.from = e.from;
    path.dataset.to = e.to;
    svg.appendChild(path);
    edgeEls[e.from + "→" + e.to] = path;

    // 热区：透明宽描边，提高悬停命中率
    var hit = document.createElementNS(NS, "path");
    hit.setAttribute("d", d);
    hit.setAttribute("fill", "none");
    hit.setAttribute("stroke", "rgba(0,0,0,0)");
    hit.setAttribute("stroke-width", "16");
    hit.style.pointerEvents = "stroke";
    hit.style.cursor = "pointer";
    hit.classList.add("edge-hit");
    hit.dataset.from = e.from;
    hit.dataset.to = e.to;
    svg.appendChild(hit);
    hitEls.push(hit);
  });

  // ---- 节点与标签：朱砂点，半径随到访次数；标签上下交替避让 ----
  var tooltip = document.createElement("div");
  tooltip.className = "popover";
  document.body.appendChild(tooltip);

  // 悬停高亮：聚焦相关子图，其余置灰（非隐藏）
  function setFocus(hiPlaces, hiEdges) {
    svg.classList.add("dim");
    Array.prototype.forEach.call(svg.querySelectorAll(".node,.edge"), function (el) {
      var on;
      if (el.classList.contains("node")) on = hiPlaces.indexOf(el.dataset.place) > -1;
      else on = hiEdges.indexOf(el.dataset.from + "→" + el.dataset.to) > -1;
      el.classList.toggle("hi", !!on);
    });
  }
  function clearFocus() {
    svg.classList.remove("dim");
    tooltip.classList.remove("show");   // 移开时同步隐藏浮签
    Array.prototype.forEach.call(svg.querySelectorAll(".hi"), function (el) {
      el.classList.remove("hi");
    });
  }

  groups.forEach(function (g, gi) {
    var p = pts[gi];
    var r = 6.5 + 2.2 * Math.sqrt(g.count - 1);   // 半径随次数增长（基准加大保证观感）
    var el = document.createElementNS(NS, "g");
    el.classList.add("node");
    el.dataset.place = g.place;
    el.style.cursor = "pointer";

    var halo = document.createElementNS(NS, "circle");
    halo.setAttribute("cx", p.x); halo.setAttribute("cy", p.y); halo.setAttribute("r", r + 6);
    halo.setAttribute("fill", "#C0392B"); halo.setAttribute("fill-opacity", "0.12");
    el.appendChild(halo);

    var dot = document.createElementNS(NS, "circle");
    dot.setAttribute("cx", p.x); dot.setAttribute("cy", p.y); dot.setAttribute("r", r);
    dot.setAttribute("fill", "#C0392B");
    el.appendChild(dot);

    // 多次到访：点内白点计数提示（克制，不加文字）
    if (g.count > 1) {
      var core = document.createElementNS(NS, "circle");
      core.setAttribute("cx", p.x); core.setAttribute("cy", p.y); core.setAttribute("r", Math.max(1.6, r * 0.28));
      core.setAttribute("fill", "#F5F1E8"); core.setAttribute("fill-opacity", "0.85");
      el.appendChild(core);
    }

    var label = document.createElementNS(NS, "text");
    label.setAttribute("x", p.x);
    label.setAttribute("y", p.y + (gi % 2 === 0 ? -(r + 12) : r + 20));
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("font-size", "13");
    label.setAttribute("fill", "#1A1A1A");
    label.setAttribute("fill-opacity", "0.8");
    label.textContent = g.place;
    el.appendChild(label);

    var year = document.createElementNS(NS, "text");
    year.setAttribute("x", p.x);
    year.setAttribute("y", p.y + (gi % 2 === 0 ? -(r + 28) : r + 36));
    year.setAttribute("text-anchor", "middle");
    year.setAttribute("font-size", "11");
    year.setAttribute("fill", "#55708A");
    year.textContent = g.yearMin === g.yearMax ? g.yearMin : g.yearMin + "–" + g.yearMax;
    el.appendChild(year);

    el.addEventListener("mouseenter", function () {
      // 节点：高亮自身 + 全部入边出边 + 对端节点
      var hiP = [g.place], hiE = [];
      edgeList.forEach(function (e) {
        if (e.from === g.place || e.to === g.place) {
          hiE.push(e.from + "→" + e.to);
          if (hiP.indexOf(e.from) < 0) hiP.push(e.from);
          if (hiP.indexOf(e.to) < 0) hiP.push(e.to);
        }
      });
      setFocus(hiP, hiE);
      showTooltip(g, p);
    });
    el.addEventListener("mouseleave", clearFocus);

    svg.appendChild(el);
  });

  // 边悬停：高亮该边 + 两端节点
  hitEls.forEach(function (hit) {
    hit.addEventListener("mouseenter", function () {
      var f = hit.dataset.from, t = hit.dataset.to;
      setFocus([f, t], [f + "→" + t]);
      var g = byPlace[f];
      showTooltip({
        place: f + " → " + t,
        yearMin: "", yearMax: "",
        count: edgeMap[f + "→" + t].count,
        labels: [edgeMap[f + "→" + t].count > 1 ? "此路线往返 " + edgeMap[f + "→" + t].count + " 次" : ""]
      }, null);
    });
    hit.addEventListener("mouseleave", clearFocus);
  });

  function showTooltip(g, p) {
    tooltip.innerHTML = "";
    var t = document.createElement("div");
    t.className = "pop-title";
    var span = g.yearMin ? (g.yearMin === g.yearMax ? g.yearMin : g.yearMin + "–" + g.yearMax) : "";
    t.textContent = g.place + (span ? " · " + span : "");
    tooltip.appendChild(t);
    if (g.count > 1) {
      var c = document.createElement("div");
      c.textContent = "到访 " + g.count + " 次";
      tooltip.appendChild(c);
    }
    g.labels.slice(0, 3).forEach(function (lb) {
      if (!lb) return;
      var b = document.createElement("div");
      b.textContent = lb;
      tooltip.appendChild(b);
    });
    tooltip.classList.add("show");
    if (p) {
      var rect = svg.getBoundingClientRect();
      var scrollX = window.scrollX, scrollY = window.scrollY;
      tooltip.style.left = Math.min(rect.left + scrollX + p.x / W * rect.width - 60, scrollX + document.documentElement.clientWidth - 200) + "px";
      tooltip.style.top = (rect.top + scrollY + p.y / H * rect.height + 16) + "px";
    }
  }

  mount.appendChild(svg);
})();
