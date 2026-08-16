(function (global) {
  'use strict';

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function bind(options) {
    options = options || {};
    var itemSelector = options.items || '[data-nika-lightbox]';
    var box = typeof options.box === 'string' ? qs(options.box) : (options.box || qs('.nika-lightbox'));
    if (!box) return null;
    var img = box.querySelector('[data-nika-lightbox-img]');
    var cap = box.querySelector('[data-nika-lightbox-caption]');
    var closeBtn = box.querySelector('[data-nika-lightbox-close]');
    var prevBtn = box.querySelector('[data-nika-lightbox-prev]');
    var nextBtn = box.querySelector('[data-nika-lightbox-next]');
    var items = Array.prototype.slice.call(document.querySelectorAll(itemSelector));
    var idx = 0;
    if (!img || !items.length) return null;

    function openAt(n) {
      idx = (n + items.length) % items.length;
      var el = items[idx];
      var src = el.getAttribute('data-full') || el.getAttribute('href') || '';
      var caption = el.getAttribute('data-caption') || '';
      img.src = src;
      img.alt = caption;
      if (cap) cap.textContent = caption;
      box.hidden = false;
      document.body.style.overflow = 'hidden';
    }

    function close() {
      box.hidden = true;
      img.removeAttribute('src');
      document.body.style.overflow = '';
    }

    items.forEach(function (el, n) {
      el.addEventListener('click', function (e) {
        if (el.tagName === 'A') e.preventDefault();
        openAt(n);
      });
    });
    if (closeBtn) closeBtn.addEventListener('click', close);
    if (prevBtn) prevBtn.addEventListener('click', function () { openAt(idx - 1); });
    if (nextBtn) nextBtn.addEventListener('click', function () { openAt(idx + 1); });
    box.addEventListener('click', function (e) {
      if (e.target === box) close();
    });
    document.addEventListener('keydown', function (e) {
      if (box.hidden) return;
      if (e.key === 'Escape') close();
      if (e.key === 'ArrowLeft') openAt(idx - 1);
      if (e.key === 'ArrowRight') openAt(idx + 1);
    });
    return { openAt: openAt, close: close };
  }

  global.NikaLightbox = { bind: bind };
})(window);
