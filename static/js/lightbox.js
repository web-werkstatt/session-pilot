/**
 * Lightbox — globale Bild-Vergroesserung.
 * Vorher Teil von base.js, ausgelagert Phase 7 (2026-04-14) wegen Dateigroessen-Limit.
 */
var lbImages = [];
var lbIndex = 0;

function getLightbox() {
    return document.getElementById('lightbox');
}


function collectLightboxImages(clickedSrc) {
    var imgs = document.querySelectorAll('img:not(.lightbox img):not(.sidebar img):not([src*="favicon"])');
    lbImages = [];
    var foundIdx = 0;
    imgs.forEach(function(img) {
        var src = img.src || img.dataset.src;
        if (!src || img.offsetParent === null) return;
        if (img.naturalWidth < 20 && img.naturalWidth > 0) return;
        lbImages.push({src: src, alt: img.alt || ''});
        if (src === clickedSrc) foundIdx = lbImages.length - 1;
    });
    if (lbImages.length === 0 || !lbImages.some(function(i) { return i.src === clickedSrc; })) {
        var galleryItems = document.querySelectorAll('.doc-gallery-item');
        if (galleryItems.length > 0) {
            lbImages = [];
            galleryItems.forEach(function(item) {
                var img = item.querySelector('img');
                var label = item.querySelector('.gallery-label');
                if (img) lbImages.push({src: img.src, alt: label ? label.textContent : ''});
            });
            lbImages.forEach(function(i, idx) { if (i.src === clickedSrc) foundIdx = idx; });
        }
    }
    return foundIdx;
}

function openLightbox(src) {
    var lightbox = getLightbox();
    if (!lightbox) return;
    lbIndex = collectLightboxImages(src);
    showLightboxImage();
    lightbox.classList.add('show');
}

function showLightboxImage() {
    if (lbImages.length === 0) return;
    var lightboxImg = document.getElementById('lightboxImg');
    var info = document.getElementById('lbInfo');
    var counter = document.getElementById('lbCounter');
    if (!lightboxImg || !info || !counter) return;
    var item = lbImages[lbIndex];
    lightboxImg.src = item.src;
    info.textContent = item.alt || '';
    if (lbImages.length > 1) {
        counter.textContent = (lbIndex + 1) + ' / ' + lbImages.length;
        document.getElementById('lbPrev').style.display = lbIndex > 0 ? '' : 'none';
        document.getElementById('lbNext').style.display = lbIndex < lbImages.length - 1 ? '' : 'none';
        counter.style.display = '';
    } else {
        document.getElementById('lbPrev').style.display = 'none';
        document.getElementById('lbNext').style.display = 'none';
        counter.style.display = 'none';
    }
}

function lightboxNav(dir) {
    lbIndex = Math.max(0, Math.min(lbImages.length - 1, lbIndex + dir));
    showLightboxImage();
}

function closeLightbox() {
    var lightbox = getLightbox();
    var lightboxImg = document.getElementById('lightboxImg');
    if (!lightbox || !lightboxImg) return;
    lightbox.classList.remove('show');
    lightboxImg.src = '';
}

document.addEventListener('click', function(e) {
    if (!getLightbox()) return;
    if (e.target.tagName === 'IMG' && !e.target.closest('.lightbox') && !e.target.closest('.sidebar')) {
        e.preventDefault(); e.stopPropagation(); openLightbox(e.target.src);
    }
}, true);

document.addEventListener('keydown', function(e) {
    var lightbox = getLightbox();
    if (!lightbox || !lightbox.classList.contains('show')) return;
    if (e.key === 'ArrowLeft') { lightboxNav(-1); e.preventDefault(); }
    else if (e.key === 'ArrowRight') { lightboxNav(1); e.preventDefault(); }
});
