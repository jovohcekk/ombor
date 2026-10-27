(function () {
  const translationsNode = document.getElementById("javascript-translations");
  const translations = translationsNode ? JSON.parse(translationsNode.textContent) : {};
  const language = document.documentElement.lang || "uz";
  const numberFormatter = new Intl.NumberFormat(language);
  const priceFormatter = new Intl.NumberFormat(language, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const sidebar = document.getElementById("sidebar");
  const toggle = document.getElementById("sidebarToggle");
  const backdrop = document.getElementById("sidebarBackdrop");

  function closeSidebar() {
    if (!sidebar) return;
    sidebar.classList.remove("open");
    if (backdrop) backdrop.classList.remove("show");
    if (toggle) {
      toggle.setAttribute("aria-expanded", "false");
      toggle.setAttribute("aria-label", translations.open_navigation);
    }
  }

  if (toggle && sidebar) {
    toggle.addEventListener("click", () => {
      const isOpen = sidebar.classList.toggle("open");
      if (backdrop) backdrop.classList.toggle("show", isOpen);
      toggle.setAttribute("aria-expanded", String(isOpen));
      toggle.setAttribute("aria-label", isOpen ? translations.close_navigation : translations.open_navigation);
    });
  }
  if (backdrop) {
    backdrop.addEventListener("click", closeSidebar);
  }
  if (sidebar) {
    sidebar.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", closeSidebar);
    });
  }
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && sidebar && sidebar.classList.contains("open")) {
      closeSidebar();
      if (toggle) toggle.focus();
    }
  });
  window.addEventListener("resize", () => {
    if (window.matchMedia("(min-width: 992px)").matches) closeSidebar();
  });

  const themeToggle = document.getElementById("themeToggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const html = document.documentElement;
      const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
      html.setAttribute("data-theme", next);
      try {
        localStorage.setItem("ombor-theme", next);
      } catch (e) {
        // Keep the selected theme for this page even when browser storage is unavailable.
      }
    });
  }

  document.querySelectorAll("form[data-stock-form]").forEach((form) => {
    let products = [];
    try {
      products = JSON.parse(form.getAttribute("data-products") || "[]");
    } catch (e) {
      products = [];
    }
    const type = form.getAttribute("data-stock-form");
    const select = form.querySelector("#id_product");
    const qty = form.querySelector("#id_quantity");
    const price = form.querySelector("#id_unit_price");
    const hint = form.querySelector("#stockHint");

    function currentProduct() {
      const id = select ? Number(select.value) : null;
      return products.find((p) => Number(p.id) === id);
    }

    function refreshHint() {
      const p = currentProduct();
      if (!p || !hint) return;
      hint.textContent = `${translations.on_hand}: ${numberFormatter.format(p.quantity)}. ${translations.purchase} ${priceFormatter.format(Number(p.purchase_price))} / ${translations.selling} ${priceFormatter.format(Number(p.selling_price))}.`;
      if (price && !price.value) {
        price.value = type === "OUT" ? p.selling_price : p.purchase_price;
      }
    }

    if (select) select.addEventListener("change", () => {
      const p = currentProduct();
      if (price && p) price.value = type === "OUT" ? p.selling_price : p.purchase_price;
      refreshHint();
    });
    refreshHint();

    form.addEventListener("submit", (event) => {
      const p = currentProduct();
      const quantity = qty ? Number(qty.value) : 0;
      if (!p) return;
      if (quantity < 1) {
        event.preventDefault();
        alert(translations.quantity_minimum);
        return;
      }
      if (type === "OUT" && quantity > Number(p.quantity)) {
        event.preventDefault();
        alert(translations.insufficient_stock);
      }
    });
  });

  window.initDashboardCharts = function (data) {
    const chartLanguage = document.documentElement.lang || "uz";
    const dateFormatter = new Intl.DateTimeFormat(chartLanguage, {
      day: "numeric",
      month: "short",
    });
    const chartDates = data.labels.map((label) => {
      const date = new Date(`${label}T00:00:00`);
      return Number.isNaN(date.getTime()) ? label : dateFormatter.format(date);
    });
    const chartText = getComputedStyle(document.documentElement).getPropertyValue("--muted").trim() || "#a6b1cb";
    const chartGrid = getComputedStyle(document.documentElement).getPropertyValue("--stroke").trim() || "rgba(210, 222, 255, 0.11)";
    const chartAnimation = window.matchMedia("(prefers-reduced-motion: reduce)").matches
      ? false
      : { duration: 450 };
    const stockEl = document.getElementById("stockChart");
    if (stockEl && window.Chart) {
      new Chart(stockEl, {
        type: "line",
        data: {
          labels: chartDates,
          datasets: [
            { label: translations.stock_in, data: data.stock_in, borderColor: "#62ddb0", backgroundColor: "rgba(98, 221, 176, 0.12)", tension: 0.32, fill: true },
            { label: translations.stock_out, data: data.stock_out, borderColor: "#ff8298", backgroundColor: "rgba(255, 130, 152, 0.08)", tension: 0.32, fill: true },
          ],
        },
        options: {
          responsive: true,
          locale: language,
          animation: chartAnimation,
          plugins: { legend: { position: "bottom", labels: { color: chartText, usePointStyle: true, boxWidth: 8 } } },
          scales: {
            x: { ticks: { color: chartText }, grid: { color: chartGrid } },
            y: { ticks: { color: chartText }, grid: { color: chartGrid }, beginAtZero: true },
          },
        },
      });
    }
    const catEl = document.getElementById("categoryChart");
    if (catEl && window.Chart) {
      new Chart(catEl, {
        type: "doughnut",
        data: {
          labels: data.categories,
          datasets: [{ data: data.category_counts, backgroundColor: ["#987cff", "#6387ff", "#73d8ef", "#62ddb0", "#ffc875", "#ff8298", "#c28dff"], borderColor: "rgba(11, 15, 29, 0.7)", borderWidth: 2 }],
        },
        options: {
          locale: language,
          animation: chartAnimation,
          plugins: { legend: { position: "bottom", labels: { color: chartText, usePointStyle: true, boxWidth: 8 } } },
        },
      });
    }
    const prodEl = document.getElementById("productChart");
    if (prodEl && window.Chart && data.product_stats) {
      new Chart(prodEl, {
        type: "bar",
        data: {
          labels: [translations.active, translations.inactive, translations.low_stock],
          datasets: [{
            label: translations.products,
            data: [data.product_stats.active, data.product_stats.inactive, data.product_stats.low],
            backgroundColor: ["#6387ff", "#7f8ba7", "#ffc875"],
          }],
        },
        options: {
          locale: language,
          animation: chartAnimation,
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: chartText }, grid: { display: false } },
            y: { beginAtZero: true, ticks: { color: chartText }, grid: { color: chartGrid } },
          },
        },
      });
    }
  };
})();
