/* AyokBelajar client-side utilities: export (zero-server), markdown render,
   quiz engine, flashcard deck, roadmap tracker, chat with document. */

(function () {
  'use strict';

  function parseJsonScript(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    return JSON.parse(el.textContent);
  }

  function downloadBlob(content, filename, mime) {
    var blob = new Blob([content], { type: mime });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  window.Ayok = {
    downloadMarkdown: function (text, filename) {
      downloadBlob(text, filename || 'ringkasan.md', 'text/markdown');
    },

    downloadAnkiCSV: function (cards, filename) {
      var rows = cards.map(function (c) {
        return '"' + String(c.question || '').replace(/"/g, '""') + '","' +
          String(c.answer || '').replace(/"/g, '""') + '"';
      });
      downloadBlob('\ufeff' + 'Question,Answer\n' + rows.join('\n'), filename || 'flashcards.csv', 'text/csv');
    },

    printView: function () {
      window.print();
    },

    parseJsonScript: parseJsonScript,
  };

  document.addEventListener('DOMContentLoaded', function () {
    var summaryData = parseJsonScript('summary-data');
    if (summaryData !== null && document.getElementById('summary-content')) {
      var markdown = String(summaryData);
      document.getElementById('summary-content').innerHTML = marked.parse(markdown);
      document.getElementById('summary-plain').value = markdown;
    }

    if (document.getElementById('roadmap-list')) {
      initRoadmap();
    }
  });

  function initRoadmap() {
    var docId = document.getElementById('roadmap-list').dataset.documentId;
    var key = 'ayok-roadmap-' + docId;
    var saved;
    try { saved = JSON.parse(localStorage.getItem(key) || '{}'); } catch (e) { saved = {}; }

    document.querySelectorAll('#roadmap-list input[type=checkbox]').forEach(function (cb) {
      var step = cb.dataset.step;
      if (saved[step]) cb.checked = true;
      cb.addEventListener('change', function () {
        saved[step] = cb.checked;
        localStorage.setItem(key, JSON.stringify(saved));
        updateProgress();
      });
    });

    function updateProgress() {
      var boxes = document.querySelectorAll('#roadmap-list input[type=checkbox]');
      var done = Array.prototype.filter.call(boxes, function (b) { return b.checked; }).length;
      var label = document.getElementById('roadmap-progress');
      var bar = document.getElementById('roadmap-progress-bar');
      var pct = boxes.length ? (done / boxes.length) * 100 : 0;
      if (label) label.textContent = done + '/' + boxes.length + ' langkah selesai';
      if (bar) bar.style.width = pct + '%';
    }
    updateProgress();
  }

  window.tabs = function () {
    return { active: 'summary' };
  };

  window.flashcardDeck = function () {
    var cards = parseJsonScript('flashcards-data') || [];
    return {
      cards: cards,
      index: 0,
      flipped: false,
      gridMode: false,
      mastered: new Set(),
      get current() { return this.cards[this.index] || null; },
      flip: function () { this.flipped = !this.flipped; },
      next: function () {
        if (this.index < this.cards.length - 1) { this.index++; this.flipped = false; }
      },
      prev: function () {
        if (this.index > 0) { this.index--; this.flipped = false; }
      },
      rate: function (ok) {
        if (ok) this.mastered.add(this.index);
        else this.mastered.delete(this.index);
      },
    };
  };

  window.quizEngine = function () {
    var questions = parseJsonScript('quiz-data') || [];
    return {
      questions: questions,
      index: 0,
      selected: null,
      locked: false,
      answers: [],
      startTime: Date.now(),
      now: Date.now(),
      finished: false,
      review: false,
      _timer: null,
      init: function () {
        var self = this;
        this._timer = setInterval(function () { self.now = Date.now(); }, 1000);
      },
      destroy: function () {
        if (this._timer) clearInterval(this._timer);
      },
      get current() { return this.questions[this.index] || null; },
      get score() {
        return this.answers.filter(function (a) { return a.correct; }).length;
      },
      get percent() {
        return this.questions.length ? Math.round((this.score / this.questions.length) * 100) : 0;
      },
      get elapsed() {
        return Math.round((this.now - this.startTime) / 1000);
      },
      choose: function (i) {
        if (this.locked) return;
        this.selected = i;
        this.locked = true;
        this.answers[this.index] = { chosen: i, correct: i === this.current.correctAnswer };
      },
      next: function () {
        this.index++;
        this.selected = null;
        this.locked = false;
        if (this.index >= this.questions.length) {
          this.finished = true;
          if (this._timer) { clearInterval(this._timer); this._timer = null; }
        }
      },
      reset: function () {
        this.index = 0; this.selected = null; this.locked = false;
        this.answers = []; this.startTime = Date.now(); this.now = Date.now();
        this.finished = false; this.review = false;
        if (!this._timer) {
          var self = this;
          this._timer = setInterval(function () { self.now = Date.now(); }, 1000);
        }
      },
      missed: function () {
        var self = this;
        return this.questions.filter(function (_, i) {
          return !self.answers[i] || !self.answers[i].correct;
        });
      },
    };
  };

  window.chatPanel = function () {
    return {
      open: false,
      message: '',
      sending: false,
      send: function () {
        var self = this;
        var text = this.message.trim();
        if (!text || this.sending) return;
        this.message = '';
        this.sending = true;

        var box = document.getElementById('chat-box');
        box.insertAdjacentHTML('beforeend', messageBubble('user', text));
        box.scrollTop = box.scrollHeight;

        var docId = document.getElementById('chat-panel').dataset.documentId;
        fetch('/workspace/' + docId + '/chat/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
          body: JSON.stringify({ message: text }),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            box.insertAdjacentHTML('beforeend', messageBubble('assistant', data.content || 'Tidak ada jawaban.'));
            box.scrollTop = box.scrollHeight;
          })
          .catch(function () {
            box.insertAdjacentHTML('beforeend', messageBubble('assistant', 'Gagal terhubung. Coba lagi.'));
          })
          .finally(function () { self.sending = false; });
      },
    };
  };

  function messageBubble(role, text) {
    var isUser = role === 'user';
    return '<div class="flex ' + (isUser ? 'justify-end' : 'justify-start') + '">' +
      '<div class="max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm ' +
      (isUser ? 'bg-primary text-white' : 'bg-slate-100 text-slate-800') + '">' +
      escapeHtml(text) + '</div></div>';
  }

  function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function getCookie(name) {
    var match = document.cookie.match(new RegExp('(^|;\\s*)' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[2]) : '';
  }
})();
