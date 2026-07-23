/* PassionWavesMedia — shared front-end behavior.
   Config is injected by the build as window.PW = { supabaseUrl, supabaseAnonKey }. */
(function () {
  var cfg = window.PW || {};
  var haveDB = !!(cfg.supabaseUrl && cfg.supabaseAnonKey);

  /* ---------- scroll reveal ---------- */
  var io = new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
  }, { threshold: 0.12 });
  document.querySelectorAll(".reveal").forEach(function (el) { io.observe(el); });

  /* ---------- category filter (cards are static; we just show/hide) ---------- */
  window.pwFilter = function (btn, cat) {
    document.querySelectorAll(".filters .chip").forEach(function (c) { c.setAttribute("aria-pressed", "false"); });
    btn.setAttribute("aria-pressed", "true");
    document.querySelectorAll("#grid .card").forEach(function (card) {
      card.style.display = (cat === "all" || card.dataset.cat === cat) ? "flex" : "none";
    });
    var feat = document.getElementById("featured");
    if (feat) feat.style.display = (cat === "all") ? "" : "none";
  };

  /* ---------- Supabase helper ---------- */
  function rpc(fn, args) {
    return fetch(cfg.supabaseUrl + "/rest/v1/rpc/" + fn, {
      method: "POST",
      headers: {
        "apikey": cfg.supabaseAnonKey,
        "Authorization": "Bearer " + cfg.supabaseAnonKey,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(args)
    }).then(function (r) { if (!r.ok) throw new Error("rpc"); return r.json(); });
  }

  function fmt(n) {
    if (n == null) return "—";
    if (n >= 1000) return (n / 1000).toFixed(1).replace(/\.0$/, "") + "k";
    return String(n);
  }

  /* ---------- likes + views on an article page ---------- */
  window.pwInitArticle = function (slug) {
    var likeBtn = document.getElementById("likeBtn");
    var likeCount = document.getElementById("likeCount");
    var viewCount = document.getElementById("viewCount");
    if (!likeBtn) return;

    var likedKey = "pw_liked_" + slug;
    var alreadyLiked = localStorage.getItem(likedKey) === "1";
    if (alreadyLiked) likeBtn.classList.add("liked");

    // Register a view + load counts.
    if (haveDB) {
      rpc("pw_view", { p_slug: slug })
        .then(function (rows) {
          var row = Array.isArray(rows) ? rows[0] : rows;
          if (row) { likeCount.textContent = fmt(row.likes); viewCount.textContent = fmt(row.views) + " reads"; }
        })
        .catch(function () { viewCount.textContent = ""; });
    } else {
      // Local fallback: no shared counts, but the button still works visually.
      viewCount.textContent = "";
      likeCount.textContent = alreadyLiked ? "1" : "0";
    }

    likeBtn.addEventListener("click", function () {
      if (localStorage.getItem(likedKey) === "1") return; // one like per browser
      localStorage.setItem(likedKey, "1");
      likeBtn.classList.add("liked", "pop");
      setTimeout(function () { likeBtn.classList.remove("pop"); }, 360);

      if (haveDB) {
        rpc("pw_like", { p_slug: slug })
          .then(function (rows) { var row = Array.isArray(rows) ? rows[0] : rows; if (row) likeCount.textContent = fmt(row.likes); })
          .catch(function () {});
      } else {
        likeCount.textContent = String((parseInt(likeCount.textContent, 10) || 0) + 1);
      }
    });
  };
  window.pwArchiveFilter = function (btn, cat) {
    document.querySelectorAll(".filters .chip").forEach(function (c) { c.setAttribute("aria-pressed", "false"); });
    btn.setAttribute("aria-pressed", "true");
    document.querySelectorAll(".cat-group").forEach(function (g) {
      g.style.display = (cat === "all" || g.dataset.cat === cat) ? "" : "none";
    });
  };
  window.pwShowMore = function (btn) {
    var g = btn.closest(".cat-group"); if (!g) return;
    g.querySelectorAll(".card.extra").forEach(function (c) { c.classList.remove("extra"); });
    btn.remove();
  };
  window.pwArchiveInit = function () {
    var h = decodeURIComponent((location.hash || "").replace("#", "")); if (!h) return;
    var chip = [].slice.call(document.querySelectorAll(".filters .chip"))
      .filter(function (x) { return x.textContent.trim().toLowerCase() === h.toLowerCase(); })[0];
    if (chip) chip.click();
  };
})();
