// Syntax colouring for code blocks (highlight.js 11.9.0, bundled locally).
// Targets <pre class="code"> and <pre class="cNN-code|cNN-log">. The language comes from
// data-lang on the <pre> when present, otherwise from a guess on the text; logs and status
// lines are left plain. Spans already in a block (.ln line numbers, .cm comments) are kept:
// only the text between them is coloured.
(function () {
  const SKIP = ".ln, .cm";
  function guess(t) {
    if (/^\s*(import |from \S+ import |def |print\()/m.test(t)) return "python";
    if (/\b(create_clock|create_generated_clock|set_clock_groups|set_device|add_file|set_option|run all|IO_LOC|IO_PORT)\b/.test(t)) return "tcl";
    if (/^\s*(iverilog|vvp|cd |python3? )/m.test(t)) return "bash";
    if (/\b(uint\d+_t|send_pixel|while \(true\))\b|for \(\w+ = 0;/.test(t)) return "c";
    if (/\b(module|always|wire|reg|localparam|assign|function|begin|end|posedge|negedge)\b|\d+'[bdh]/.test(t)) return "verilog";
    return null;
  }
  function paint(text, lang) {
    return window.hljs.highlight(text, { language: lang, ignoreIllegals: true }).value;
  }
  function run() {
    if (!window.hljs) return;
    document.querySelectorAll('pre.code, pre[class*="-code"], pre[class*="-log"]').forEach((pre) => {
      const host = pre.querySelector(":scope > code") || pre;
      const lang = pre.dataset.lang || guess(host.textContent);
      if (!lang || lang === "none" || !window.hljs.getLanguage(lang)) return;
      pre.classList.add("hlc");
      if (!host.querySelector("*")) { host.innerHTML = paint(host.textContent, lang); return; }
      const walker = document.createTreeWalker(host, NodeFilter.SHOW_TEXT);
      const nodes = [];
      while (walker.nextNode()) { const n = walker.currentNode; if (n.nodeValue.trim() && !n.parentElement.closest(SKIP)) nodes.push(n); }
      nodes.forEach((n) => {
        const tpl = document.createElement("template");
        tpl.innerHTML = paint(n.nodeValue, lang);
        n.replaceWith(tpl.content);
      });
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run); else run();
})();
