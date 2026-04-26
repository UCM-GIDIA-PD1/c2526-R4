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
    });
    document.getElementById('btn-back-game').addEventListener('click', () => {
        showView('view-game');
    });
}

// ============================================================
// SEARCH (same fetch() pattern as flower3.html)
// ============================================================
function setupSearch() {
    const input = document.getElementById('search-input');

    input.addEventListener('input', () => {
        const q = input.value.trim().toLowerCase();
        const cards = document.querySelectorAll('.game-card');

        cards.forEach(card => {
            const name = (card.dataset.name || '').toLowerCase();
            if (!q || name.includes(q)) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
    });
}

// ============================================================
// TRENDING GAMES
// ============================================================
async function loadTrendingGames() {
    const grid = document.getElementById('game-grid');
    grid.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    const res = await fetch('/api/trending');
    const games = await res.json();

    grid.innerHTML = games.map(g => `
        <div class="game-card" data-appid="${g.appid}" data-name="${g.name}">
            <img class="game-card-banner" src="${g.banner_url}" alt="${g.name}" loading="lazy">
        </div>
    `).join('');

    // Click to navigate to game detail
    grid.querySelectorAll('.game-card').forEach(card => {
        card.addEventListener('click', () => {
            navigateToGame(parseInt(card.dataset.appid));
        });
    });
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

    // Render game header
    const reviewPercent = Math.round(game.positive_reviews / (game.positive_reviews + game.negative_reviews) * 100);

    // Render new structure
    container.innerHTML = `
        <div class="game-detail-header-container">
            <img class="game-banner-large" src="${game.banner_url}" alt="${game.name}">
            <div class="game-info-primary">
                <h1 class="game-detail-name">${game.name}</h1>
                <div class="game-detail-dev-meta">
                    <span>Desarrollado por <strong>${game.developer}</strong></span>
                    <span class="game-detail-date-meta">Lanzado el ${game.release_date}</span>
                </div>
                <div class="genre-tags-list">
                    ${game.genres.map(g => `<span class="genre-chip">${g}</span>`).join('')}
                </div>
            </div>
        </div>

        <div class="prediction-section-list">
            <button class="prediction-action-btn" id="btn-predict-popularidad" onclick="requestPrediction('popularidad', ${game.appid})">
                <span class="prediction-btn-title">Popularidad</span>
                <span class="prediction-btn-hint">Predice cuántos jugadores tendrá este juego basándose en tendencias actuales.</span>
            </button>
            
            <button class="prediction-action-btn" id="btn-predict-precio" onclick="requestPrediction('precio', ${game.appid})">
                <span class="prediction-btn-title">Precio</span>
                <span class="prediction-btn-hint">Analiza el valor óptimo del juego y posibles fluctuaciones en el mercado.</span>
            </button>
            
            <button class="prediction-action-btn" id="btn-predict-reviews" onclick="requestPrediction('reviews', ${game.appid})">
                <span class="prediction-btn-title">Reseñas</span>
                <span class="prediction-btn-hint">Anticipa el sentimiento de la comunidad y la calificación de los usuarios.</span>
            </button>
        </div>

        <div id="prediction-results-area" class="prediction-results-area">
            </div>
    `;
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
});

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

const frameCount = 240;
const currentFrame = index => `/static/img/frames/ezgif-frame-${index.toString().padStart(3, '0')}.jpg`;

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

    const frameIndex = Math.min(
        frameCount - 1,
        Math.floor(scrollFraction * frameCount)
    );

    if (images[frameIndex]) {
        requestAnimationFrame(() => {
            ctx.drawImage(images[frameIndex], 0, 0);
        });
    }
};

window.addEventListener('scroll', updateCanvas);

let isAutoScrolling = true;
const pixelsPerFrame = window.innerHeight / (frameCount / 2.5);

const cinematicAutoPlay = () => {
    if (!isAutoScrolling) return;

    window.scrollBy(0, pixelsPerFrame);

    const heroScrollContainer = document.getElementById('hero-scroll-container');
    if (window.scrollY >= heroScrollContainer.scrollHeight - window.innerHeight) {
        isAutoScrolling = false;
        return;
    }

    requestAnimationFrame(cinematicAutoPlay);
};

window.addEventListener('load', () => {
    requestAnimationFrame(cinematicAutoPlay);
});

const stopAutoScroll = () => {
    isAutoScrolling = false;
};

window.addEventListener('wheel', stopAutoScroll);
window.addEventListener('touchstart', stopAutoScroll);
window.addEventListener('mousedown', stopAutoScroll);
window.addEventListener('keydown', stopAutoScroll);