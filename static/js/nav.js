/**
 * SPA-like navigation with AJAX page loading and smooth transitions.
 * Intercepts nav-link clicks, fetches #main-content, swaps it in.
 */
(function () {
    'use strict';

    class NavigationManager {
        constructor() {
            this.main = document.getElementById('main-content');
            this.cache = new Map();
            this.cacheTTL = 5 * 60 * 1000;
            this.busy = false;
            this.controller = null;
            this.init();
        }

        init() {
            this.bindLinks();
            this.bindPopState();
            this.updateActiveNav(location.pathname);
            this.main?.classList.add('content-entering');
        }

        bindLinks() {
            document.addEventListener('click', (e) => {
                const link = e.target.closest('a');
                if (!link) return;
                if (!link.classList.contains('nav-link')) return;
                if (link.target === '_blank') return;
                const href = link.getAttribute('href');
                if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:')) return;
                const url = new URL(href, location.origin);
                if (url.origin !== location.origin) return;
                e.preventDefault();
                this.navigate(url.pathname + url.search);
            });
        }

        bindPopState() {
            window.addEventListener('popstate', () => {
                this.navigate(location.pathname + location.search, false);
            });
        }

        async navigate(path, pushState = true) {
            if (this.busy) {
                if (this.controller) this.controller.abort();
            }
            if (pushState && location.pathname + location.search === path) return;

            this.busy = true;
            this.controller = new AbortController();

            const cached = this.cache.get(path);
            if (cached && Date.now() - cached.ts < this.cacheTTL) {
                this.swap(cached, path, pushState);
                this.busy = false;
                return;
            }

            try {
                const res = await fetch(path, {
                    signal: this.controller.signal,
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                });
                if (!res.ok) { location.href = path; return; }
                const html = await res.text();
                const doc = new DOMParser().parseFromString(html, 'text/html');
                const content = doc.getElementById('main-content')?.innerHTML;
                const title = doc.title;
                if (!content) { location.href = path; return; }
                const data = { content, title, ts: Date.now() };
                this.cache.set(path, data);
                if (this.cache.size > 15) {
                    this.cache.delete(this.cache.keys().next().value);
                }
                this.swap(data, path, pushState);
            } catch (err) {
                if (err.name !== 'AbortError') location.href = path;
            } finally {
                this.busy = false;
            }
        }

        swap(data, path, pushState) {
            if (pushState) history.pushState(null, '', path);
            document.title = data.title;

            // Dispatch cleanup event so page scripts can self-teardown
            window.dispatchEvent(new CustomEvent('pageCleanup', { detail: { path } }));

            this.main.innerHTML = data.content;

            // Re-execute inline scripts in new content
            this.main.querySelectorAll('script').forEach(old => {
                const s = document.createElement('script');
                [...old.attributes].forEach(a => s.setAttribute(a.name, a.value));
                s.textContent = old.textContent;
                old.replaceWith(s);
            });

            window.scrollTo({ top: 0, behavior: 'instant' });
            this.main.classList.remove('content-entering');
            void this.main.offsetWidth; // reflow
            this.main.classList.add('content-entering');
            this.updateActiveNav(path);

            window.dispatchEvent(new CustomEvent('navigationComplete', { detail: { path } }));
        }

        updateActiveNav(path) {
            document.querySelectorAll('[data-nav-page]').forEach(el => {
                const page = el.dataset.navPage;
                const match = path === '/' ? page === '' : path.startsWith('/' + page);
                el.classList.toggle('active', match);
            });
        }
    }

    // Mobile menu
    function initMobileMenu() {
        const btn = document.getElementById('mobMenuBtn');
        const close = document.getElementById('mobMenuClose');
        const nav = document.getElementById('mobNav');
        if (!btn || !nav) return;

        function open() {
            nav.classList.add('open');
            document.body.style.overflow = 'hidden';
        }

        function closeMenu() {
            nav.classList.remove('open');
            document.body.style.overflow = '';
        }

        btn.addEventListener('click', open);
        close?.addEventListener('click', closeMenu);

        // Close on nav-link click
        nav.querySelectorAll('a').forEach(a => {
            a.addEventListener('click', closeMenu);
        });
    }

    // Header scroll shadow
    function initHeaderScroll() {
        const hdr = document.querySelector('.site-header');
        if (!hdr) return;
        const obs = new IntersectionObserver(
            ([e]) => hdr.classList.toggle('scrolled', e.intersectionRatio < 1),
            { threshold: [1], rootMargin: '-1px 0px 0px 0px' }
        );
        const sentinel = document.createElement('div');
        sentinel.style.cssText = 'height:1px;width:100%;position:absolute;top:0;pointer-events:none;';
        document.body.prepend(sentinel);
        obs.observe(sentinel);
    }

    document.addEventListener('DOMContentLoaded', () => {
        window._navManager = new NavigationManager();
        initMobileMenu();
        initHeaderScroll();
    });

})();
