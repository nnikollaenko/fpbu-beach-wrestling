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
            this.updateLangSwitcher(location.pathname + location.search);
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
            let lastPath = location.pathname + location.search;
            window.addEventListener('popstate', () => {
                const newPath = location.pathname + location.search;
                if (newPath === lastPath) return; // only hash changed
                lastPath = newPath;
                this.navigate(newPath, false);
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
            this.updateLangSwitcher(path);

            window.dispatchEvent(new CustomEvent('navigationComplete', { detail: { path } }));
        }

        updateActiveNav(path) {
            const cleanPath = path.replace(/^\/en(\/|$)/, '/');
            document.querySelectorAll('[data-nav-page]').forEach(el => {
                const pages = el.dataset.navPage.split(',').map(p => p.trim());
                const match = pages.some(page =>
                    cleanPath === '/' ? page === '' : cleanPath.startsWith('/' + page)
                );
                el.classList.toggle('active', match);
            });
        }

        updateLangSwitcher(path) {
            const isEn = path === '/en' || path.startsWith('/en/');
            const suffix = isEn ? (path.slice(3) || '/') : path;
            const urls = { uk: suffix || '/', en: '/en' + (suffix || '/') };
            document.querySelectorAll('[data-lang]').forEach(a => {
                a.href = urls[a.dataset.lang];
            });
        }
    }

    // Mobile menu
    function initMobileMenu() {
        const btn = document.getElementById('mobMenuBtn');
        const nav = document.getElementById('mobNav');
        if (!btn || !nav) return;

        let closeTimer = null;

        // iOS-safe body scroll lock: position:fixed is the only reliable
        // way to prevent rubber-band scrolling on Safari.
        function lockScroll() {
            const y = window.scrollY;
            document.body.dataset.scrollY = y;
            document.body.style.position = 'fixed';
            document.body.style.top = `-${y}px`;
            document.body.style.left = '0';
            document.body.style.right = '0';
        }

        function unlockScroll() {
            const y = parseInt(document.body.dataset.scrollY || '0', 10);
            document.body.style.position = '';
            document.body.style.top = '';
            document.body.style.left = '';
            document.body.style.right = '';
            window.scrollTo(0, y);
        }

        function openMenu() {
            clearTimeout(closeTimer);
            nav.classList.remove('is-closing');
            nav.classList.add('open');
            btn.classList.add('is-open');
            btn.setAttribute('aria-expanded', 'true');
            lockScroll();
        }

        function closeMenu() {
            if (!nav.classList.contains('open')) return;
            nav.classList.add('is-closing');
            btn.classList.remove('is-open');
            btn.setAttribute('aria-expanded', 'false');
            unlockScroll();
            closeTimer = setTimeout(() => {
                nav.classList.remove('open');
                nav.classList.remove('is-closing');
            }, 240);
        }

        btn.addEventListener('click', () => {
            if (nav.classList.contains('open')) closeMenu();
            else openMenu();
        });

        // Close on nav-link click
        nav.querySelectorAll('a').forEach(a => {
            a.addEventListener('click', closeMenu);
        });

        // Accordion
        const accs = nav.querySelectorAll('.mob-acc');
        accs.forEach(acc => {
            const trigger = acc.querySelector('.mob-acc-btn');
            trigger.addEventListener('click', () => {
                const isOpen = acc.classList.contains('open');
                accs.forEach(a => {
                    a.classList.remove('open');
                    a.querySelector('.mob-acc-btn').setAttribute('aria-expanded', 'false');
                });
                if (!isOpen) {
                    acc.classList.add('open');
                    trigger.setAttribute('aria-expanded', 'true');
                }
            });
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

    // Smart header: hide on scroll-down, reveal on scroll-up (mobile/tablet only)
    function initSmartHeader() {
        const hdr = document.querySelector('.site-header');
        if (!hdr) return;

        let lastY = window.scrollY;
        let ticking = false;
        const THRESHOLD = 80; // px from top before hiding kicks in

        function update() {
            const y = window.scrollY;
            const isMobile = window.innerWidth <= 960;
            const menuOpen = document.getElementById('mobNav')?.classList.contains('open');

            if (!isMobile || menuOpen) {
                hdr.classList.remove('hdr-hidden');
                lastY = y;
                ticking = false;
                return;
            }

            if (y < THRESHOLD) {
                hdr.classList.remove('hdr-hidden');
            } else if (y > lastY + 4) {
                hdr.classList.add('hdr-hidden');
            } else if (y < lastY - 4) {
                hdr.classList.remove('hdr-hidden');
            }

            lastY = y;
            ticking = false;
        }

        window.addEventListener('scroll', () => {
            if (!ticking) {
                requestAnimationFrame(update);
                ticking = true;
            }
        }, { passive: true });

        // Always show header after navigation
        window.addEventListener('navigationComplete', () => {
            lastY = 0;
            hdr.classList.remove('hdr-hidden');
        });
    }

    // Dropdown: delay close so mouse can travel from trigger to menu
    function initDropdowns() {
        const dropdowns = document.querySelectorAll('.hdr-dropdown');
        dropdowns.forEach(el => {
            let timer = null;
            const open = () => {
                clearTimeout(timer);
                dropdowns.forEach(other => { if (other !== el) other.classList.remove('open'); });
                el.classList.add('open');
            };
            const close = () => { timer = setTimeout(() => el.classList.remove('open'), 120); };
            el.addEventListener('mouseenter', open);
            el.addEventListener('mouseleave', close);
        });

        window.addEventListener('navigationComplete', () => {
            dropdowns.forEach(d => d.classList.remove('open'));
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        window._navManager = new NavigationManager();
        initMobileMenu();
        initHeaderScroll();
        initSmartHeader();
        initDropdowns();
    });

})();
