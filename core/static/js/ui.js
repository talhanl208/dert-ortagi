// Dert Ortağı — küçük arayüz yardımcıları.
// Sayfa JavaScript olmadan da çalışır; bunlar yalnızca kolaylık sağlar.
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    // Karakter sayacı: data-counter="1500"
    document.querySelectorAll("[data-counter]").forEach(function (field) {
      var max = parseInt(field.getAttribute("data-counter"), 10);
      var counter = document.createElement("span");
      counter.className = "counter";
      counter.setAttribute("aria-live", "polite");
      field.insertAdjacentElement("afterend", counter);
      var update = function () {
        counter.textContent = field.value.length + " / " + max;
      };
      field.addEventListener("input", update);
      update();
    });

    // Geri dönülemez işlemlerden önce onay: data-confirm="..."
    document.querySelectorAll("[data-confirm]").forEach(function (button) {
      var form = button.closest("form");
      if (!form) return;
      form.addEventListener("submit", function (event) {
        if (!window.confirm(button.getAttribute("data-confirm"))) {
          event.preventDefault();
        }
      });
    });

    // "Vazgeç" bağlantıları mümkünse bir önceki sayfaya döner.
    document.querySelectorAll("[data-back]").forEach(function (link) {
      link.addEventListener("click", function (event) {
        if (window.history.length > 1) {
          event.preventDefault();
          window.history.back();
        }
      });
    });

    // Kayıt formunda rastgele rumuz önerisi
    var dice = document.querySelector("[data-nick-dice]");
    var wordsEl = document.getElementById("nick-words");
    if (dice && wordsEl) {
      var words = JSON.parse(wordsEl.textContent);
      var input = document.getElementById("id_username");
      var pick = function (list) {
        return list[Math.floor(Math.random() * list.length)];
      };
      dice.hidden = false;
      dice.addEventListener("click", function () {
        var n = 10 + Math.floor(Math.random() * 90);
        input.value = pick(words.adjectives) + pick(words.animals) + n;
        input.focus();
      });
    }

    // Açılır menüler: dışarı tıklanınca veya Esc ile kapanır.
    var menus = document.querySelectorAll("details.user-menu, details.more-menu, details.mobile-menu");
    document.addEventListener("click", function (event) {
      menus.forEach(function (menu) {
        if (menu.open && !menu.contains(event.target)) menu.open = false;
      });
    });
    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape") return;
      menus.forEach(function (menu) {
        if (menu.open) {
          menu.open = false;
          menu.querySelector("summary").focus();
        }
      });
    });
  });
})();
