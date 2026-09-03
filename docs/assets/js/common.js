/* 诗词行旅 · 公共交互
   首页/人物页：浮签（地名/出处）
   章节页：左右翻页（箭头按钮 + 方向键 + 触摸滑动 + hash 定位） */
(function () {
  "use strict";

  var pageKind = document.body.getAttribute("data-page");

  // 有 JS 时才启用翻页显隐与淡入（无 JS 环境纵向全文可读）
  document.documentElement.classList.add("js");

  // ---- 浮签（地名 / 出处共用） ----
  var pop = document.createElement("div");
  pop.className = "popover";
  document.body.appendChild(pop);

  function showPop(anchor, title, body) {
    pop.innerHTML = "";
    if (title) {
      var t = document.createElement("div");
      t.className = "pop-title";
      t.textContent = title;
      pop.appendChild(t);
    }
    var b = document.createElement("div");
    b.textContent = body;
    pop.appendChild(b);
    pop.classList.add("show");
    var rect = anchor.getBoundingClientRect();
    var top = rect.bottom + window.scrollY + 8;
    var left = Math.min(
      Math.max(8, rect.left + window.scrollX),
      window.scrollX + document.documentElement.clientWidth - pop.offsetWidth - 8
    );
    pop.style.top = top + "px";
    pop.style.left = left + "px";
  }

  function hidePop() { pop.classList.remove("show"); }

  document.querySelectorAll(".place-mark").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var open = btn.getAttribute("data-open") === "1";
      if (!open) {
        showPop(btn, btn.getAttribute("data-place") + " · " + btn.getAttribute("data-year") + " 年",
          "本章事件发生地。全卷足迹见人物页「一生足迹」。");
        btn.setAttribute("data-open", "1");
      } else {
        hidePop();
        btn.setAttribute("data-open", "0");
      }
    });
  });

  document.querySelectorAll(".source-mark").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      showPop(btn, "出处", btn.getAttribute("data-source"));
    });
  });
  document.addEventListener("click", hidePop);

  // ---- 阅读进度线（首页/人物页按滚动；章节页按页码在翻页器里驱动） ----
  var bar = document.getElementById("progress-bar");
  if (bar && pageKind !== "chapter") {
    window.addEventListener("scroll", function () {
      var h = document.documentElement;
      var ratio = h.scrollTop / Math.max(1, h.scrollHeight - h.clientHeight);
      bar.style.width = (ratio * 100).toFixed(2) + "%";
    }, { passive: true });
  }

  // ---- 章节页翻页器 ----
  if (pageKind === "chapter") {
    var flow = document.querySelector(".chapter-flow");
    if (!flow) return;
    var pages = Array.prototype.slice.call(flow.querySelectorAll(":scope > .pager-page"));
    if (!pages.length) return;

    var current = 0;

    // 控件注入：左右箭头 + 页码
    var btnPrev = document.createElement("button");
    btnPrev.className = "pager-btn prev";
    btnPrev.type = "button";
    btnPrev.setAttribute("aria-label", "上一页");
    btnPrev.innerHTML = '<svg class="icon" viewBox="0 0 16 16" aria-hidden="true"><path d="M10 2L4 8l6 6" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>';

    var btnNext = document.createElement("button");
    btnNext.className = "pager-btn next";
    btnNext.type = "button";
    btnNext.setAttribute("aria-label", "下一页");
    btnNext.innerHTML = '<svg class="icon" viewBox="0 0 16 16" aria-hidden="true"><path d="M6 2l6 6-6 6" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>';

    var counter = document.createElement("div");
    counter.className = "pager-count";

    document.body.appendChild(btnPrev);
    document.body.appendChild(btnNext);
    document.body.appendChild(counter);

    function pad2(n) { return (n < 10 ? "0" : "") + n; }

    function updateChrome() {
      counter.textContent = pad2(current + 1) + " / " + pad2(pages.length);
      btnPrev.disabled = current === 0;
      btnNext.disabled = current === pages.length - 1;
      if (bar) bar.style.width = (current / (pages.length - 1) * 100).toFixed(2) + "%";
    }

    var ANIM_FALLBACK_MS = 600;  // 动画时长 550ms，略长于此作为后台标签页兼底
    function ensureVisible(el) {
      setTimeout(function () { el.classList.add("anim-done"); }, ANIM_FALLBACK_MS);
    }

    function goTo(i, back) {
      if (i < 0 || i >= pages.length || i === current) return;
      pages[current].classList.remove("active", "leaving-back", "anim-done");
      current = i;
      var el = pages[current];
      if (back) el.classList.add("leaving-back");
      el.classList.add("active");
      ensureVisible(el);
      el.scrollTop = 0;             // 翻页后回到页顶
      updateChrome();
      hidePop();
      var id = el.id || ("p" + current);
      try { history.replaceState(null, "", "#" + id); } catch (e) { /* file:// 下静默 */ }
    }

    // 初始定位：优先 hash 对应页，否则第一页
    (function init() {
      var hash = decodeURIComponent(location.hash.slice(1));
      var start = 0;
      if (hash) {
        for (var k = 0; k < pages.length; k++) {
          if (pages[k].id === hash) { start = k; break; }
        }
      }
      pages[start].classList.add("active");
      current = start;
      updateChrome();
      ensureVisible(pages[start]);
    })();

    btnPrev.addEventListener("click", function () { goTo(current - 1, true); });
    btnNext.addEventListener("click", function () { goTo(current + 1, false); });

    // 方向键翻页；PageUp/PageDown 同义
    document.addEventListener("keydown", function (e) {
      if (e.key === "ArrowRight" || e.key === "PageDown") {
        e.preventDefault();
        goTo(current + 1, false);
      } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
        e.preventDefault();
        goTo(current - 1, true);
      }
    });

    // 触摸滑动：横向位移大于纵向时翻页
    var touchX = null, touchY = null;
    document.addEventListener("touchstart", function (e) {
      touchX = e.touches[0].clientX;
      touchY = e.touches[0].clientY;
    }, { passive: true });
    document.addEventListener("touchend", function (e) {
      if (touchX === null) return;
      var dx = e.changedTouches[0].clientX - touchX;
      var dy = e.changedTouches[0].clientY - touchY;
      if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) {
        if (dx < 0) goTo(current + 1, false);
        else goTo(current - 1, true);
      }
      touchX = touchY = null;
    }, { passive: true });
  }
})();
