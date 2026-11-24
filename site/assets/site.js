// fojin.ai landing page behaviour. Progressive: without this file every
// master card and its install command still shows; only the filters, copy
// buttons and the non-default install tabs need it.
(function () {
  "use strict";

  // ---- copy buttons -------------------------------------------------------
  function copyText(text, btn) {
    var done = function () {
      var old = btn.textContent;
      btn.textContent = "已复制";
      setTimeout(function () { btn.textContent = old; }, 1400);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () {});
    }
  }
  document.querySelectorAll(".copy").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var text = btn.getAttribute("data-copy");
      if (!text) {
        var code = btn.parentElement && btn.parentElement.querySelector("code");
        text = code ? code.textContent : "";
      }
      if (text) copyText(text.trim(), btn);
    });
  });

  // ---- master filter: by situation (chips) or by tradition (tabs) ---------
  var cards = Array.prototype.slice.call(document.querySelectorAll("#grid .card"));
  var chips = Array.prototype.slice.call(document.querySelectorAll(".chip"));
  var tabs = Array.prototype.slice.call(document.querySelectorAll(".tabs .tab"));
  var hint = document.getElementById("hint");

  function nameOf(card) {
    var n = card.querySelector(".name");
    return n ? n.textContent : "";
  }

  var grid = document.getElementById("grid");
  var more = document.getElementById("more");
  if (more && grid) {
    more.hidden = false;
    more.addEventListener("click", function () {
      grid.classList.add("expanded");
      more.hidden = true;
    });
  }
  // Any filter shows every match, not just the first six.
  function expand() {
    if (grid) grid.classList.add("expanded");
    if (more) more.hidden = true;
  }

  function apply(pick, trad) {
    if (pick || trad) expand();
    var ids = pick ? pick.split(/\s+/) : null;
    var hits = [];
    cards.forEach(function (c) {
      var id = c.getAttribute("data-id");
      var t = c.getAttribute("data-t");
      var match = ids ? ids.indexOf(id) !== -1 : (!trad || t === trad);
      c.classList.toggle("dim", !match);
      c.classList.toggle("hit", !!ids && match);
      if (match) hits.push(c);
    });
    if (ids) {
      // keep the recommended order: chip lists masters best-first
      hint.textContent = "推荐：" + ids.map(function (id) {
        var c = document.querySelector('#grid .card[data-id="' + id + '"]');
        return c ? nameOf(c) : id;
      }).join("、");
      if (hits[0] && hits[0].getBoundingClientRect().top > window.innerHeight * 0.8) {
        hits[0].scrollIntoView({ block: "center", behavior: "smooth" });
      }
    } else {
      hint.textContent = "";
    }
  }

  chips.forEach(function (chip) {
    chip.setAttribute("aria-pressed", "false");
    chip.addEventListener("click", function () {
      var on = chip.getAttribute("aria-pressed") !== "true";
      chips.forEach(function (c) { c.setAttribute("aria-pressed", "false"); });
      tabs.forEach(function (t) { t.setAttribute("aria-selected", t.getAttribute("data-trad") === "" ? "true" : "false"); });
      if (on) {
        chip.setAttribute("aria-pressed", "true");
        apply(chip.getAttribute("data-pick"), "");
      } else {
        apply("", "");
      }
    });
  });

  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      chips.forEach(function (c) { c.setAttribute("aria-pressed", "false"); });
      tabs.forEach(function (t) { t.setAttribute("aria-selected", t === tab ? "true" : "false"); });
      apply("", tab.getAttribute("data-trad"));
    });
  });

  // ---- light / dark toggle ----------------------------------------------------
  var root = document.documentElement;
  var toggle = document.querySelector(".theme-toggle");
  var themeMeta = document.querySelector('meta[name="theme-color"]');
  function syncToggle() {
    var dark = root.getAttribute("data-theme") === "dark";
    if (toggle) toggle.setAttribute("aria-label", dark ? "切换浅色模式" : "切换深色模式");
    if (themeMeta) themeMeta.setAttribute("content", dark ? "#0f0e0c" : "#f7f8fa");
  }
  if (toggle) {
    toggle.addEventListener("click", function () {
      var dark = root.getAttribute("data-theme") !== "dark";
      if (dark) root.setAttribute("data-theme", "dark");
      else root.removeAttribute("data-theme");
      try { localStorage.setItem("fojin-ai-theme", dark ? "dark" : "light"); } catch (e) {}
      syncToggle();
    });
  }
  syncToggle();

  // ---- example questions fill the hero ask box -------------------------------
  var askQ = document.getElementById("ask-q");
  var askM = document.getElementById("ask-m");
  document.querySelectorAll(".try-q").forEach(function (b) {
    b.addEventListener("click", function () {
      if (askQ) { askQ.value = b.getAttribute("data-q") || ""; askQ.focus(); }
      if (askM && b.getAttribute("data-m")) askM.value = b.getAttribute("data-m");
    });
  });

  // ---- Umami: what visitors actually do here ----------------------------------
  // ask_submit (hero box), card_ask (a card's 提问), copy_install (any copy
  // button). Decides what the page should lead with next time it is trimmed.
  function track(name, data) {
    try { if (window.umami && window.umami.track) window.umami.track(name, data); } catch (e) {}
  }
  var askForm = document.querySelector("form.ask");
  if (askForm) {
    askForm.addEventListener("submit", function () {
      track("ask_submit", { master: (askM && askM.value) || "none" });
    });
  }
  document.querySelectorAll(".card-ask").forEach(function (a) {
    a.addEventListener("click", function () { track("card_ask", { master: a.getAttribute("data-master") }); });
  });
  document.querySelectorAll("a.card-dl").forEach(function (a) {
    a.addEventListener("click", function () { track("skill_download", { master: a.getAttribute("data-master") }); });
  });
  document.querySelectorAll(".copy").forEach(function (b) {
    b.addEventListener("click", function () {
      track("copy_install", { what: b.getAttribute("data-master") || (b.getAttribute("data-copy") || "").slice(0, 40) });
    });
  });

  // ---- header nav: mark the section in view; count clicks ------------------
  var navLinks = Array.prototype.slice.call(document.querySelectorAll("nav.links a"));
  navLinks.forEach(function (a) {
    a.addEventListener("click", function () { track("nav_click", { to: a.getAttribute("href") }); });
  });
  var sectionLinks = navLinks.filter(function (a) { return (a.getAttribute("href") || "").charAt(0) === "#"; });
  if ("IntersectionObserver" in window && sectionLinks.length) {
    var current = null;
    var mark = function (id) {
      if (id === current) return;
      current = id;
      sectionLinks.forEach(function (a) {
        if (a.getAttribute("href") === "#" + id) a.setAttribute("aria-current", "true");
        else a.removeAttribute("aria-current");
      });
    };
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) mark(e.target.id);
        else if (e.target.id === current) mark(null);
      });
    }, { rootMargin: "-40% 0px -55% 0px" });
    sectionLinks.forEach(function (a) {
      var sec = document.querySelector(a.getAttribute("href"));
      if (sec) io.observe(sec);
    });
  }

  // ---- install tabs ---------------------------------------------------------
  var itabs = Array.prototype.slice.call(document.querySelectorAll('.install [role="tab"]'));
  itabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      itabs.forEach(function (t) {
        var sel = t === tab;
        t.setAttribute("aria-selected", sel ? "true" : "false");
        var panel = document.getElementById(t.getAttribute("aria-controls"));
        if (panel) panel.hidden = !sel;
      });
    });
  });
})();
