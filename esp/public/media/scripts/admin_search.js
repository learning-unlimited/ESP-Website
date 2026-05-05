(function() {
  function normalize(text) {
    return (text || "").toLowerCase();
  }

  function matches(entry, query) {
    var q = normalize(query);
    if (!q) {
      return true;
    }

    if (normalize(entry.title).indexOf(q) !== -1) {
      return true;
    }

    if (entry.keywords) {
      for (var i = 0; i < entry.keywords.length; i++) {
        if (normalize(entry.keywords[i]).indexOf(q) !== -1) {
          return true;
        }
      }
    }

    return false;
  }

  function groupByCategory(entries) {
    var grouped = {};
    for (var i = 0; i < entries.length; i++) {
      var e = entries[i];
      var cat = e.category || "Other";
      if (!grouped[cat]) {
        grouped[cat] = [];
      }
      grouped[cat].push(e);
    }
    return grouped;
  }

  function renderResults(entries) {
    var container = document.getElementById("admin_search_results");
    var empty = document.getElementById("admin_search_empty");
    if (!container) {
      return;
    }

    container.innerHTML = "";

    if (!entries.length) {
      container.style.display = "none";
      if (empty) {
        empty.style.display = "block";
      }
      return;
    }

    if (empty) {
      empty.style.display = "none";
    }

    var grouped = groupByCategory(entries);
    var cats = [];
    for (var cat in grouped) {
      if (Object.prototype.hasOwnProperty.call(grouped, cat)) {
        cats.push(cat);
      }
    }
    cats.sort();

    for (var i = 0; i < cats.length; i++) {
      var category = cats[i];
      var catDiv = document.createElement("div");
      catDiv.className = "admin-search-category";
      var h4 = document.createElement("h4");
      h4.textContent = category;
      catDiv.appendChild(h4);
      var ul = document.createElement("ul");
      var list = grouped[category];
      for (var j = 0; j < list.length; j++) {
        var e = list[j];
        var li = document.createElement("li");
        var a = document.createElement("a");
        a.setAttribute("href", e.url);
        var strong = document.createElement("strong");
        strong.textContent = e.title;
        a.appendChild(strong);
        li.appendChild(a);
        ul.appendChild(li);
      }
      catDiv.appendChild(ul);
      container.appendChild(catDiv);
    }

    container.style.display = "block";
  }

  function updateSectionVisibility(query) {
    // Phase 1: keep existing sections always visible.
    // This can be extended later to hide sections with no matching items.
  }

  function initAdminSearch() {
    var input = document.getElementById("admin_search_input");
    if (!input || !window.ADMIN_SEARCH_ENTRIES) {
      return;
    }

    input.addEventListener("input", function() {
      var q = input.value || "";
      var all = window.ADMIN_SEARCH_ENTRIES || [];
      if (!q) {
        var container = document.getElementById("admin_search_results");
        var empty = document.getElementById("admin_search_empty");
        if (container) {
          container.style.display = "none";
        }
        if (empty) {
          empty.style.display = "none";
        }
        updateSectionVisibility(q);
        return;
      }

      var filtered = [];
      for (var i = 0; i < all.length; i++) {
        if (matches(all[i], q)) {
          filtered.push(all[i]);
        }
      }

      renderResults(filtered);
      updateSectionVisibility(q);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAdminSearch);
  } else {
    initAdminSearch();
  }
})();

