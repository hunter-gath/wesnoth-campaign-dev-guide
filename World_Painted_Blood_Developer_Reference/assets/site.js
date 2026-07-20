(() => {
  const root = document.documentElement;
  const saved = localStorage.getItem("wpb-reference-theme");
  if (saved) root.dataset.theme = saved;

  document.querySelectorAll("[data-theme-toggle]").forEach(button => {
    const setLabel = () => {
      const current = root.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      button.textContent = current === "dark" ? "Use light theme" : "Use dark theme";
    };
    setLabel();
    button.addEventListener("click", () => {
      const current = root.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      const next = current === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      localStorage.setItem("wpb-reference-theme", next);
      setLabel();
    });
  });

  document.querySelectorAll("[data-table-filter]").forEach(input => {
    const table = document.querySelector(input.dataset.tableFilter);
    if (!table) return;
    input.addEventListener("input", () => {
      const query = input.value.toLowerCase().trim();
      table.querySelectorAll("tbody tr").forEach(row => {
        row.hidden = !row.innerText.toLowerCase().includes(query);
      });
    });
  });

  const escapeHtml = value => String(value).replace(/[&<>"']/g, ch => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
  }[ch]));
  const highlight = (text, terms) => {
    let output = escapeHtml(text);
    terms.filter(Boolean).sort((a,b) => b.length-a.length).forEach(term => {
      const safe = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      output = output.replace(new RegExp(`(${safe})`, "ig"), "<mark>$1</mark>");
    });
    return output;
  };

  const searchPage = document.querySelector("[data-search-page]");
  if (searchPage && Array.isArray(window.WPB_SEARCH_INDEX)) {
    const form = searchPage.querySelector("[data-search-form]");
    const input = form.querySelector('input[name="q"]');
    const resultsNode = searchPage.querySelector("[data-search-results]");
    const statusNode = searchPage.querySelector("[data-search-status]");
    const run = query => {
      const terms = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
      if (!terms.length) {
        resultsNode.innerHTML = "";
        statusNode.textContent = "Enter one or more terms.";
        return;
      }
      const ranked = window.WPB_SEARCH_INDEX.map(item => {
        const title = item.title.toLowerCase();
        const headings = item.headings.toLowerCase();
        const text = item.text.toLowerCase();
        let score = 0;
        for (const term of terms) {
          if (!text.includes(term) && !title.includes(term) && !headings.includes(term)) return null;
          if (title.includes(term)) score += 30;
          if (headings.includes(term)) score += 12;
          score += Math.min(10, text.split(term).length - 1);
        }
        return {...item, score};
      }).filter(Boolean).sort((a,b) => b.score-a.score || a.title.localeCompare(b.title));
      statusNode.textContent = `${ranked.length} result${ranked.length === 1 ? "" : "s"} for “${query}”.`;
      if (!ranked.length) {
        resultsNode.innerHTML = '<div class="search-empty">No matching pages. Try fewer terms or identifiers such as <code>wpb_corruption</code>, <code>Nightgaunt</code>, or <code>command pylon</code>.</div>';
        return;
      }
      resultsNode.innerHTML = ranked.slice(0, 80).map(item => `
        <article class="search-result">
          <h3><a href="${escapeHtml(item.path)}">${highlight(item.title, terms)}</a></h3>
          <div class="search-path">${escapeHtml(item.path)}</div>
          <p>${highlight(item.excerpt, terms)}</p>
        </article>`).join("");
    };
    const params = new URLSearchParams(location.search);
    const initial = params.get("q") || "";
    input.value = initial;
    run(initial);
    form.addEventListener("submit", event => {
      event.preventDefault();
      const query = input.value.trim();
      const url = new URL(location.href);
      if (query) url.searchParams.set("q", query); else url.searchParams.delete("q");
      history.replaceState(null, "", url);
      run(query);
    });
    input.addEventListener("input", () => run(input.value));
  }

  document.addEventListener("keydown", event => {
    if (event.key === "/" && !/input|textarea|select/i.test(document.activeElement.tagName)) {
      const field = document.querySelector(".sidebar-search input");
      if (field) { event.preventDefault(); field.focus(); }
    }
  });
})();
