// Sohbet sayfası: yeni mesajları birkaç saniyede bir çeker.
// Mesaj içerikleri yalnızca textContent ile eklenir; HTML olarak yorumlanmaz (XSS koruması).
(function () {
  "use strict";

  var log = document.getElementById("chat-log");
  if (!log) return;

  var pollUrl = log.getAttribute("data-poll-url");
  var lastId = parseInt(log.getAttribute("data-last-id"), 10) || 0;
  var status = log.getAttribute("data-status");
  var delay = 4000;
  var maxDelay = 30000;
  var timer = null;

  function scrollToBottom() {
    log.scrollTop = log.scrollHeight;
  }

  function addMessage(msg) {
    var li = document.createElement("li");
    li.className = "bubble" + (msg.mine ? " mine" : "");
    var text = document.createElement("div");
    text.className = "text";
    text.textContent = msg.body;
    var meta = document.createElement("div");
    meta.className = "meta";
    var time = document.createElement("time");
    time.textContent = msg.time;
    meta.appendChild(time);
    li.appendChild(text);
    li.appendChild(meta);
    log.appendChild(li);
  }

  function schedule() {
    timer = window.setTimeout(poll, document.hidden ? maxDelay : delay);
  }

  function poll() {
    fetch(pollUrl + "?after=" + encodeURIComponent(lastId), {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        delay = 4000;
        if (data.messages && data.messages.length) {
          data.messages.forEach(function (m) {
            if (m.id > lastId) {
              addMessage(m);
              lastId = m.id;
            }
          });
          scrollToBottom();
        }
        // Durum değiştiyse (kabul edildi, kapandı…) sayfayı yenile.
        if (data.status !== status) {
          window.location.reload();
          return;
        }
        schedule();
      })
      .catch(function () {
        delay = Math.min(delay * 2, maxDelay);
        schedule();
      });
  }

  scrollToBottom();
  if (status === "active" || status === "pending") schedule();

  // Enter ile gönder, Shift+Enter ile yeni satır.
  var composer = document.querySelector(".composer textarea");
  if (composer) {
    composer.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        if (composer.value.trim()) composer.form.requestSubmit();
      }
    });
    if (window.location.hash === "#yaz") composer.focus();
  }

  document.addEventListener("visibilitychange", function () {
    if (!document.hidden && timer) {
      window.clearTimeout(timer);
      poll();
    }
  });
})();
