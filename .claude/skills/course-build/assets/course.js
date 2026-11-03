// Shared runtime for course-build chapters: top bar, in-page TOC, prev/next pager, small helpers.
// Course-specific data lives in course-config.js, which must be
// loaded (with `defer`) BEFORE this file and set window.COURSE = { title, hub, chapters: [[id, title, href], ...] }.
// Each chapter page sets <body data-ch="Cxx">. Hrefs in COURSE are relative to chapters/.
(function () {
  const COURSE = window.COURSE || { title: "Course", hub: "../index.html", chapters: [] };
  // Planned chapters (4th element "todo") are listed on the hub but excluded from navigation.
  const CHAPTERS = COURSE.chapters.filter((c) => c[3] !== "todo");
  window.TC = window.TC || {};
  TC.COURSE = COURSE;
  TC.CHAPTERS = CHAPTERS;

  // Canvas helper: size to CSS width x given height with devicePixelRatio; returns 2D context.
  TC.canvas = function (cv, h) {
    const dpr = window.devicePixelRatio || 1;
    const w = cv.clientWidth || cv.parentElement.clientWidth || 600;
    cv.style.height = h + "px";
    cv.width = Math.round(w * dpr);
    cv.height = Math.round(h * dpr);
    const g = cv.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { g, w, h };
  };
  TC.css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  // Bind a range input to an <output> and a callback; fmt formats the displayed value.
  TC.range = function (id, fmt, cb) {
    const el = document.getElementById(id);
    const out = document.querySelector('output[for="' + id + '"]');
    const run = () => { if (out) out.textContent = fmt ? fmt(+el.value) : el.value; cb && cb(+el.value); };
    el.addEventListener("input", run);
    run();
    return el;
  };
  // Segmented buttons inside container: one pressed at a time; cb(value).
  TC.seg = function (container, cb) {
    const root = typeof container === "string" ? document.getElementById(container) : container;
    const btns = [...root.querySelectorAll("button")];
    btns.forEach((b) => b.addEventListener("click", () => {
      btns.forEach((x) => x.setAttribute("aria-pressed", x === b ? "true" : "false"));
      cb(b.dataset.v);
    }));
    const init = btns.find((b) => b.getAttribute("aria-pressed") === "true") || btns[0];
    if (init) { init.setAttribute("aria-pressed", "true"); cb(init.dataset.v); }
  };
  // Seeded PRNG (mulberry32) so simulations are reproducible across reloads and in headless checks.
  TC.rng = function (seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };
  // Standard normal draw from a uniform generator (Box-Muller).
  TC.randn = function (u) {
    let x = 0, y = 0;
    while (x === 0) x = u();
    while (y === 0) y = u();
    return Math.sqrt(-2 * Math.log(x)) * Math.cos(2 * Math.PI * y);
  };
  TC.reducedMotion = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Notation: operators are upright and come from these macros only (chapter-spec §2.5).
  // Chapters must not call renderMathInElement themselves; course.js renders once with these macros.
  TC.MATH_MACROS = Object.assign({
    "\\E": "\\operatorname{E}", "\\Var": "\\operatorname{Var}", "\\Cov": "\\operatorname{Cov}",
    "\\Corr": "\\operatorname{Corr}", "\\SE": "\\operatorname{SE}", "\\MSE": "\\operatorname{MSE}",
    "\\Bias": "\\operatorname{Bias}", "\\AIC": "\\operatorname{AIC}", "\\BIC": "\\operatorname{BIC}",
    "\\logit": "\\operatorname{logit}", "\\tr": "\\operatorname{tr}", "\\diag": "\\operatorname{diag}",
    "\\argmax": "\\operatorname*{arg\\,max}", "\\argmin": "\\operatorname*{arg\\,min}",
    "\\iid": "\\overset{\\text{i.i.d.}}{\\sim}", "\\Normal": "\\mathrm{N}",
    "\\dd": "\\mathrm{d}", "\\T": "^{\\top}", "\\R": "\\mathbb{R}",
  }, COURSE.mathMacros || {});
  TC.renderMath = function (root) {
    if (!window.renderMathInElement) return false;
    window.renderMathInElement(root || document.body, {
      delimiters: [{ left: "\\[", right: "\\]", display: true }, { left: "\\(", right: "\\)", display: false }],
      macros: TC.MATH_MACROS, throwOnError: false, ignoredClasses: ["nomath"],
    });
    return true;
  };

  document.addEventListener("DOMContentLoaded", () => {
    TC.renderMath();
    const id = document.body.dataset.ch;
    const idx = CHAPTERS.findIndex((c) => c[0] === id);
    const wrap = document.querySelector(".wrap");
    if (!wrap) return;

    // Top bar with chapter jump.
    const bar = document.createElement("div");
    bar.className = "topbar";
    const here = idx < 0 ? `<option value="" selected disabled>${id || ""} ${(document.querySelector("h1") || {}).textContent || ""}</option>` : "";
    const opts = here + CHAPTERS.map((c) => `<option value="${c[2]}"${c[0] === id ? " selected" : ""}>${c[0]} ${c[1]}</option>`).join("");
    bar.innerHTML = `<a href="${COURSE.hub}">← ${COURSE.title}</a><span class="sp"></span><select aria-label="章へ移動">${opts}</select>`;
    bar.querySelector("select").addEventListener("change", (e) => { if (e.target.value) location.href = e.target.value; });
    wrap.prepend(bar);

    // In-page TOC from h2[id].
    const toc = document.querySelector("nav.intoc");
    if (toc) {
      const items = [...document.querySelectorAll("main h2[id]")]
        .map((h) => `<li><a href="#${h.id}">${h.textContent}</a></li>`).join("");
      toc.innerHTML = `<b class="small muted">この章の内容</b><ol>${items}</ol>`;
    }

    // Prev / next pager.
    const pager = document.createElement("nav");
    pager.className = "pager";
    if (idx < 0) {
      const first = CHAPTERS[0];
      pager.innerHTML = `<a href="${COURSE.hub}"><span>← 入口へ戻る</span>${COURSE.title}</a>` +
        (first ? `<a href="${first[2]}" style="text-align:right"><span>章を読む →</span>${first[0]} ${first[1]}</a>` : "<i></i>");
    } else {
      const prev = CHAPTERS[idx - 1], next = CHAPTERS[idx + 1];
      pager.innerHTML =
        (prev ? `<a href="${prev[2]}"><span>← 前の章</span>${prev[0]} ${prev[1]}</a>` : `<a href="${COURSE.hub}"><span>← 入口</span>${COURSE.title}</a>`) +
        (next ? `<a href="${next[2]}" style="text-align:right"><span>次の章 →</span>${next[0]} ${next[1]}</a>` : "<i></i>");
    }
    wrap.appendChild(pager);
  });
})();
