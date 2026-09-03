/* 诗词行旅 · 人物页足迹卷轴
   兜底方案（设计文档 8 节三级方案之第三级）：零依赖自绘 SVG 水墨路线卷轴。
   动态经纬边界投影（卷轴铺满可视区，不留空域）；
   相邻节点以交替弧线相连并带方向箭头；近址节点自动横向分离避免重叠。 */
(function () {
  "use strict";

  var mount = document.getElementById("route-map");
  var dataEl = document.getElementById("page-data");
  if (!mount || !dataEl) return;

  var data;
  try { data = JSON.parse(dataEl.textContent); } catch (e) { return; }
  var route = (data.figure && data.figure.route) || [];
  if (!route.length) return;

  // ---- 动态边界：以实际足迹范围为域，卷轴铺满，默认即有画面 ----
  var lngs = route.map(function (n) { return n.lng; });
  var lats = route.map(function (n) { return n.lat; });
  var lngMin = Math.min.apply(null, lngs), lngMax = Math.max.apply(null, lngs);
  var latMin = Math.min.apply(null, lats), latMax = Math.max.apply(null, lats);
  var lngPad = Math.max(1.2, (lngMax - lngMin) * 0.06);
  var latPad = Math.max(1.2, (latMax - latMin) * 0.10);
  lngMin -= lngPad; lngMax += lngPad; latMin -= latPad; latMax += latPad;

  var W = 1200;
  var H = Math.round(Math.min(520, Math.max(300, (latMax - latMin) * 42)));
  var PAD = 64;

  function projRaw(n) {
    var x = PAD + (n.lng - lngMin) / (lngMax - lngMin) * (W - PAD * 2);
    var y = H - PAD - (n.lat - latMin) / (latMax - latMin) * (H - PAD * 2);
    return { x: x, y: y };
  }

  // ---- 近址分离：全节点两两检查，多轮迭代直至无重叠（卷轴为示意，允许脱离精确地理位置） ----
  var pts = route.map(projRaw);
  var MIN_GAP = 56;
  for (var pass = 0; pass < 4; pass++) {
    var moved = false;
    for (var i = 1; i < pts.length; i++) {
      for (var j = 0; j < i; j++) {
        var a = pts[j], b = pts[i];
        var dx = b.x - a.x, dy = b.y - a.y;
        var dist = Math.sqrt(dx * dx + dy * dy);
        if (dist >= MIN_GAP) continue;
        if (dist < 1) {
          // 完全同址（如多次还朝汴京）：沿右下 45 度阶梯排开
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

  // ---- 弧线：相邻节点二次贝塞尔，拱向交替，弧度随距离收敛 ----
  for (var s = 1; s < pts.length; s++) {
    var a = pts[s - 1], b = pts[s];
    var mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
    var ex = b.x - a.x, ey = b.y - a.y;
    var len = Math.sqrt(ex * ex + ey * ey);
    if (len < 1) continue;
    // 法向单位向量；拱向交替；近距离小弧、远距离大弧但有上限
    var nx = -ey / len, ny = ex / len;
    var bow = Math.min(34, Math.max(12, len * 0.16)) * (s % 2 === 0 ? 1 : -1);
    var cx = mx + nx * bow, cy = my + ny * bow;

    var path = document.createElementNS(NS, "path");
    path.setAttribute("d",
      "M" + a.x.toFixed(1) + " " + a.y.toFixed(1) +
      " Q" + cx.toFixed(1) + " " + cy.toFixed(1) +
      " " + b.x.toFixed(1) + " " + b.y.toFixed(1));
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "#2C3E50");
    path.setAttribute("stroke-opacity", "0.55");
    path.setAttribute("stroke-width", "2");
    path.setAttribute("stroke-linecap", "round");
    path.setAttribute("marker-end", "url(#route-arrow)");
    svg.appendChild(path);
  }

  // ---- 节点与标签：朱砂点；标签上下交替避让 ----
  var tooltip = document.createElement("div");
  tooltip.className = "popover";
  document.body.appendChild(tooltip);

  route.forEach(function (n, i) {
    var p = pts[i];
    var g = document.createElementNS(NS, "g");
    g.style.cursor = "pointer";

    var halo = document.createElementNS(NS, "circle");
    halo.setAttribute("cx", p.x); halo.setAttribute("cy", p.y); halo.setAttribute("r", 10);
    halo.setAttribute("fill", "#C0392B"); halo.setAttribute("fill-opacity", "0.12");
    g.appendChild(halo);

    var dot = document.createElementNS(NS, "circle");
    dot.setAttribute("cx", p.x); dot.setAttribute("cy", p.y); dot.setAttribute("r", 4.5);
    dot.setAttribute("fill", "#C0392B");
    g.appendChild(dot);

    var label = document.createElementNS(NS, "text");
    label.setAttribute("x", p.x);
    label.setAttribute("y", p.y + (i % 2 === 0 ? -16 : 24));
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("font-size", "13");
    label.setAttribute("fill", "#1A1A1A");
    label.setAttribute("fill-opacity", "0.8");
    label.textContent = n.place;
    g.appendChild(label);

    var year = document.createElementNS(NS, "text");
    year.setAttribute("x", p.x);
    year.setAttribute("y", p.y + (i % 2 === 0 ? -32 : 40));
    year.setAttribute("text-anchor", "middle");
    year.setAttribute("font-size", "11");
    year.setAttribute("fill", "#55708A");
    year.textContent = n.year;
    g.appendChild(year);

    g.addEventListener("mouseenter", function () {
      dot.setAttribute("r", "6.5");
      tooltip.innerHTML = "";
      var t = document.createElement("div");
      t.className = "pop-title";
      t.textContent = n.place + " · " + n.year;
      tooltip.appendChild(t);
      var b = document.createElement("div");
      b.textContent = n.label || "";
      tooltip.appendChild(b);
      tooltip.classList.add("show");
      var rect = svg.getBoundingClientRect();
      var scrollX = window.scrollX, scrollY = window.scrollY;
      tooltip.style.left = Math.min(rect.left + scrollX + p.x / W * rect.width - 60, scrollX + document.documentElement.clientWidth - 200) + "px";
      tooltip.style.top = (rect.top + scrollY + p.y / H * rect.height + 16) + "px";
    });
    g.addEventListener("mouseleave", function () {
      dot.setAttribute("r", "4.5");
      tooltip.classList.remove("show");
    });

    svg.appendChild(g);
  });

  mount.appendChild(svg);
})();
