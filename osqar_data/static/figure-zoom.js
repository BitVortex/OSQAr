// OSQAr figure zoom — click any diagram to open a full-viewport lightbox.
//
// Works with:
//   - PlantUML figures (sphinxcontrib-plantuml renders <object>)
//   - .gsn-figure containers (GSN diagrams, architecture diagrams)
//   - Any <figure> containing diagrams or large images
//
// <object> elements create nested browsing contexts — clicks never bubble
// to the parent document. We place transparent click layers on top.
(function() {
  'use strict';

  // ── Image source detection ──────────────────────────────────────

  function findBestSrc(el) {
    var obj = el.querySelector('object[data]');
    if (obj) return obj.getAttribute('data');
    var img = el.querySelector('img[src]');
    if (img) return img.getAttribute('src');
    var link = el.querySelector('a[href]');
    if (link) return link.getAttribute('href');
    return null;
  }

  // ── Lightbox ────────────────────────────────────────────────────

  function showLightbox(src) {
    var existing = document.getElementById('osqar-lightbox');
    if (existing) existing.remove();

    var overlay = document.createElement('div');
    overlay.id = 'osqar-lightbox';
    overlay.innerHTML =
      '<div class="osqar-lightbox-close">&times;</div>' +
      '<img src="' + src + '" alt="Full-size diagram" />';

    overlay.addEventListener('click', function(e) {
      if (e.target === overlay || e.target.classList.contains('osqar-lightbox-close')) {
        overlay.remove();
      }
    });

    function onEsc(e) {
      if (e.key === 'Escape') {
        overlay.remove();
        document.removeEventListener('keydown', onEsc);
      }
    }
    document.addEventListener('keydown', onEsc);
    document.body.appendChild(overlay);
  }

  function makeClickable(container, src) {
    container.addEventListener('click', function(e) {
      if (e.target.classList.contains('headerlink')) return;
      showLightbox(src);
      e.preventDefault();
    });
    container.style.cursor = 'pointer';
  }

  // ── Click-layer approach for <object> elements ──────────────────

  function addClickLayer(container) {
    var src = findBestSrc(container);
    if (!src) return;

    container.style.position = 'relative';
    var layer = document.createElement('div');
    layer.className = 'osqar-click-layer';
    layer.style.cssText =
      'position:absolute;top:0;left:0;width:100%;height:100%;' +
      'z-index:1;cursor:zoom-in';
    layer.title = 'Click for detailed view';
    layer.addEventListener('click', function(e) {
      showLightbox(src);
      e.stopPropagation();
      e.preventDefault();
    });
    container.appendChild(layer);
  }

  // ── Initialization ─────────────────────────────────────────────

  function init() {
    // 1. .gsn-figure containers — explicit opt-in wrapping
    document.querySelectorAll('.gsn-figure').forEach(function(ctr) {
      if (ctr.querySelector('object[data]')) {
        addClickLayer(ctr);
      } else {
        var src = findBestSrc(ctr);
        if (src) {
          var img = ctr.querySelector('img');
          if (img) {
            img.style.cursor = 'zoom-in';
            img.title = 'Click for detailed view';
          }
          makeClickable(ctr, src);
        }
      }
    });

    // 2. All PlantUML diagrams — works for architecture diagrams
    //    anywhere on the page without manual .gsn-figure wrapping.
    document.querySelectorAll('p.plantuml').forEach(function(ctr) {
      // Skip if already inside a .gsn-figure (handled above)
      if (ctr.closest('.gsn-figure')) return;
      if (ctr.querySelector('object[data]')) {
        addClickLayer(ctr);
      }
    });

    // 3. Any <figure> with images that isn't already covered
    document.querySelectorAll('figure').forEach(function(ctr) {
      if (ctr.closest('.gsn-figure')) return;
      if (ctr.querySelector('.osqar-click-layer')) return;
      var src = findBestSrc(ctr);
      if (!src) return;
      var img = ctr.querySelector('img');
      if (img) {
        img.style.cursor = 'zoom-in';
        img.title = 'Click for detailed view';
      }
      makeClickable(ctr, src);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
