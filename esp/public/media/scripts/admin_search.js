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
    var html = "";

    var cats = [];
    for (var cat in grouped) {
      if (Object.prototype.hasOwnProperty.call(grouped, cat)) {
        cats.push(cat);
      }
    }
    cats.sort();

    for (var i = 0; i < cats.length; i++) {
      var category = cats[i];
      html += '<div class="admin-search-category">';
      html += '<h4>' + category + '</h4>';
      html += "<ul>";
      var list = grouped[category];
      for (var j = 0; j < list.length; j++) {
        var e = list[j];
        html += '<li><a href="' + e.url + '"><strong>' + e.title + "</strong></a></li>";
      }
      html += "</ul></div>";
    }

    container.innerHTML = html;
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

