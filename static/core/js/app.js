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
    theme: {
      STORAGE_KEY: 'ayok-theme',
      getMode: function () {
        try {
          var stored = localStorage.getItem('ayok-theme');
          if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
        } catch (e) { /* localStorage tidak tersedia */ }
        return 'system';
      },
      isDark: function () {
        var mode = this.getMode();
        if (mode === 'dark') return true;
        if (mode === 'light') return false;
        return !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
      },
      apply: function () {
        document.documentElement.classList.toggle('dark', this.isDark());
        syncThemeIcons();
      },
      set: function (mode) {
        if (mode !== 'light' && mode !== 'dark' && mode !== 'system') return;
        try { localStorage.setItem('ayok-theme', mode); } catch (e) { /* abaikan */ }
        this.apply();
      },
      toggle: function () {
        this.set(document.documentElement.classList.contains('dark') ? 'light' : 'dark');
      },
    },

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

    downloadKit: function (filename, title) {
      var parts = [];
      parts.push('# ' + (title || 'Paket Belajar AyokBelajar'));
      parts.push('');

      var plainEl = document.getElementById('summary-plain');
      var summary = plainEl && String(plainEl.value).trim()
        ? plainEl.value
        : (parseJsonScript('summary-data') || '');
      if (summary) {
        parts.push('## Rangkuman');
        parts.push('');
        parts.push(String(summary));
        parts.push('');
      }

      var roadmap = parseJsonScript('roadmap-data') || [];
      if (roadmap.length) {
        parts.push('## Peta Belajar');
        parts.push('');
        roadmap.forEach(function (s) {
          parts.push((s.step || '') + '. **' + (s.title || '') + '**' + (s.detail ? ' — ' + s.detail : ''));
        });
        parts.push('');
      }

      var cards = parseJsonScript('flashcards-data') || [];
      if (cards.length) {
        parts.push('## Kartu Belajar');
        parts.push('');
        cards.forEach(function (c, i) {
          parts.push((i + 1) + '. **Q:** ' + (c.question || ''));
          parts.push('   **A:** ' + (c.answer || ''));
        });
        parts.push('');
      }

      var resources = parseJsonScript('resources-data') || {};
      if (resources.search_query || (resources.books || []).length || (resources.articles || []).length) {
        parts.push('## Sumber Belajar');
        parts.push('');
        if (resources.search_query) parts.push('Kata kunci pencarian: `' + resources.search_query + '`');
        if ((resources.books || []).length) {
          parts.push('');
          parts.push('### Buku Rekomendasi');
          resources.books.forEach(function (b) {
            parts.push('- ' + (b.title || '') + (b.note ? ' — ' + b.note : ''));
          });
        }
        if ((resources.articles || []).length) {
          parts.push('');
          parts.push('### Artikel Rekomendasi');
          resources.articles.forEach(function (a) {
            parts.push('- ' + (a.title || '') + (a.note ? ' — ' + a.note : ''));
          });
        }
        parts.push('');
      }

      var exam = parseJsonScript('exam-data') || [];
      if (exam.length) {
        parts.push('## Latihan Soal (' + exam.length + ' soal)');
        parts.push('');
        exam.forEach(function (q, i) {
          parts.push((i + 1) + '. ' + (q.question || ''));
          (q.options || []).forEach(function (opt, j) {
            parts.push('   ' + String.fromCharCode(65 + j) + '. ' + opt);
          });
          parts.push('   **Kunci:** ' + String.fromCharCode(65 + (q.correctAnswer || 0)) + ' — ' + (q.explanation || ''));
        });
        parts.push('');
      }

      downloadBlob(parts.join('\n'), filename || 'paket-belajar.md', 'text/markdown');
    },

    downloadExam: function (exam, filename, title) {
      var parts = [];
      parts.push('# ' + (title || 'Latihan Soal'));
      parts.push('');
      (exam || []).forEach(function (q, i) {
        parts.push((i + 1) + '. ' + (q.question || ''));
        (q.options || []).forEach(function (opt, j) {
          parts.push('   ' + String.fromCharCode(65 + j) + '. ' + opt);
        });
        parts.push('   **Kunci:** ' + String.fromCharCode(65 + (q.correctAnswer || 0)) + ' — ' + (q.explanation || ''));
        parts.push('');
      });
      downloadBlob(parts.join('\n'), filename || 'latihan-soal.md', 'text/markdown');
    },

    printView: function () {
      var html = document.documentElement;
      var wasDark = html.classList.contains('dark');
      if (wasDark) html.classList.remove('dark');
      window.print();
      if (wasDark) html.classList.add('dark');
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

  function syncThemeIcons() {
    var dark = document.documentElement.classList.contains('dark');
    document.querySelectorAll('.js-theme-icon-sun').forEach(function (el) {
      el.classList.toggle('hidden', !dark);
    });
    document.querySelectorAll('.js-theme-icon-moon').forEach(function (el) {
      el.classList.toggle('hidden', dark);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    syncThemeIcons();
    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
        try {
          if (!localStorage.getItem('ayok-theme') || localStorage.getItem('ayok-theme') === 'system') {
            document.documentElement.classList.toggle('dark', e.matches);
            syncThemeIcons();
          }
        } catch (err) { /* abaikan */ }
      });
    }

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

    document.querySelectorAll('#chat-box .chat-md').forEach(function (el) {
      el.innerHTML = renderMarkdown(el.textContent);
    });
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

  window.supplementLoader = function (docId) {
    return {
      state: 'idle',
      error: '',
      start: function () {
        var self = this;
        if (self.state === 'loading') return;
        self.state = 'loading';
        self.error = '';
        fetch('/workspace/' + docId + '/kit/supplement/', {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken') },
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data && data.ok) {
              window.location.reload();
            } else {
              self.state = 'error';
              self.error = (data && data.error) || 'Gagal melengkapi kartu belajar.';
            }
          })
          .catch(function () {
            self.state = 'error';
            self.error = 'Gagal terhubung. Coba lagi.';
          });
      },
    };
  };

  window.flashcardDeck = function () {
    var cards = parseJsonScript('flashcards-data') || [];
    var docId = (document.querySelector('[data-document-id]') || {}).dataset.documentId;
    var storageKey = 'ayok-flashcards-' + docId;
    var saved = {};
    try { saved = JSON.parse(localStorage.getItem(storageKey) || '{}'); } catch (e) { saved = {}; }
    var mastered = new Set((saved.mastered || []).filter(function (i) {
      return Number.isInteger(i) && i >= 0 && i < cards.length;
    }));

    function persist() {
      try {
        localStorage.setItem(storageKey, JSON.stringify({ mastered: Array.from(mastered) }));
      } catch (e) { /* localStorage tidak tersedia: status hanya untuk sesi ini */ }
    }

    return {
      cards: cards,
      index: 0,
      flipped: false,
      gridMode: false,
      mastered: mastered,
      get current() { return this.cards[this.index] || null; },
      get isCurrentMastered() { return this.mastered.has(this.index); },
      get masteredCount() { return this.mastered.size; },
      get pendingCount() { return this.cards.length - this.mastered.size; },
      get masteredPercent() {
        return this.cards.length ? Math.round((this.mastered.size / this.cards.length) * 100) : 0;
      },
      flip: function () { this.flipped = !this.flipped; },
      next: function () {
        if (this.index < this.cards.length - 1) { this.index++; this.flipped = false; }
      },
      prev: function () {
        if (this.index > 0) { this.index--; this.flipped = false; }
      },
      isMastered: function (i) { return this.mastered.has(i); },
      rate: function (ok) {
        this.rateIndex(this.index, ok);
      },
      rateIndex: function (i, ok) {
        if (i < 0 || i >= this.cards.length) return;
        if (ok) this.mastered.add(i);
        else this.mastered.delete(i);
        persist();
        this.flipped = false;
      },
      nextPending: function () {
        if (this.pendingCount === 0) return;
        for (var steps = 1; steps <= this.cards.length; steps++) {
          var i = (this.index + steps) % this.cards.length;
          if (!this.mastered.has(i)) { this.index = i; this.flipped = false; return; }
        }
      },
      reset: function () {
        if (!window.confirm('Ulangi semua kartu sebagai "Masih Belajar"? Status mahir akan dihapus.')) return;
        this.mastered.clear();
        persist();
        this.index = 0;
        this.flipped = false;
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

  window.practiceEngine = function () {
    var EXAM_MINUTES = 30;
    var EXAM_DURATION = EXAM_MINUTES * 60;
    var questions = parseJsonScript('exam-data') || [];
    var sessions = parseJsonScript('practice-sessions-data') || [];
    var docId = (document.querySelector('[data-document-id]') || {}).dataset.documentId;

    function defaultTitle() {
      var d = new Date();
      var label = d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
      return 'Latihan soal - ' + label;
    }
    function sessionFrom(s) {
      return { id: s.id, title: s.title, questions: s.questions || [], created_label: s.created_label || '' };
    }

    return {
      questions: questions,
      sessions: sessions.map(sessionFrom),
      activeSession: null,
      sessionSaved: false,
      sessionTitle: defaultTitle(),
      saveStatus: '',
      savingSession: false,
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
        fetch('/workspace/' + docId + '/practice/generate/', {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken') },
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data && data.ok && data.exam) {
              self.questions = data.exam;
              self.activeSession = null;
              self.sessionSaved = false;
              self.sessionTitle = defaultTitle();
              self.saveStatus = '';
              self.start();
            } else {
              self.error = (data && data.error) || 'Gagal generate latihan.';
            }
          })
          .catch(function () { self.error = 'Gagal terhubung. Coba lagi.'; })
          .finally(function () { self.generating = false; });
      },
      loadSession: function (s) {
        var sess = sessionFrom(s);
        this.questions = sess.questions;
        this.activeSession = sess;
        this.sessionSaved = true;
        this.sessionTitle = sess.title;
        this.saveStatus = '';
        this.answers = {};
        this.index = 0;
        this.running = false;
        this.finished = false;
        this.review = false;
        this.error = '';
        if (this._timer) clearInterval(this._timer);
        this._timer = null;
        this.remaining = EXAM_DURATION;
      },
      saveSession: function () {
        var self = this;
        if (this.savingSession) return;
        var title = (this.sessionTitle || '').trim();
        if (!title) {
          this.saveStatus = 'Beri nama sesi dulu sebelum menyimpan.';
          return;
        }
        this.savingSession = true;
        fetch('/workspace/' + docId + '/practice/save/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
          body: JSON.stringify({ title: title }),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data && data.ok && data.session) {
              var sess = sessionFrom(data.session);
              sess.questions = self.questions;
              self.sessions = [sess].concat(self.sessions.filter(function (x) { return x.id !== sess.id; }));
              self.activeSession = sess;
              self.sessionSaved = true;
              self.saveStatus = 'Tersimpan ✓';
            } else {
              self.saveStatus = (data && data.error) || 'Gagal menyimpan sesi.';
            }
          })
          .catch(function () { self.saveStatus = 'Gagal terhubung. Coba lagi.'; })
          .finally(function () { self.savingSession = false; });
      },
      deleteSession: function (s) {
        var self = this;
        if (!window.confirm('Hapus sesi "' + s.title + '"? Sesi yang dihapus tidak bisa dikembalikan.')) return;
        fetch('/workspace/' + docId + '/practice/' + s.id + '/delete/', {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken') },
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data && data.ok) {
              self.sessions = self.sessions.filter(function (x) { return x.id !== s.id; });
              if (self.activeSession && self.activeSession.id === s.id) self.activeSession = null;
            }
          })
          .catch(function () { /* diam saja; sesi tetap ada */ });
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

  window.exportPanel = function (slug) {
    return {
      open: false,
      slug: slug || 'materi',
      get hasExam() {
        return (parseJsonScript('exam-data') || []).length > 0;
      },
      exportAll: function (kind) {
        this.open = false;
        var slug = this.slug;
        if (kind === 'markdown') {
          var el = document.getElementById('summary-plain');
          var text = el && String(el.value).trim()
            ? el.value
            : (parseJsonScript('summary-data') || '');
          Ayok.downloadMarkdown(text, slug + '.md');
        } else if (kind === 'anki') {
          Ayok.downloadAnkiCSV(parseJsonScript('flashcards-data') || [], slug + '.csv');
        } else if (kind === 'kit') {
          Ayok.downloadKit(slug + '-paket.md', document.title);
        } else if (kind === 'exam') {
          Ayok.downloadExam(parseJsonScript('exam-data') || [], slug + '-latihan.md', 'Latihan Soal');
        } else if (kind === 'print') {
          Ayok.printView();
        }
      },
    };
  };

  window.themePicker = function () {
    return {
      mode: window.Ayok.theme.getMode(),
      choose: function (mode) {
        window.Ayok.theme.set(mode);
        this.mode = mode;
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

        var typing = document.createElement('div');
        typing.className = 'flex justify-start';
        typing.setAttribute('role', 'status');
        typing.setAttribute('aria-label', 'AI sedang mengetik...');
        typing.innerHTML = '<div class="flex items-center gap-1 rounded-2xl bg-white px-4 py-3 shadow-sm">' +
          '<span class="typing-dot h-2 w-2 rounded-full bg-slate-400"></span>' +
          '<span class="typing-dot h-2 w-2 rounded-full bg-slate-400" style="animation-delay:0.15s"></span>' +
          '<span class="typing-dot h-2 w-2 rounded-full bg-slate-400" style="animation-delay:0.3s"></span>' +
          '</div>';
        box.appendChild(typing);
        box.scrollTop = box.scrollHeight;

        function replaceWithBubble(content) {
          if (typing.parentNode) typing.parentNode.removeChild(typing);
          box.insertAdjacentHTML('beforeend', messageBubble('assistant', content));
          box.scrollTop = box.scrollHeight;
        }

        var docId = document.getElementById('chat-panel').dataset.documentId;
        fetch('/workspace/' + docId + '/chat/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
          body: JSON.stringify({ message: text }),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            replaceWithBubble(data.content || 'Tidak ada jawaban.');
          })
          .catch(function () {
            replaceWithBubble('Gagal terhubung. Coba lagi.');
          })
          .finally(function () { self.sending = false; });
      },
    };
  };

  function messageBubble(role, text) {
    var isUser = role === 'user';
    var bubbleClass = 'max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ' +
      (isUser ? 'bg-primary text-white whitespace-pre-wrap' : 'chat-md summary-prose bg-white text-slate-800 shadow-sm');
    var inner = isUser ? escapeHtml(text) : renderMarkdown(text);
    return '<div class="flex ' + (isUser ? 'justify-end' : 'justify-start') + '">' +
      '<div class="' + bubbleClass + '">' + inner + '</div></div>';
  }

  function renderMarkdown(text) {
    var html = marked.parse(String(text || ''));
    if (window.DOMPurify) {
      return DOMPurify.sanitize(html);
    }
    return html;
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
