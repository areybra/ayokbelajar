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

    renderMindmap: function () {
      var container = document.getElementById('mindmap-container');
      if (!container || !window.markmap || !window.markmap.autoLoader) return;
      var summary = parseJsonScript('summary-data') || '';
      var md = (summary ? '# Rangkuman\n\n' : '') + summary;
      if (!summary) {
        container.innerHTML = '';
        return;
      }
      container.textContent = md;
      container.dataset.rendered = '1';
      // Tunggu tab terlihat (x-cloak) agar ukuran container sudah terhitung
      // oleh CSS, sehingga markmap.fit() mengisi kotak mind map sepenuhnya.
      setTimeout(function () {
        window.markmap.autoLoader.render(container);
      }, 60);
    },

    parseJsonScript: parseJsonScript,
  };

  document.addEventListener('DOMContentLoaded', function () {
    var summaryData = parseJsonScript('summary-data');
    var savedHtml = parseJsonScript('summary-html-data');
    var summaryContent = document.getElementById('summary-content');
    var summaryPlain = document.getElementById('summary-plain');
    if (summaryContent) {
      if (savedHtml && String(savedHtml).trim()) {
        summaryContent.innerHTML = savedHtml;
        if (summaryPlain) summaryPlain.value = summaryData !== null ? String(summaryData) : '';
      } else if (summaryData !== null) {
        summaryContent.innerHTML = marked.parse(String(summaryData));
        if (summaryPlain) summaryPlain.value = String(summaryData);
      }
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

  window.summaryEditor = function () {
    var editorEl = null;
    var savedRange = null;

    function getRange() {
      var sel = window.getSelection();
      if (sel.rangeCount > 0) return sel.getRangeAt(0).cloneRange();
      return null;
    }
    function restoreRange() {
      if (!savedRange || !editorEl) return;
      editorEl.focus();
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(savedRange);
    }
    function captureRange() {
      if (editorEl && editorEl.contains(window.getSelection().anchorNode)) {
        savedRange = getRange();
      }
    }
    function exec(cmd, value) {
      restoreRange();
      document.execCommand(cmd, false, value || null);
      savedRange = getRange();
    }

    return {
      editing: false,
      saving: false,
      statusText: '',
      initialized: false,
      openEditor: function () {
        if (this.editing) return;
        this.editing = true;
        var self2 = this;
        this.$nextTick(function () {
          requestAnimationFrame(function () {
            self2.initEditor();
          });
        });
      },
      initEditor: function () {
        if (this.initialized) return;
        editorEl = document.getElementById('summary-editor');
        if (!editorEl) return;
        var savedHtml = parseJsonScript('summary-html-data') || '';
        var summaryData = parseJsonScript('summary-data') || '';
        var initialHtml = (savedHtml && String(savedHtml).trim())
          ? savedHtml
          : (summaryData ? marked.parse(String(summaryData)) : '');
        editorEl.innerHTML = initialHtml || '';

        // Tombol toolbar -> document.execCommand
        var self2 = this;
        document.querySelectorAll('.rt-toolbar [data-cmd]').forEach(function (btn) {
          btn.addEventListener('mousedown', function (e) { e.preventDefault(); });
          btn.addEventListener('click', function () {
            var cmd = btn.getAttribute('data-cmd');
            var val = btn.getAttribute('data-val') || undefined;
            if (cmd === 'createLink') {
              var url = window.prompt('Alamat URL tautan:', 'https://');
              if (url) { restoreRange(); document.execCommand('createLink', false, url); }
              return;
            }
            exec(cmd, val);
            self2.statusText = 'Ada perubahan belum disimpan';
          });
        });
        // Input warna (foreColor / hiliteColor)
        document.querySelectorAll('.rt-toolbar input[type=color]').forEach(function (input) {
          input.addEventListener('input', function () {
            exec(input.getAttribute('data-cmd'), input.value);
            self2.statusText = 'Ada perubahan belum disimpan';
          });
        });

        editorEl.addEventListener('keyup', captureRange);
        editorEl.addEventListener('mouseup', captureRange);
        editorEl.addEventListener('keydown', function () {
          self2.statusText = 'Ada perubahan belum disimpan';
        });
        editorEl.addEventListener('blur', captureRange);

        this.initialized = true;
        editorEl.focus();
        var end = editorEl.textContent.trim().length;
        try {
          var r = document.createRange();
          r.selectNodeContents(editorEl);
          r.collapse(false);
          var sel = window.getSelection();
          sel.removeAllRanges();
          sel.addRange(r);
          savedRange = r.cloneRange();
        } catch (e) { /* abaikan */ }
      },
      save: function (closeAfter) {
        var self2 = this;
        if (!editorEl || this.saving) return;
        var html = editorEl.innerHTML.trim();
        if (!editorEl.textContent.trim()) {
          this.statusText = 'Rangkuman tidak boleh kosong.';
          return;
        }
        this.saving = true;
        var wrap = editorEl.closest('[data-document-id]');
        var docId = wrap ? wrap.dataset.documentId
          : (document.querySelector('[data-document-id]') || {}).dataset.documentId;
        fetch('/workspace/' + docId + '/summary/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
          body: JSON.stringify({ html: html }),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data && data.ok) {
              var content = document.getElementById('summary-content');
              if (content) content.innerHTML = data.html;
              var plain = document.getElementById('summary-plain');
              if (plain) plain.value = editorEl.textContent;
              self2.statusText = 'Tersimpan ✓';
              if (closeAfter) self2.editing = false;
            } else {
              self2.statusText = (data && data.error) || 'Gagal menyimpan.';
            }
          })
          .catch(function () { self2.statusText = 'Gagal terhubung. Coba lagi.'; })
          .finally(function () { self2.saving = false; });
      },
      cancelEdit: function () {
        this.editing = false;
        this.statusText = '';
      },
    };
  };

  window.examEngine = function () {
    var EXAM_MINUTES = 30;
    var EXAM_DURATION = EXAM_MINUTES * 60;
    var questions = parseJsonScript('exam-data') || [];
    return {
      questions: questions,
      index: 0,
      answers: {},
      remaining: EXAM_DURATION,
      running: false,
      finished: false,
      review: false,
      generating: false,
      error: '',
      _timer: null,
      get current() { return this.questions[this.index] || null; },
      get answeredCount() { return Object.keys(this.answers).length; },
      get score() {
        var self = this;
        return this.questions.reduce(function (acc, q, i) {
          return acc + (self.answers[i] === q.correctAnswer ? 1 : 0);
        }, 0);
      },
      get percent() { return this.questions.length ? Math.round((this.score / this.questions.length) * 100) : 0; },
      get wrongCount() { return this.questions.length - this.score - this.unansweredCount; },
      get unansweredCount() { return this.questions.length - this.answeredCount; },
      get mmss() {
        var m = Math.floor(this.remaining / 60);
        var s = this.remaining % 60;
        return m + ':' + String(s).padStart(2, '0');
      },
      get timeUsedLabel() {
        var used = EXAM_DURATION - this.remaining;
        var m = Math.floor(used / 60);
        var s = used % 60;
        return m + ' menit ' + s + ' detik';
      },
      generate: function () {
        var self = this;
        this.generating = true;
        this.error = '';
        var docId = document.querySelector('[data-document-id]').dataset.documentId;
        fetch('/workspace/' + docId + '/exam/generate/', {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken') },
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data && data.ok && data.exam) {
              self.questions = data.exam;
              self.start();
            } else {
              self.error = (data && data.error) || 'Gagal generate ujian.';
            }
          })
          .catch(function () { self.error = 'Gagal terhubung. Coba lagi.'; })
          .finally(function () { self.generating = false; });
      },
      start: function () {
        var self = this;
        this.answers = {};
        this.index = 0;
        this.finished = false;
        this.review = false;
        this.remaining = EXAM_DURATION;
        this.running = true;
        if (this._timer) clearInterval(this._timer);
        this._timer = setInterval(function () {
          self.remaining--;
          if (self.remaining <= 0) {
            self.remaining = 0;
            self.finish();
          }
        }, 1000);
      },
      choose: function (i) {
        if (!this.running || this.finished) return;
        this.answers[this.index] = i;
      },
      go: function (i) {
        if (i < 0 || i >= this.questions.length) return;
        this.index = i;
      },
      submit: function () {
        this.finish();
      },
      finish: function () {
        if (this._timer) { clearInterval(this._timer); this._timer = null; }
        this.running = false;
        this.finished = true;
        this.review = false;
      },
      answerStatus: function (i) {
        if (this.answers[i] === undefined) return 'unanswered';
        return this.answers[i] === this.questions[i].correctAnswer ? 'correct' : 'wrong';
      },
    };
  };

  window.resourcesPanel = function () {
    return {
      search: function (query, engine) {
        var q = encodeURIComponent(query || '');
        var url = engine === 'youtube'
          ? 'https://www.youtube.com/results?search_query=' + q
          : engine === 'books'
          ? 'https://www.google.com/search?tbm=bks&q=' + q
          : 'https://www.google.com/search?q=' + q;
        window.open(url, '_blank', 'noopener noreferrer');
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
