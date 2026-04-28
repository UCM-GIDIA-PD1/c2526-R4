let currentGame = null;
let currentPrediction = null;
let charts = {};

// ============================================================
// NAVIGATION
// ============================================================
function showView(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
    const appContainer = document.querySelector('.app-container');
    if (appContainer) {
        appContainer.scrollIntoView({ behavior: 'smooth' });
    }
}

function setupNavigation() {
    document.getElementById('btn-back-home').addEventListener('click', () => {
        showView('view-home');
        checkAndRestoreBg();
    });
    document.getElementById('btn-back-game').addEventListener('click', () => {
        showView('view-game');
    });
}

// ============================================================
// SEARCH & TRENDING STATE
// ============================================================
let currentPage = 1;
let currentQuery = '';
let isLoading = false;
let hasMore = true;
let currentSort = 'desc';
let currentGenre = 'all';
let currentMinPrice = 0;
let currentMaxPrice = -1;
let lastFeaturedAppId = null;

// ============================================================
// SEARCH (same fetch() pattern as flower3.html)
// ============================================================
function setupSearch() {
    const input = document.getElementById('search-input');
    let debounceTimer = null;

    input.addEventListener('input', () => {
        const q = input.value.trim();
        clearTimeout(debounceTimer);

        debounceTimer = setTimeout(() => {
            currentQuery = q;
            currentPage = 1;
            hasMore = true;
            fetchGames(true);
        }, 300);

        // Keep icon hidden while there's text
        const icon = input.closest('.search-wrapper').querySelector('.search-icon');
        if (q) icon.classList.add('icon-hidden');
        else icon.classList.add('icon-hidden'); // still focused, keep hidden
    });

    // Glow animation + icon toggle on focus / blur
    const wrapper = input.closest('.search-wrapper');
    const icon = wrapper.querySelector('.search-icon');
    input.addEventListener('focus', () => {
        wrapper.classList.remove('glow-out');
        wrapper.classList.add('glow-in');
        icon.classList.add('icon-hidden');
    });
    input.addEventListener('blur', () => {
        wrapper.classList.remove('glow-in');
        wrapper.classList.add('glow-out');
        if (!input.value.trim()) {
            icon.classList.remove('icon-hidden');
        }
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && lastFeaturedAppId) {
            navigateToGame(lastFeaturedAppId);
            input.blur();
        }
    });

    setupInfiniteScroll();

    // Sort Toggle
        // Top sort button removed. Logic moved to sidebar click.

    // Initialize Filters
    initFilters(wrapper, input);

    // Setup hover background crossfade layers (global for reuse)
    const grid = document.getElementById('game-grid');
    window._hoverBg = {
        layers: [
            document.getElementById('hover-bg-a'),
            document.getElementById('hover-bg-b'),
        ],
        activeLayer: 0,
        currentSrc: null,
        hideTimer: null,
    };

    // Click delegation
    grid.addEventListener('click', (e) => {
        const card = e.target.closest('.game-card');
        if (card) {
            navigateToGame(parseInt(card.dataset.appid));
        }
    });

    // Hover delegation
    grid.addEventListener('mouseover', (e) => {
        const card = e.target.closest('.game-card');
        if (!card) return;
        if (window._hoverBg.hideTimer) { clearTimeout(window._hoverBg.hideTimer); window._hoverBg.hideTimer = null; }
        const img = card.querySelector('.game-card-banner');
        if (img && img.src) showHoverBg(img.src);
    });

    grid.addEventListener('mouseout', (e) => {
        const related = e.relatedTarget;

        if (!related || !related.closest('.game-card')) {
            // Check if there is an active exact match that should persist
            let keepBg = false;
            if (grid.classList.contains('single-result')) {
                keepBg = true;
            } else if (currentQuery) {
                const queryLower = currentQuery.toLowerCase().trim();
                const exactCard = Array.from(grid.querySelectorAll('.game-card')).find(c => c.dataset.name.toLowerCase() === queryLower);
                if (exactCard) {
                    keepBg = true;
                    const img = exactCard.querySelector('.game-card-banner');
                    if (img && img.src) showHoverBg(img.src);
                }
            }

            if (!keepBg) {
                window._hoverBg.hideTimer = setTimeout(() => hideHoverBg(), 150);
            }
        }
    });
}

/**
 * Initialize Genre and Price filters
 */
async function initFilters(wrapper, input) {
    const genreDropdown = document.getElementById('genre-dropdown');
    const priceDropdown = document.getElementById('price-dropdown');

    // Helper to toggle dropdowns
    const toggleDropdown = (dropdown) => {
        const isVisible = dropdown.classList.contains('visible');
        document.querySelectorAll('.filter-dropdown').forEach(d => d.classList.remove('visible'));
        if (!isVisible) dropdown.classList.add('visible');
    };

    // Helper to trigger glow
    const triggerSearchGlow = () => {
        wrapper.classList.remove('glow-in', 'glow-out');
        void wrapper.offsetWidth;
        wrapper.classList.add('glow-in');
        
        if (window._glowTimeout) clearTimeout(window._glowTimeout);
        window._glowTimeout = setTimeout(() => {
            if (document.activeElement !== input) {
                wrapper.classList.remove('glow-in');
                wrapper.classList.add('glow-out');
            }
        }, 400);
    };

    // Top buttons removed.

    // Close on click outside
    document.addEventListener('click', () => {
        document.querySelectorAll('.filter-dropdown').forEach(d => d.classList.remove('visible'));
    });

    // Sidebar Bindings
    const sideSort = document.getElementById('side-btn-sort');
    const sideGenre = document.getElementById('side-btn-genre');
    const sidePrice = document.getElementById('side-btn-price');

    if (sideSort) {
        sideSort.addEventListener('click', (e) => {
            e.stopPropagation();
            currentSort = (currentSort === 'desc') ? 'asc' : 'desc';
            updateSidebarSortIcon();
            currentPage = 1;
            hasMore = true;
            fetchGames(true);
            triggerSearchGlow();
            triggerSidebarAnimation(sideSort);
        });
    }

    if (sideGenre) {
        sideGenre.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleDropdown(genreDropdown);
            triggerSidebarAnimation(sideGenre, 'anim-genre');
        });
    }

    if (sidePrice) {
        sidePrice.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleDropdown(priceDropdown);
            triggerSidebarAnimation(sidePrice, 'anim-price');
        });
    }

    function triggerSidebarAnimation(item, animClass) {
        // Underline animation
        item.classList.remove('anim-active');
        void item.offsetWidth;
        item.classList.add('anim-active');
        setTimeout(() => item.classList.remove('anim-active'), 850);

        // Icon animation
        if (animClass) {
            const icon = item.querySelector('.sidebar-icon');
            if (!icon) return;
            icon.classList.remove(animClass);
            void icon.offsetWidth;
            icon.classList.add(animClass);
            setTimeout(() => icon.classList.remove(animClass), 700);
        }
    }

    // Fetch and populate options
    try {
        const res = await fetch('/api/filter-options');
        const options = await res.json();

        // Genres
        genreDropdown.innerHTML = `<div class="filter-option active" data-val="all">Todos los géneros</div>`;
        options.genres.forEach(g => {
            genreDropdown.innerHTML += `<div class="filter-option" data-val="${g}">${g}</div>`;
        });

        // Prices
        priceDropdown.innerHTML = '';
        options.prices.forEach(p => {
            const activeClass = (p.min === 0 && p.max === -1) ? 'active' : '';
            priceDropdown.innerHTML += `<div class="filter-option ${activeClass}" data-min="${p.min}" data-max="${p.max}">${p.label}</div>`;
        });

        // Event delegation for options
        [genreDropdown, priceDropdown].forEach(dropdown => {
            dropdown.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevents parent sidebar item from toggling the menu back
                const opt = e.target.closest('.filter-option');
                if (!opt) return;

                if (dropdown === genreDropdown) {
                    currentGenre = opt.dataset.val;
                    sideGenre.title = currentGenre === 'all' ? 'Filtrar por género' : `Géneros: ${currentGenre}`;
                } else {
                    currentMinPrice = parseFloat(opt.dataset.min);
                    currentMaxPrice = parseFloat(opt.dataset.max);
                    const label = opt.textContent;
                    sidePrice.title = (currentMinPrice === 0 && currentMaxPrice === -1) ? 'Filtrar por precio' : `Precio: ${label}`;
                }

                dropdown.querySelectorAll('.filter-option').forEach(o => o.classList.remove('active'));
                opt.classList.add('active');

                triggerSearchGlow();
                currentPage = 1;
                fetchGames(true);
            });
        });

    } catch (err) {
        console.error("Error loading filter options:", err);
    }
}

function checkAndRestoreBg() {
    const grid = document.getElementById('game-grid');
    let keepBg = false;
    if (grid.classList.contains('single-result')) {
        keepBg = true;
    } else if (currentQuery) {
        const queryLower = currentQuery.toLowerCase().trim();
        const exactCard = Array.from(grid.querySelectorAll('.game-card')).find(c => c.dataset.name.toLowerCase() === queryLower);
        if (exactCard) {
            keepBg = true;
            const img = exactCard.querySelector('.game-card-banner');
            if (img && img.src) showHoverBg(img.src);
        }
    }

    if (!keepBg) {
        window._hoverBg.hideTimer = setTimeout(() => hideHoverBg(), 150);
    }
}

function showHoverBg(src) {
    const hb = window._hoverBg;
    if (!hb || src === hb.currentSrc) return;
    hb.currentSrc = src;
    const oldLayer = hb.layers[hb.activeLayer];
    hb.activeLayer = 1 - hb.activeLayer;
    const newLayer = hb.layers[hb.activeLayer];
    newLayer.style.backgroundImage = `url('${src}')`;
    newLayer.classList.add('active');
    oldLayer.classList.remove('active');
}

function hideHoverBg() {
    // Si estamos en la vista de juego, no ocultamos el fondo
    const viewGame = document.getElementById('view-game');
    if (viewGame && viewGame.classList.contains('active')) return;

    const hb = window._hoverBg;
    if (!hb) return;
    hb.currentSrc = null;
    hb.layers[0].classList.remove('active');
    hb.layers[1].classList.remove('active');
}

function setupInfiniteScroll() {
    const sentinel = document.getElementById('scroll-sentinel');
    if (!sentinel) return;

    const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && !isLoading && hasMore) {
            currentPage++;
            fetchGames(false);
        }
    }, { rootMargin: '100px' });

    observer.observe(sentinel);
}

// ============================================================
// FETCH & RENDER GAME GRID
// ============================================================
async function fetchGames(reset = false) {
    if (isLoading) return;
    isLoading = true;

    const sentinel = document.getElementById('scroll-sentinel');
    const grid = document.getElementById('game-grid');

    if (reset) {
        grid.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
        if (sentinel) sentinel.style.display = 'none';
        // Removed window.scrollTo to prevent jumping to top while typing
    } else if (sentinel && hasMore) {
        sentinel.style.display = 'flex';
    }

    const url = `/api/search?q=${encodeURIComponent(currentQuery)}&page=${currentPage}&limit=40&sort=${currentSort}&genre=${currentGenre}&min_price=${currentMinPrice}&max_price=${currentMaxPrice}`;

    try {
        const res = await fetch(url);
        const data = await res.json();
        hasMore = data.has_more;
        renderGameGrid(data.games, reset);
    } catch (e) {
        console.error(e);
        if (reset) grid.innerHTML = '<div class="search-no-results">Error al cargar resultados</div>';
    } finally {
        isLoading = false;
        if (sentinel) {
            sentinel.style.display = hasMore ? 'flex' : 'none';
        }
    }
}

function renderGameGrid(games, reset) {
    const grid = document.getElementById('game-grid');

    if (reset) {
        if (!games.length) {
            grid.innerHTML = '<div class="search-no-results">Sin resultados</div>';
            hideHoverBg();
            return;
        }
        grid.innerHTML = '';
    }

    if (!games.length && !reset) return;

    const html = games.map(g => `
        <div class="game-card" data-appid="${g.appid}" data-name="${g.name}">
            <img class="game-card-banner" src="${g.banner_url}" alt="${g.name}" loading="lazy">
            <div class="game-card-name">${g.name}</div>
        </div>
    `).join('');

    grid.insertAdjacentHTML('beforeend', html);

    // If exactly one result after a search reset, show its background and enlarge
    if (reset && games.length === 1 && !hasMore && games[0].banner_url) {
        showHoverBg(games[0].banner_url);
        grid.classList.add('single-result');
        const card = grid.querySelector('.game-card');
        if (card) card.classList.add('game-card-featured');
        lastFeaturedAppId = games[0].appid;
    } else if (reset) {
        grid.classList.remove('single-result');
        // CAMBIO DEL CÓDIGO ORIGINAL: lastFeaturedAppId = null;
        let foundExactMatch = false;
        if (currentQuery) {
            const queryLower = currentQuery.toLowerCase().trim();
            const exactMatch = games.find(g => g.name.toLowerCase() === queryLower);
            if (exactMatch && exactMatch.banner_url) {
                showHoverBg(exactMatch.banner_url);
                foundExactMatch = true;
                lastFeaturedAppId = exactMatch.appid;
            }
        }

        if (!foundExactMatch) {
            hideHoverBg();
        }
    }
}

// ============================================================
// TRENDING GAMES
// ============================================================
function loadTrendingGames() {
    currentQuery = '';
    currentPage = 1;
    hasMore = true;
    currentSort = 'desc';
    currentGenre = 'all';
    currentMinPrice = 0;
    currentMaxPrice = -1;
    lastFeaturedAppId = null;
    fetchGames(true);
}

// ============================================================
// GAME DETAIL VIEW
// ============================================================
async function navigateToGame(appid) {
    showView('view-game');

    const container = document.getElementById('game-detail-content');
    container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    // Fetch game info
    const res = await fetch(`/api/game/${appid}`);
    const game = await res.json();
    currentGame = game;

    showHoverBg(game.banner_url);

    const positive = game.positive_reviews || 0;
    const negative = game.negative_reviews || 0;
    const totalReviews = positive + negative;

    // 1. Parseo limpio del array de géneros
    let parsedGenres = [];
    try {
        let rawGenres = [];
        if (typeof game.genres === 'string') {
            rawGenres = game.genres.split(',');
        } else if (Array.isArray(game.genres)) {
            rawGenres = game.genres;
        }
        
        parsedGenres = rawGenres
            .map(g => g.replace(/[\[\]'"]/g, '').trim())
            .filter(Boolean);
    } catch (e) { }
    if (!parsedGenres.length) parsedGenres = ['Unknown'];

    const safeGenres = parsedGenres.map(g => `<span class="glow-chip">${g}</span>`).join('');

    // 2. Inyección del nuevo HTML en el contenedor
    container.innerHTML = `
        <div class="game-hero-section vision-glass">
            <div class="hero-left">
                <img class="hero-banner console-transition" src="${game.banner_url}" alt="${game.name}">
            </div>
            <div class="hero-right">
                <h1 class="hero-name">${game.name}</h1>
                <p class="hero-desc">${game.short_description || 'Explora esta increíble experiencia que te mantendrá al borde de tu asiento.'}</p>
                <div class="hero-genres">
                    ${safeGenres}
                </div>
            </div>
        </div>

        <div class="game-meta-grid">
            <div class="vision-glass meta-card">
                <div class="meta-label">Desarrollador</div>
                <div class="meta-value">${game.developer || 'Unknown Studio'}</div>
            </div>
            <div class="vision-glass meta-card">
                <div class="meta-label">Fecha de Lanzamiento</div>
                <div class="meta-value">${game.release_date || 'N/A'}</div>
            </div>
            <div class="vision-glass meta-card">
                <div class="meta-label">Precio Actual</div>
                <div class="meta-value">${game.price_overview === 0 || game.price_overview === '0' ? 'Gratis' : (game.price_overview || 'Unknown')}</div>
            </div>
            <div class="vision-glass meta-card">
                <div class="meta-label">Reseñas en lanzamiento</div>
                <div class="meta-value">${formatNumber(game.total_reviews_at_launch) || '0'}</div>
            </div>
        </div>

        <div class="predictions-grid">
            <div class="predictions-row-top">
                <div class="vision-glass pred-card">
                    <h3 class="pred-title">Predicción de Popularidad</h3>
                    <div class="pred-value">${formatNumber(Math.floor(Math.random() * 50000) + 10000)} Jugadores</div>
                    <div class="confidence-wrapper">
                        <span class="conf-label">Confianza: 92%</span>
                        <div class="conf-bar"><div class="conf-fill" style="width: 92%;"></div></div>
                    </div>
                </div>
                <div class="vision-glass pred-card">
                    <h3 class="pred-title">Estimación de Precio</h3>
                    <div class="pred-value" id="pred-price-value">Cargando...</div>
                    <div class="market-label">Basado en IA</div>
                </div>
            </div>
            
            <div class="vision-glass nlp-card">
                <h3 class="pred-title">RESUMEN DE RESEÑAS</h3>
                <div class="nlp-themes-list">
                    <div class="nlp-theme-row">
                        <div class="nlp-theme-text">
                            <span class="nlp-theme-name">GRÁFICOS:</span>
                            <span class="nlp-theme-keywords">Impresionante, Visuales, Estética</span>
                        </div>
                        <div class="nlp-mini-gauge excellent">
                            <svg viewBox="0 0 100 50" class="gauge-svg"><path class="gauge-bg" d="M 10 50 A 40 40 0 0 1 90 50" /><path class="gauge-fill" d="M 10 50 A 40 40 0 0 1 90 50" style="stroke-dashoffset: 25.12;" /></svg>
                            <span class="gauge-score">80</span>
                        </div>
                    </div>
                    
                    <div class="nlp-theme-row">
                        <div class="nlp-theme-text">
                            <span class="nlp-theme-name">HISTORIA:</span>
                            <span class="nlp-theme-keywords">Narrativa, Personajes, Final</span>
                        </div>
                        <div class="nlp-mini-gauge excellent">
                            <svg viewBox="0 0 100 50" class="gauge-svg"><path class="gauge-bg" d="M 10 50 A 40 40 0 0 1 90 50" /><path class="gauge-fill" d="M 10 50 A 40 40 0 0 1 90 50" style="stroke-dashoffset: 6.28;" /></svg>
                            <span class="gauge-score">95</span>
                        </div>
                    </div>

                    <div class="nlp-theme-row">
                        <div class="nlp-theme-text">
                            <span class="nlp-theme-name">RENDIMIENTO:</span>
                            <span class="nlp-theme-keywords">FPS, Optimización, Stuttering</span>
                        </div>
                        <div class="nlp-mini-gauge negative">
                            <svg viewBox="0 0 100 50" class="gauge-svg"><path class="gauge-bg" d="M 10 50 A 40 40 0 0 1 90 50" /><path class="gauge-fill" d="M 10 50 A 40 40 0 0 1 90 50" style="stroke-dashoffset: 87.92;" /></svg>
                            <span class="gauge-score">30</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Cargar predicción real de precio
    loadRealPricePrediction(game.appid);
}

async function loadRealPricePrediction(appid) {
    const priceValue = document.getElementById('pred-price-value');
    if (!priceValue) return;
    
    try {
        const res = await fetch(`/api/predict/precio`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ appid: appid }),
        });
        const data = await res.json();
        priceValue.textContent = data.price;
    } catch (e) {
        priceValue.textContent = 'Error';
    }
}

async function requestPrediction(type, appid) {
    const resultsArea = document.getElementById('prediction-results-area');
    resultsArea.style.display = 'block';
    resultsArea.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    resultsArea.scrollIntoView({ behavior: 'smooth' });

    const res = await fetch(`/api/predict/${type}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ appid: appid }),
    });
    const prediction = await res.json();
    currentPrediction = prediction;

    showPredictionView(type, prediction);
}

function showPredictionView(type, prediction) {
    document.getElementById('prediction-detail-content').innerHTML = `
        <div class="loading"><div class="spinner"></div></div>
    `;
    showView('view-prediction');
    renderPredictionDetail(type, prediction);
}

async function loadPrediction(type, appid) {
    const card = document.getElementById(`card-${type}`);

    const res = await fetch(`/api/predict/${type}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ appid: appid }),
    });
    const prediction = await res.json();

    renderPredictionCard(card, type, prediction);
}

function renderPredictionCard(card, type, prediction) {
    const config = {
        popularidad: {
            title: 'Popularidad',
            formatValue: (v) => formatNumber(v),
            label: 'Jugadores estimados',
            color: '#22d3ee',
        },
        precio: {
            title: 'Precio',
            formatValue: (v) => v.toFixed(2) + '\u20ac',
            label: 'Precio predicho',
            color: '#fbbf24',
        },
        reviews: {
            title: 'Rese\u00f1as',
            formatValue: (v) => (v * 100).toFixed(1) + '%',
            label: 'Ratio positivo predicho',
            color: '#34d399',
        },
    };

    const c = config[type];
    const chartId = `chart-${type}-mini`;

    card.innerHTML = `
        <div class="prediction-card-header">
            <span class="prediction-card-title">${c.title}</span>
        </div>
        <div class="prediction-card-value">${c.formatValue(prediction.value)}</div>
        <div class="prediction-card-label">${c.label}</div>
        <div class="prediction-card-confidence">
            <div class="confidence-bar-container">
                <div class="confidence-bar" style="width: ${prediction.confidence * 100}%"></div>
            </div>
            <span class="confidence-text">${(prediction.confidence * 100).toFixed(0)}%</span>
        </div>
        <div class="prediction-card-chart">
            <canvas id="${chartId}"></canvas>
        </div>
        <div class="prediction-card-footer">
            <span class="prediction-card-model">${prediction.model_used}</span>
            <span class="view-detail-btn">Ver detalle</span>
        </div>
    `;

    renderMiniChart(chartId, prediction.details.history, c.color);

    card.addEventListener('click', () => {
        navigateToPredictionDetail(type, prediction);
    });
}

// ============================================================
// PREDICTION DETAIL VIEW
// ============================================================
function navigateToPredictionDetail(type, prediction) {
    showView('view-prediction');
    currentPrediction = { type, data: prediction };

    const container = document.getElementById('prediction-detail-content');
    const config = {
        popularidad: {
            title: 'Popularidad', formatValue: (v) => formatNumber(v),
            unit: 'Jugadores estimados', colorClass: 'popularidad',
        },
        precio: {
            title: 'Precio', formatValue: (v) => v.toFixed(2) + '€',
            unit: 'Precio predicho', colorClass: 'precio',
        },
        reviews: {
            title: 'Reseñas', formatValue: (v) => (v * 100).toFixed(1) + '%',
            unit: 'Ratio de reseñas positivas', colorClass: 'reviews',
        },
    };
    const c = config[type];

    let extraPanels = '';

    if (type === 'popularidad' && prediction.details.feature_importance) {
        const features = prediction.details.feature_importance;
        extraPanels += `
            <div class="detail-panel">
                <h3 class="detail-panel-title">Importancia de caracteristicas</h3>
                <div class="feature-list">
                    ${Object.entries(features).map(([name, val]) => `
                        <div class="feature-item">
                            <span class="feature-name">${formatFeatureName(name)}</span>
                            <div class="feature-bar-container">
                                <div class="feature-bar" style="width: ${val * 100}%"></div>
                            </div>
                            <span class="feature-value">${(val * 100).toFixed(0)}%</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    if (type === 'precio' && prediction.details.price_range) {
        const range = prediction.details.price_range;
        extraPanels += `
            <div class="detail-panel">
                <h3 class="detail-panel-title">Rango de precios</h3>
                <div class="price-range">
                    <div>
                        <div class="price-range-value" style="color:var(--accent-red)">${range.min}€</div>
                        <div class="price-range-label">Mínimo</div>
                    </div>
                    <div class="price-range-bar"><div class="price-range-fill"></div></div>
                    <div>
                        <div class="price-range-value" style="color:var(--accent-green)">${range.max}€</div>
                        <div class="price-range-label">Máximo</div>
                    </div>
                </div>
            </div>
        `;
    }

    if (type === 'reviews' && prediction.details.sentiment_distribution) {
        const sentiments = prediction.details.sentiment_distribution;
        const sentimentColors = {
            very_positive: '#22c55e',
            positive: '#34d399',
            mixed: '#fbbf24',
            negative: '#f87171',
            very_negative: '#ef4444',
        };
        const sentimentLabels = {
            very_positive: 'Muy positivo',
            positive: 'Positivo',
            mixed: 'Mixto',
            negative: 'Negativo',
            very_negative: 'Muy negativo',
        };
        extraPanels += `
            <div class="detail-panel">
                <h3 class="detail-panel-title">Distribucion de sentimiento</h3>
                <div class="sentiment-list">
                    ${Object.entries(sentiments).map(([key, val]) => `
                        <div class="sentiment-item">
                            <div class="sentiment-dot" style="background:${sentimentColors[key]}"></div>
                            <span class="sentiment-name">${sentimentLabels[key]}</span>
                            <span class="sentiment-value">${(val * 100).toFixed(1)}%</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    container.innerHTML = `
        <div class="prediction-detail-header">
            <img class="prediction-detail-game-img" src="${currentGame.banner_url}" alt="${currentGame.name}">
            <div class="prediction-detail-main">
                <div class="prediction-detail-type ${c.colorClass}">${c.title}</div>
                <div class="prediction-detail-value">${c.formatValue(prediction.value)}</div>
                <div class="prediction-detail-unit">${c.unit} — ${currentGame.name}</div>
                <div class="prediction-detail-confidence">
                    <span class="prediction-detail-confidence-label">Confianza del modelo:</span>
                    <span class="prediction-detail-confidence-value" style="color:var(--accent-${type === 'popularidad' ? 'cyan' : type === 'precio' ? 'gold' : 'green'})">${(prediction.confidence * 100).toFixed(1)}%</span>
                    <span class="prediction-detail-confidence-label">·</span>
                    <span class="prediction-detail-confidence-label">Modelo: ${prediction.model_used}</span>
                </div>
            </div>
        </div>

        <div class="detail-panels">
            <div class="detail-panel">
                <h3 class="detail-panel-title">Evolucion historica</h3>
                <div class="detail-chart-container">
                    <canvas id="chart-detail-history"></canvas>
                </div>
            </div>
            ${extraPanels}
        </div>
    `;

    const colors = { popularidad: '#22d3ee', precio: '#fbbf24', reviews: '#34d399' };
    renderDetailChart('chart-detail-history', prediction.details.history, colors[type]);
}

// ============================================================
// CHARTS (Chart.js)
// ============================================================
function renderMiniChart(canvasId, history, color) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    if (charts[canvasId]) charts[canvasId].destroy();

    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 100);
    gradient.addColorStop(0, color + '33');
    gradient.addColorStop(1, 'transparent');

    charts[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: history.map(h => h.month),
            datasets: [{
                data: history.map(h => h.value),
                borderColor: color,
                backgroundColor: gradient,
                fill: true,
                tension: 0.4,
                borderWidth: 2,
                pointRadius: 0,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
            scales: {
                x: { display: false },
                y: { display: false },
            },
        },
    });
}

function renderDetailChart(canvasId, history, color) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    if (charts[canvasId]) charts[canvasId].destroy();

    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 200);
    gradient.addColorStop(0, color + '40');
    gradient.addColorStop(1, 'transparent');

    charts[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: history.map(h => h.month),
            datasets: [{
                label: 'Valor',
                data: history.map(h => h.value),
                borderColor: color,
                backgroundColor: gradient,
                fill: true,
                tension: 0.4,
                borderWidth: 2.5,
                pointRadius: 4,
                pointBackgroundColor: color,
                pointHoverRadius: 6,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(15,23,42,0.9)',
                    borderColor: color,
                    borderWidth: 1,
                    titleColor: '#e2e8f0',
                    bodyColor: '#94a3b8',
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: false,
                },
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#64748b', font: { size: 11 } },
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#64748b', font: { size: 11 } },
                },
            },
        },
    });
}

// ============================================================
// HELPERS
// ============================================================
function formatNumber(n) {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toString();
}

function formatFeatureName(name) {
    return name.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

// ============================================================
// BACKGROUND ANIMATION — Floating figures
// ============================================================
function initBackground() {
    const container = document.getElementById('bg-figures');
    if (!container) return;

    const CONFIG = {
        IMG_SRC: '/static/img/figura.png',
        NUM_COLUMNS: 14,
        COL_WIDTH: 400,
        OVERLAP_OFFSET: -14,
        OVERLAP_END: 200,
        SCALE_MIN: 1.0,
        SCALE_MAX: 1.5,
        OPACITY_MIN: 0.22,
        OPACITY_MAX: 0.3,
        DUR_MIN: 40,
        DUR_MAX: 70,
        SWAY_MAX_PX: 50,
        SWAY_DUR_MIN: 8,
        SWAY_DUR_MAX: 15,
        BLUR_PX: 2,
    };

    const range = CONFIG.OVERLAP_END - CONFIG.OVERLAP_OFFSET;

    for (let i = 0; i < CONFIG.NUM_COLUMNS; i++) {
        const col = document.createElement('div');
        col.className = 'bg-chain-col';
        col.style.width = `${CONFIG.COL_WIDTH}px`;

        const goesUp = (i % 2 === 0);
        col.classList.add(goesUp ? 'up' : 'down');

        const leftPct = CONFIG.OVERLAP_OFFSET + (i / (CONFIG.NUM_COLUMNS - 1)) * range;
        col.style.left = `${leftPct}%`;

        const scale = CONFIG.SCALE_MIN + Math.random() * (CONFIG.SCALE_MAX - CONFIG.SCALE_MIN);
        col.style.transform = `scale(${scale})`;
        col.style.opacity = (CONFIG.OPACITY_MIN + Math.random() * (CONFIG.OPACITY_MAX - CONFIG.OPACITY_MIN)).toString();

        const sway = document.createElement('div');
        sway.className = 'bg-chain-sway';
        const swayAmount = Math.random() * CONFIG.SWAY_MAX_PX;
        const swayDur = CONFIG.SWAY_DUR_MIN + Math.random() * (CONFIG.SWAY_DUR_MAX - CONFIG.SWAY_DUR_MIN);
        sway.style.setProperty('--sway-amount', swayAmount);
        sway.style.setProperty('--sway-dur', `${swayDur}s`);
        sway.style.animationDelay = `-${Math.random() * swayDur}s`;

        const track = document.createElement('div');
        track.className = 'bg-chain-track';

        const durY = CONFIG.DUR_MIN + Math.random() * (CONFIG.DUR_MAX - CONFIG.DUR_MIN);
        track.style.animationDuration = `${durY}s`;

        const delayY = -(Math.random() * durY);
        track.style.animationDelay = `${delayY}s`;

        for (let j = 0; j < 3; j++) {
            const img = document.createElement('img');
            img.src = CONFIG.IMG_SRC;
            img.className = 'bg-chain-img';
            img.alt = '';
            img.draggable = false;
            track.appendChild(img);
        }

        sway.appendChild(track);
        col.appendChild(sway);
        container.appendChild(col);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadTrendingGames();
    setupSearch();
    setupNavigation();
    initBackground();
    initNoise();
    setupSidebarVisibility();
});

function setupSidebarVisibility() {
    const sidebar = document.querySelector('.sidebar-filters');
    const target = document.querySelector('.search-container');
    
    if (!sidebar || !target) return;

    const updateVisibility = () => {
        const rect = target.getBoundingClientRect();
        // Show 400px after the search container starts entering the viewport
        if (rect.top < (window.innerHeight * 0.9 - 400)) {
            sidebar.classList.remove('hidden');
        } else {
            sidebar.classList.add('hidden');
        }
    };

    window.addEventListener('scroll', updateVisibility);
    updateVisibility();
}

let sidebarSortRotation = 0;
function updateSidebarSortIcon() {
    const arrow = document.querySelector('.sidebar-icon-arrow');
    if (!arrow) return;
    sidebarSortRotation += 180;
    arrow.style.transform = `rotate(${sidebarSortRotation}deg)`;
}

// ============================================================
// NOISE GRAIN
// ============================================================
function initNoise() {
    const el = document.getElementById('bg-noise');
    if (!el) return;

    const SIZE = 150;
    const c = document.createElement('canvas');
    c.width = SIZE;
    c.height = SIZE;

    const ctx = c.getContext('2d');
    const img = ctx.createImageData(SIZE, SIZE);
    const data = img.data;

    for (let i = 0; i < data.length; i += 4) {
        const v = Math.floor(Math.random() * 256);
        data[i] = v;
        data[i + 1] = v;
        data[i + 2] = v;
        data[i + 3] = 255;
    }

    ctx.putImageData(img, 0, 0);
    el.style.backgroundImage = `url('${c.toDataURL()}')`;
}

/* ============================================================
   LÓGICA JS PARA EL VÍDEO HERO SCROLLYTELLING (VANILLA JS)
   ============================================================ */

const canvas = document.getElementById('hero-canvas');
const ctx = canvas.getContext('2d');
const echoCanvas = document.getElementById('hero-echo-canvas');
const echoCtx = echoCanvas.getContext('2d');

const frameCount = 192;
const currentFrame = index => `/static/img/frames/header${String(86399 + index).padStart(8, '0')}.jpg`;

const images = [];
const heroSequence = { frame: 0 };

const initCanvas = () => {
    if (canvas.width !== images[0].width) {
        canvas.width = images[0].width;
        canvas.height = images[0].height;
    }
    ctx.drawImage(images[0], 0, 0);
};

for (let i = 1; i <= frameCount; i++) {
    const img = new Image();

    if (i === 1) {
        img.onload = initCanvas;
    }

    img.src = currentFrame(i);
    images.push(img);

    if (i === 1 && img.complete) {
        initCanvas();
    }
}

const updateCanvas = () => {
    const scrollTop = document.documentElement.scrollTop;
    const heroScrollContainer = document.getElementById('hero-scroll-container');
    const maxScroll = heroScrollContainer.scrollHeight - window.innerHeight;
    const scrollFraction = scrollTop / maxScroll;
    const frameIndex = Math.min(frameCount - 1, Math.floor(scrollFraction * frameCount));
    if (images[frameIndex]) {
        requestAnimationFrame(() => {
            ctx.drawImage(images[frameIndex], 0, 0);
            const img = images[frameIndex];
            const ew = echoCanvas.clientWidth, eh = echoCanvas.clientHeight;
            if (echoCanvas.width !== ew) echoCanvas.width = ew;
            if (echoCanvas.height !== eh) echoCanvas.height = eh;
            const es = Math.max(ew / img.naturalWidth, eh / img.naturalHeight);
            echoCtx.drawImage(img, (ew - img.naturalWidth * es) / 2, eh - img.naturalHeight * es, img.naturalWidth * es, img.naturalHeight * es);
        });
    }
};

window.addEventListener('scroll', updateCanvas);

let isAutoScrolling = true;
const pixelsPerFrame = 20;
const cinematicAutoPlay = () => {
    if (!isAutoScrolling) return;

    const heroScrollContainer = document.getElementById('hero-scroll-container');
    const maxScroll = heroScrollContainer.scrollHeight - window.innerHeight;

    if (maxScroll <= 0) {
        // Layout not ready yet, retry
        requestAnimationFrame(cinematicAutoPlay);
        return;
    }

    window.scrollBy(0, pixelsPerFrame);

    if (window.scrollY >= maxScroll) {
        isAutoScrolling = false;
        return;
    }

    requestAnimationFrame(cinematicAutoPlay);
};

window.addEventListener('load', () => {
    // Reset scroll position on reload to avoid stuck state
    window.scrollTo(0, 0);
    // Wait a tick for layout to settle, then start
    setTimeout(() => {
        if (images[0] && images[0].complete) {
            requestAnimationFrame(cinematicAutoPlay);
        } else {
            images[0].addEventListener('load', () => {
                requestAnimationFrame(cinematicAutoPlay);
            });
        }
    }, 100);
});

const stopAutoScroll = () => {
    isAutoScrolling = false;
};

window.addEventListener('wheel', stopAutoScroll);
window.addEventListener('touchstart', stopAutoScroll);
window.addEventListener('mousedown', stopAutoScroll);
window.addEventListener('keydown', stopAutoScroll);