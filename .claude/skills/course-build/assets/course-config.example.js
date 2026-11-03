// Course data for course.js and the hub page. Hrefs are relative to chapters/.
// A 4th element "todo" marks a planned chapter that is not written yet (hub shows it greyed out).
window.COURSE = {
  title: "コース名",
  hub: "../index.html",
  chapters: [
    ["C01", "章タイトル 1", "C01.html"],
    ["C02", "章タイトル 2", "C02.html", "todo"],
  ],
  summaries: {
    C01: "この章で扱うことを 1 行で。",
  },
};
