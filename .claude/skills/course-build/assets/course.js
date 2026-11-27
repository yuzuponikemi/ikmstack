// Shared runtime for course-build chapters: top bar, in-page TOC, prev/next pager, small helpers,
// and reader controls (page / figure text size, figure width on phones, quiz progress, hub progress).
// Course-specific data lives in course-config.js, which must be
// loaded (with `defer`) BEFORE this file and set window.COURSE = { title, hub, chapters: [[id, title, href], ...] }.
// Optional COURSE fields: storagePrefix (localStorage key prefix), pageScale (default page text scale, 0.85),
// quizCounts / labCounts ({ C01: n }) for the hub before a chapter has been opened.
// Each chapter page sets <body data-ch="Cxx">; the hub sets data-ch="HUB". Hrefs in COURSE are relative to chapters/.
// Reader preferences and quiz marks are kept in localStorage only (per browser); every access is guarded.
(function () {
  const COURSE = window.COURSE || { title: "Course", hub: "../index.html", chapters: [] };
  // Planned chapters (4th element "todo") are listed on the hub but excluded from navigation.
  const CHAPTERS = COURSE.chapters.filter((c) => c[3] !== "todo");
  window.TC = window.TC || {};
  TC.COURSE = COURSE;
  TC.CHAPTERS = CHAPTERS;
  // Headless checks (browser_check.mjs) see the page as authored: no font boost, no figure toolbars.
  const HEADLESS = typeof navigator !== "undefined" && navigator.webdriver;

  function slug(s) { let h = 0; for (const ch of String(s)) h = (h * 31 + ch.codePointAt(0)) >>> 0; return h.toString(36); }
  const PREFIX = COURSE.storagePrefix || "tc_" + slug(COURSE.title) + "_";
  const store = {
    get(k) { try { return localStorage.getItem(PREFIX + k); } catch (_) { return null; } },
    set(k, v) { try { localStorage.setItem(PREFIX + k, v); } catch (_) {} },
    del(k) { try { localStorage.removeItem(PREFIX + k); } catch (_) {} },
  };
  TC.store = store;

  // Quiz progress per chapter: { [question number]: "done" | "rev" }. The question count is
  // remembered when a chapter is opened so the hub can show progress without quizCounts.
  TC.quizStore = {
    getChapter(chId) { try { return JSON.parse(store.get("q_" + chId) || "{}"); } catch (_) { return {}; } },
    setQuestion(chId, q, state) {
      const cur = TC.quizStore.getChapter(chId);
      if (!state) delete cur[q]; else cur[q] = state;
      store.set("q_" + chId, JSON.stringify(cur));
      return cur;
    },
    getSummary(chId) {
      const vals = Object.values(TC.quizStore.getChapter(chId));
      const total = (COURSE.quizCounts && COURSE.quizCounts[chId]) || parseInt(store.get("qn_" + chId), 10) || 0;
      return { done: vals.filter((v) => v === "done").length, rev: vals.filter((v) => v === "rev").length, total };
    },
  };

  // Text size: page text (rem-based, scales the root font size) and text inside figures / canvases.
  const DEFAULT_PAGE_SCALE = COURSE.pageScale || 0.85;
  const PAGE_SCALES = [0.75, 0.8, 0.85, 0.92, 1.0, 1.1, 1.2, 1.35];
  const FIG_SCALES = [0.75, 0.88, 1.0, 1.15, 1.3, 1.5, 1.75];
  if (!PAGE_SCALES.includes(DEFAULT_PAGE_SCALE)) { PAGE_SCALES.push(DEFAULT_PAGE_SCALE); PAGE_SCALES.sort((a, b) => a - b); }
  const pct = (v) => Math.round(v * 100) + "%";
  TC.fontCtrl = {
    getPageScale() { const v = parseFloat(store.get("page_fscale")); return PAGE_SCALES.includes(v) ? v : DEFAULT_PAGE_SCALE; },
    setPageScale(s) {
      const v = PAGE_SCALES.includes(s) ? s : DEFAULT_PAGE_SCALE;
      store.set("page_fscale", String(v));
      document.documentElement.style.fontSize = (16 * v).toFixed(2) + "px";
      document.querySelectorAll('[data-fctrl="page"] span').forEach((el) => { el.textContent = pct(v); });
      window.dispatchEvent(new Event("resize"));
    },
    getFigScale() { const v = parseFloat(store.get("fig_fscale")); return FIG_SCALES.includes(v) ? v : 1.0; },
    setFigScale(s) {
      const v = FIG_SCALES.includes(s) ? s : 1.0;
      store.set("fig_fscale", String(v));
      document.querySelectorAll('[data-fctrl="fig"] span').forEach((el) => { el.textContent = "図文字 " + pct(v); });
      if (TC._updateSvgTextScale) TC._updateSvgTextScale();
      window.dispatchEvent(new Event("resize"));
    },
    step(kind, dir) {
      const page = kind === "page", list = page ? PAGE_SCALES : FIG_SCALES;
      const cur = page ? TC.fontCtrl.getPageScale() : TC.fontCtrl.getFigScale();
      const next = list[Math.max(0, Math.min(list.length - 1, list.indexOf(cur) + dir))];
      if (page) TC.fontCtrl.setPageScale(next); else TC.fontCtrl.setFigScale(next);
    },
    createStepper(kind) {
      const page = kind === "page";
      const cur = page ? TC.fontCtrl.getPageScale() : TC.fontCtrl.getFigScale();
      const wrap = document.createElement("div");
      wrap.className = "font-stepper";
      wrap.setAttribute("data-fctrl", kind);
      wrap.innerHTML =
        `<button type="button" data-d="-1" title="${page ? "文字を小さく" : "図の中の文字を小さく"}">A−</button>` +
        `<span title="タップで既定(${pct(page ? DEFAULT_PAGE_SCALE : 1)})に戻す">${page ? "" : "図文字 "}${pct(cur)}</span>` +
        `<button type="button" data-d="1" title="${page ? "文字を大きく" : "図の中の文字を大きく"}">A＋</button>`;
      wrap.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => TC.fontCtrl.step(kind, parseInt(b.dataset.d, 10))));
      wrap.querySelector("span").addEventListener("click", () => {
        if (page) TC.fontCtrl.setPageScale(DEFAULT_PAGE_SCALE); else TC.fontCtrl.setFigScale(1.0);
      });
      return wrap;
    },
  };

  // Canvas helper: size to CSS width x given height with devicePixelRatio; returns 2D context.
  // Font sizes set on the context follow the figure text scale (and get a small boost on phones).
  TC.canvas = function (cv, h) {
    const dpr = window.devicePixelRatio || 1;
    const w = cv.clientWidth || (cv.parentElement && cv.parentElement.clientWidth) || 600;
    cv.style.height = h + "px";
    cv.width = Math.round(w * dpr);
    cv.height = Math.round(h * dpr);
    const g = cv.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (!HEADLESS && !g._tcFontWrapped) {
      const desc = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(g), "font");
      if (desc && desc.set && desc.get) {
        Object.defineProperty(g, "font", {
          configurable: true,
          get() { return desc.get.call(this); },
          set(val) {
            const mob = window.innerWidth <= 640, f = TC.fontCtrl.getFigScale();
            desc.set.call(this, String(val).replace(/(\b\d+(?:\.\d+)?)px\b/, (_, num) => {
              let px = parseFloat(num);
              if (mob) px = px <= 10 ? 12 : px <= 11 ? 12.5 : px <= 12 ? 13.2 : px;
              return Math.round(px * f * 10) / 10 + "px";
            }));
          },
        });
        g._tcFontWrapped = true;
      }
    }
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

  // Quiz (<ol class="quiz">): "理解した / 要復習" marks per question and a filter bar.
  function initQuizTracker(chId) {
    const ol = document.querySelector("ol.quiz");
    if (!ol) return;
    const items = [...ol.querySelectorAll(":scope > li")];
    if (!items.length) return;
    store.set("qn_" + chId, String(items.length));
    const bar = document.createElement("div");
    bar.className = "quiz-toolbar";
    bar.innerHTML = `<div class="quiz-stats"></div><div class="seg">` +
      `<button type="button" data-v="all" aria-pressed="true">すべて (${items.length})</button>` +
      `<button type="button" data-v="rev" aria-pressed="false">★ 要復習のみ</button>` +
      `<button type="button" data-v="todo" aria-pressed="false">未完了のみ</button></div>`;
    ol.parentNode.insertBefore(bar, ol);
    let filter = "all";
    function refresh() {
      const map = TC.quizStore.getChapter(chId);
      let done = 0, rev = 0, shown = 0;
      items.forEach((li, i) => {
        const st = map[String(i + 1)] || "";
        if (st === "done") done++;
        if (st === "rev") rev++;
        if (st) li.setAttribute("data-qstate", st); else li.removeAttribute("data-qstate");
        li.querySelectorAll(".q-btn").forEach((b) => { b.className = "q-btn" + (st === b.dataset.act ? " on-" + st : ""); });
        const show = filter === "all" || (filter === "rev" && st === "rev") || (filter === "todo" && st !== "done");
        li.hidden = !show;
        if (show) shown++;
      });
      bar.querySelector(".quiz-stats").innerHTML = `学習記録: <b class="ok">✓ 理解した ${done}</b> · <b class="rv">★ 要復習 ${rev}</b> / 全 ${items.length} 問` +
        (filter !== "all" ? `（表示中 ${shown} 問）` : "");
    }
    items.forEach((li, i) => {
      const q = String(i + 1);
      const act = document.createElement("div");
      act.className = "quiz-actions";
      act.innerHTML = `<button type="button" class="q-btn" data-act="done">✓ 理解した</button><button type="button" class="q-btn" data-act="rev">★ 要復習</button>`;
      act.querySelectorAll(".q-btn").forEach((b) => b.addEventListener("click", () => {
        const cur = TC.quizStore.getChapter(chId)[q];
        TC.quizStore.setQuestion(chId, q, cur === b.dataset.act ? null : b.dataset.act);
        refresh();
      }));
      li.appendChild(act);
    });
    TC.seg(bar.querySelector(".seg"), (v) => { filter = v; refresh(); });
  }

  // Wide SVG figures (viewBox width >= 500): width mode on phones and a figure-text stepper;
  // LAB headers get the same stepper (it scales canvas text through TC.canvas).
  function enhanceFigures() {
    if (HEADLESS) return;
    const wide = [];
    document.querySelectorAll("main figure").forEach((fig) => {
      const svg = fig.querySelector("svg[viewBox]");
      if (!svg) return;
      const vb = (svg.getAttribute("viewBox") || "").trim().split(/[\s,]+/).map(Number);
      if (vb.length === 4 && vb[2] >= 500) { svg.setAttribute("data-wide-svg", "1"); wide.push({ fig, svg }); }
    });
    function applyMode(mode) {
      store.set("fig_mode", mode);
      wide.forEach(({ fig }) => {
        fig.setAttribute("data-fig-mode", mode);
        fig.querySelectorAll(".fig-toolbar .ft-mode").forEach((b) => { b.className = "ft-mode" + (b.dataset.m === mode ? " on" : ""); });
      });
    }
    function scaleSvgText() {
      const mob = window.innerWidth <= 640, f = TC.fontCtrl.getFigScale();
      wide.forEach(({ svg }) => svg.querySelectorAll("text[font-size], tspan[font-size]").forEach((el) => {
        if (!el.hasAttribute("data-orig-fs")) el.setAttribute("data-orig-fs", el.getAttribute("font-size"));
        const o = parseFloat(el.getAttribute("data-orig-fs"));
        if (!isFinite(o)) return;
        const base = mob ? (o <= 10 ? o + 2 : o <= 12 ? o + 1.5 : o <= 14 ? o + 1 : o) : o;
        el.setAttribute("font-size", String(Math.round(base * f * 10) / 10));
      }));
    }
    TC._updateSvgTextScale = scaleSvgText;
    wide.forEach(({ fig }) => {
      const bar = document.createElement("div");
      bar.className = "fig-toolbar";
      bar.innerHTML = `<span class="ft-grp"><span>図幅:</span>` +
        `<button type="button" class="ft-mode" data-m="wide">標準拡大</button>` +
        `<button type="button" class="ft-mode" data-m="full">実寸大</button>` +
        `<button type="button" class="ft-mode" data-m="fit">画面幅</button></span>`;
      bar.querySelectorAll(".ft-mode").forEach((b) => b.addEventListener("click", () => applyMode(b.dataset.m)));
      bar.appendChild(TC.fontCtrl.createStepper("fig"));
      fig.insertBefore(bar, fig.firstChild);
    });
    document.querySelectorAll("main .lab > .lh").forEach((lh) => {
      const sp = document.createElement("span");
      sp.className = "lh-sp";
      lh.appendChild(sp);
      lh.appendChild(TC.fontCtrl.createStepper("fig"));
    });
    applyMode(store.get("fig_mode") || "wide");
    scaleSvgText();
    window.addEventListener("resize", scaleSvgText);
  }

  // Hub: chapter cards with quiz progress, and a status bar (#hub-status-bar) with overall progress
  // and the page text stepper. Called from the hub page's own script.
  TC.renderHub = function () {
    const sum = COURSE.summaries || {}, labN = COURSE.labCounts || {};
    let tq = 0, td = 0, tr = 0;
    const cards = document.getElementById("hub-cards");
    if (cards) cards.innerHTML = COURSE.chapters.map((c) => {
      const id = c[0], todo = c[3] === "todo";
      const href = c[2].replace(/^(?!\.\.\/|https?:)/, "chapters/").replace(/^\.\.\//, "");
      const q = todo ? { done: 0, rev: 0, total: 0 } : TC.quizStore.getSummary(id);
      tq += q.total; td += q.done; tr += q.rev;
      let prog = "";
      if (q.total > 0) {
        const pd = Math.round(q.done / q.total * 100), pr = Math.round(q.rev / q.total * 100);
        prog = `<div class="card-prog"><span>${labN[id] ? "LAB " + labN[id] + " · " : ""}問題 ✓${q.done}/${q.total}${q.rev ? ` (★${q.rev})` : ""}</span><span>${pd}%</span></div>` +
          `<div class="card-pbar"><div class="p-done" style="width:${pd}%"></div><div class="p-rev" style="width:${pr}%"></div></div>`;
      }
      return `<a class="${todo ? "todo" : ""}" href="${href}"><span class="id">${id}${todo ? " · 未作成" : ""}</span><b>${c[1]}</b><p>${sum[id] || ""}</p>${prog}</a>`;
    }).join("");
    const bar = document.getElementById("hub-status-bar");
    if (bar) {
      bar.innerHTML = `<div><b>学習進捗:</b> 確認問題 <span class="mono">✓ ${td} / ${tq} 問</span>` +
        (tr ? ` <span class="mono" style="color:var(--warn)">(★ 要復習 ${tr})</span>` : "") +
        (tq ? "" : ` <span class="muted small">（章を開くと問題数が入ります）</span>`) +
        `</div><div class="hub-bar-actions"></div>`;
      bar.querySelector(".hub-bar-actions").appendChild(TC.fontCtrl.createStepper("page"));
    }
  };

  document.addEventListener("DOMContentLoaded", () => {
    TC.fontCtrl.setPageScale(TC.fontCtrl.getPageScale());
    TC.renderMath();
    const id = document.body.dataset.ch;
    if (id === "HUB") return;
    const idx = CHAPTERS.findIndex((c) => c[0] === id);
    const wrap = document.querySelector(".wrap");
    if (!wrap) return;

    // Top bar: back to the list, page text stepper, chapter jump, section / LAB jump.
    const bar = document.createElement("div");
    bar.className = "topbar";
    const here = idx < 0 ? `<option value="" selected disabled>${id || ""} ${(document.querySelector("h1") || {}).textContent || ""}</option>` : "";
    const chOpts = here + CHAPTERS.map((c) => `<option value="${c[2]}"${c[0] === id ? " selected" : ""}>${c[0]} ${c[1]}</option>`).join("");
    const h2s = [...document.querySelectorAll("main h2[id]")];
    const labs = [...document.querySelectorAll("main .lab[id]")];
    const secOpts = `<option value="" disabled selected>この章の内容へ移動…</option>` +
      `<optgroup label="見出し (節)">` + h2s.map((h) => `<option value="#${h.id}">${h.textContent}</option>`).join("") + `</optgroup>` +
      (labs.length ? `<optgroup label="操作演習 (LAB)">` + labs.map((l) => {
        const tag = (l.querySelector(".tagm") || {}).textContent || "LAB";
        const title = (l.querySelector(".lh b") || {}).textContent || l.id;
        return `<option value="#${l.id}">${tag}: ${title}</option>`;
      }).join("") + `</optgroup>` : "");
    bar.innerHTML = `<a class="tb-home" href="${COURSE.hub}" title="${COURSE.title}">← 一覧</a><span class="sp"></span>` +
      `<select class="tb-ch" aria-label="章へ移動">${chOpts}</select>` +
      `<select class="tb-sec" aria-label="この章の内容へ移動">${secOpts}</select>`;
    bar.insertBefore(TC.fontCtrl.createStepper("page"), bar.querySelector(".tb-ch"));
    const secSel = bar.querySelector(".tb-sec");
    bar.querySelector(".tb-ch").addEventListener("change", (e) => { if (e.target.value) location.href = e.target.value; });
    secSel.addEventListener("change", (e) => {
      const t = e.target.value && document.querySelector(e.target.value);
      if (!t) return;
      t.scrollIntoView({ behavior: TC.reducedMotion() ? "auto" : "smooth", block: "start" });
      history.replaceState(null, "", e.target.value);
    });
    if (h2s.length) {
      let ticking = false;
      window.addEventListener("scroll", () => {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(() => {
          ticking = false;
          let active = "";
          for (const h of h2s) if (!h.hidden && h.getBoundingClientRect().top <= 90) active = "#" + h.id;
          if (active && secSel.value !== active) secSel.value = active;
        });
      }, { passive: true });
    }
    wrap.prepend(bar);

    // In-page TOC from h2[id].
    const toc = document.querySelector("nav.intoc");
    if (toc) {
      toc.innerHTML = `<b class="small muted">この章の内容</b><ol>` +
        h2s.map((h) => `<li><a href="#${h.id}">${h.textContent}</a></li>`).join("") + `</ol>`;
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

    enhanceFigures();
    if (idx >= 0) initQuizTracker(id);
  });
})();
