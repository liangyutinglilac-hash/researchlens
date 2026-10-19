"use strict";
(() => {
  const key = "researchlens.public.draft.v1";
  const fields = ["topic", "question", "notes"];
  const status = document.getElementById("status");
  const setStatus = (message) => { status.textContent = message; };
  const values = () => Object.fromEntries(fields.map(id => [id, document.getElementById(id).value.trim()]));
  try {
    const saved = JSON.parse(localStorage.getItem(key) || "null");
    if (saved && typeof saved === "object") {
      fields.forEach(id => { if (typeof saved[id] === "string") document.getElementById(id).value = saved[id]; });
      setStatus("已恢复此浏览器的草稿；修改后请点击保存。");
    }
  } catch { setStatus("浏览器存储不可用或草稿损坏；仍可填写并导出草稿。"); }
  document.getElementById("draft-form").addEventListener("submit", event => {
    event.preventDefault();
    try { localStorage.setItem(key, JSON.stringify(values())); setStatus("已保存到此浏览器 · " + new Date().toLocaleTimeString("zh-CN")); }
    catch { setStatus("保存失败，浏览器可能禁止存储。请使用导出 Markdown。"); }
  });
  fields.forEach(id => document.getElementById(id).addEventListener("input", () => setStatus("草稿已修改，尚未保存。")));
  document.getElementById("clear").addEventListener("click", () => {
    if (!window.confirm("确定清空此浏览器中的研究草稿？此操作无法撤销。")) return;
    try { localStorage.removeItem(key); } catch { setStatus("无法清除浏览器存储；请检查浏览器设置。"); return; }
    fields.forEach(id => { document.getElementById(id).value = ""; });
    setStatus("已清空草稿。");
  });
  document.getElementById("export").addEventListener("click", () => {
    const draft = values();
    const text = `# ${draft.topic || "研究草稿"}\n\n## 研究问题\n${draft.question}\n\n## 证据与下一步\n${draft.notes}\n\n---\n由用户填写的研究草稿，未经科学有效性核验。\n`;
    const url = URL.createObjectURL(new Blob([text], { type: "text/markdown;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = "ResearchLens研究草稿.md";
    document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    setStatus("已导出当前填写内容。");
  });
  document.querySelectorAll("[data-query]").forEach(button => button.addEventListener("click", () => {
    document.getElementById("keywords").value = button.dataset.query;
    document.getElementById("keywords").focus();
  }));
  document.getElementById("search-form").addEventListener("submit", event => {
    event.preventDefault();
    const query = document.getElementById("keywords").value.trim();
    if (!query) { document.getElementById("keywords").focus(); return; }
    const url = document.getElementById("source").value === "pubmed"
      ? "https://pubmed.ncbi.nlm.nih.gov/?term=" + encodeURIComponent(query)
      : "https://openalex.org/works?search=" + encodeURIComponent(query);
    window.open(url, "_blank", "noopener,noreferrer");
  });
})();
