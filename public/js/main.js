// Instagram Downloader Frontend - PRISM Design
const API_BASE = '';

// DOM Elements - initialized after DOM content loaded
let urlInput, fetchBtn, downloadMediaBtn, pasteBtn, clearBtn, closeResultBtn;
let newDownloadBtn, resultSection, singleResult, profileResult;
let mediaGrid, downloadedSection, downloadLink, errorMessage, loading;

function getDomElements() {
    urlInput = document.getElementById('url-input');
    fetchBtn = document.getElementById('fetch-btn');
    downloadMediaBtn = document.getElementById('download-media-btn');
    pasteBtn = document.getElementById('paste-btn');
    clearBtn = document.getElementById('clear-btn');
    closeResultBtn = document.getElementById('close-result');
    newDownloadBtn = document.getElementById('new-download-btn');
    resultSection = document.getElementById('result-section');
    singleResult = document.getElementById('single-result');
    profileResult = document.getElementById('profile-result');
    mediaGrid = document.getElementById('media-grid');
    downloadedSection = document.getElementById('downloaded-section');
    downloadLink = document.getElementById('download-link');
    errorMessage = document.getElementById('error-message');
    loading = document.getElementById('loading');
}

// Store fetched media data
let currentMedia = null;
let fetchedData = null;
let mediaQueue = [];
let previousView = null;  // Track navigation state for back-navigation
let confettiAnimationId = null;  // Track confetti animation for cleanup

// Initialize paste/clear buttons after DOM is ready
function initButtons() {
    if (navigator.clipboard && pasteBtn) {
        pasteBtn.classList.remove('hidden');
    }
}

// Event Listeners - attached after DOM is loaded
function attachEventListeners() {
    if (pasteBtn) pasteBtn.addEventListener('click', handlePaste);
    if (clearBtn) clearBtn.addEventListener('click', handleClear);
    if (closeResultBtn) closeResultBtn.addEventListener('click', closeResult);
    if (fetchBtn) fetchBtn.addEventListener('click', handleFetch);
    if (downloadMediaBtn) downloadMediaBtn.addEventListener('click', handleDownload);
    if (newDownloadBtn) newDownloadBtn.addEventListener('click', handleNewDownload);

    // Allow Enter key to fetch
    if (urlInput) {
        urlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleFetch();
            }
        });
        // Show clear button when user types
        urlInput.addEventListener('input', () => {
            showClearBtn(urlInput.value.length > 0);
        });
    }
}

// Show error message
function showError(message) {
    if (!errorMessage) return;
    errorMessage.innerHTML = `
        <svg viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
        <span class="error-text">${escapeHtml(message)}</span>
    `;
    errorMessage.classList.remove('hidden');

    // Auto-hide after 5 seconds
    setTimeout(() => {
        errorMessage.classList.add('hidden');
    }, 5000);
}

// Clear error message
function clearError() {
    if (errorMessage) {
        errorMessage.classList.add('hidden');
    }
}

// Show loading state
function showLoading(show) {
    if (!loading) return;
    loading.classList.toggle('hidden', !show);

    // Show/hide loading progress dots
    const progressDots = document.getElementById('loading-progress');
    if (progressDots) {
        progressDots.style.display = show ? 'block' : 'none';
    }

    if (show) {
        if (fetchBtn) fetchBtn.disabled = true;
        if (downloadMediaBtn) downloadMediaBtn.disabled = true;
        if (urlInput) urlInput.disabled = true;

        // Clear any existing interval before creating new one
        if (loading.dataset.intervalId) {
            clearInterval(parseInt(loading.dataset.intervalId));
        }

        // Cycle through loading words
        const loadingTexts = ['analyzing', 'refactoring', 'extracting', 'decoding'];
        let textIndex = 0;
        const loadingWords = document.querySelector('.loading-words');

        if (loadingWords) {
            loadingWords.textContent = loadingTexts[textIndex];
            const wordInterval = setInterval(() => {
                textIndex = (textIndex + 1) % loadingTexts.length;
                loadingWords.textContent = loadingTexts[textIndex];
            }, 800);
            loading.dataset.intervalId = wordInterval;
        }
    } else {
        if (fetchBtn) fetchBtn.disabled = false;
        if (downloadMediaBtn) downloadMediaBtn.disabled = false;
        if (urlInput) urlInput.disabled = false;

        if (loading.dataset.intervalId) {
            clearInterval(parseInt(loading.dataset.intervalId));
        }
    }
}

// Paste from clipboard
async function handlePaste() {
    try {
        const text = await navigator.clipboard.readText();
        if (urlInput) urlInput.value = text;
        showClearBtn(true);
    } catch (err) {
        showError('Failed to access clipboard. Please paste manually.');
    }
}

// Clear input field
function handleClear() {
    if (urlInput) urlInput.value = '';
    showClearBtn(false);
    closeResult();
    clearError();
}

// Toggle clear button visibility
function showClearBtn(show) {
    if (clearBtn) clearBtn.style.display = show ? 'flex' : 'none';
}

// Close result section
function closeResult() {
    if (downloadedSection) downloadedSection.classList.add('hidden');
    if (singleResult) singleResult.classList.add('hidden');

    // Clear result grid
    const resultGrid = document.getElementById('result-grid');
    if (resultGrid) resultGrid.innerHTML = '';

    if (previousView === 'profile') {
        // Go back to profile grid
        if (profileResult) profileResult.classList.remove('hidden');
        if (resultSection) resultSection.classList.remove('hidden');
        previousView = null;
    } else {
        // Normal close — hide everything
        if (resultSection) resultSection.classList.add('hidden');
        if (profileResult) profileResult.classList.add('hidden');
    }

    mediaQueue = [];
}

// Handle new download request
function handleNewDownload() {
    closeResult();
    if (urlInput) urlInput.focus();
}

// Handle fetch request
async function handleFetch() {
    if (!urlInput) return;
    const url = urlInput.value.trim();

    if (!url) {
        showError('Please enter an Instagram URL');
        return;
    }

    showLoading(true);
    clearError();
    closeResult();
    currentMedia = null;
    fetchedData = null;

    try {
        const response = await fetch(`${API_BASE}/api/fetch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to fetch data');
        }

        if (data.success) {
            fetchedData = data;

            // Determine result type based on response structure
            if (Array.isArray(data.medias)) {
                // User profile response
                renderUserMedias(data.medias);
            } else if (data.data) {
                renderResult(data.data);
            } else {
                showError('No media data found');
            }
        } else {
            showError(data.message || 'Failed to fetch media');
        }
    } catch (error) {
        showError(error.message || 'An error occurred');
    } finally {
        showLoading(false);
    }
}

// Handle download request
async function handleDownload() {
    if (!currentMedia && !fetchedData) {
        showError('No media selected for download');
        return;
    }

    showLoading(true);
    clearError();

    try {
        const url = currentMedia?.url || fetchedData?.data?.url;
        if (!url) {
            throw new Error('No URL available for download');
        }

        const response = await fetch(`${API_BASE}/api/download`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to download media');
        }

        if (data.success) {
            const filename = data.path.split('/').pop();
            currentMedia = { ...currentMedia, download_path: data.path };

            // Show success with confetti animation
            const downloadedMessage = downloadedSection.querySelector('.success-message');
            if (downloadedMessage) {
                downloadedMessage.innerHTML = `
                    <strong style="color: #10B981; display: block; margin-bottom: 12px;">Refraction Complete!</strong>
                    <span style="font-family: 'JetBrains Mono', monospace;">${escapeHtml(filename)}</span>
                    <br>
                    <span style="color: var(--text-secondary); font-size: 0.9rem;">Downloaded successfully to server</span>
                `;
            }
            if (downloadLink) downloadLink.href = `${API_BASE}/api/download/${encodeURIComponent(filename)}`;
            if (downloadLink) downloadLink.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" style="display:inline;vertical-align:middle;margin-right:8px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>Open: ${escapeHtml(filename)}`;
            if (downloadedSection) downloadedSection.classList.remove('hidden');

            // Trigger confetti
            triggerConfetti();
        } else {
            showError(data.message || 'Failed to download media');
        }
    } catch (error) {
        showError(error.message || 'An error occurred');
    } finally {
        showLoading(false);
    }
}

// Unified render function for all post types (single + album)
function renderResult(data) {
    if (!resultSection || !singleResult || !profileResult) return;

    resultSection.classList.remove('hidden');
    singleResult.classList.remove('hidden');
    profileResult.classList.add('hidden');

    const resultGrid = document.getElementById('result-grid');
    if (!resultGrid) return;

    // Collect all media items to display in the grid
    const items = [];
    if (data.media_type === 8 && Array.isArray(data.carousel_media)) {
        // Album: one cell per carousel item
        data.carousel_media.forEach((child, i) => {
            items.push({
                ...child,
                index: i,
            });
        });
    } else {
        // Single post: one cell
        items.push({ ...data, index: 0 });
    }

    // Build grid HTML
    let gridHtml = '';
    items.forEach(item => {
        const type = escapeHtml(item.media_type_name || 'Post');
        const thumb = escapeHtml(item.thumbnail_url || '');
        gridHtml += `
            <div class="media-cell" data-index="${item.index}">
                <img src="${thumb}" alt="${type}" loading="lazy">
                <span class="cell-badge">${type}</span>
            </div>
        `;
    });
    resultGrid.innerHTML = gridHtml;

    // Click handlers: clicking a cell sets it as currentMedia
    resultGrid.querySelectorAll('.media-cell').forEach(cell => {
        cell.addEventListener('click', () => {
            const idx = parseInt(cell.getAttribute('data-index'));
            const item = items[idx];
            if (item) {
                currentMedia = item;
                // Highlight selected cell
                resultGrid.querySelectorAll('.media-cell').forEach(c => c.style.borderColor = '');
                cell.style.borderColor = 'var(--color-blue)';
            }
        });
    });

    // Update metadata (from parent post data)
    const metaValues = document.querySelectorAll('.meta-value');
    if (metaValues.length > 1) {
        metaValues[1].textContent = data.media_id || data.media_pk || 'N/A';
    }

    const usernameEl = document.querySelector('.username');
    if (usernameEl) usernameEl.textContent = data.user?.username || 'Unknown';

    // Update stats
    const stats = document.querySelectorAll('.stats-bar .stat-item');
    if (stats.length > 0 && stats[0].querySelector('.count')) stats[0].querySelector('.count').textContent = (data.view_count || 0).toLocaleString();
    if (stats.length > 1 && stats[1].querySelector('.count')) stats[1].querySelector('.count').textContent = (data.like_count || 0).toLocaleString();
    if (stats.length > 2 && stats[2].querySelector('.count')) stats[2].querySelector('.count').textContent = (data.comment_count || 0).toLocaleString();

    // Update caption
    const captionEl = document.querySelector('.caption-text');
    if (captionEl) captionEl.textContent = data.caption || 'No caption';

    // Update download button text
    const downloadBtnText = document.querySelector('#download-media-btn .btn-text');
    if (downloadBtnText) {
        if (data.media_type === 8) {
            downloadBtnText.textContent = 'Download Album';
        } else {
            const type = data.media_type_name || 'Post';
            downloadBtnText.textContent = (type === 'Video' || type === 'Reel') ? 'Download Video' : 'Download Image';
        }
    }

    // Set default currentMedia (first item for album, or the post itself)
    currentMedia = items[0] || data;
}

// Render user medias list
function renderUserMedias(medias) {
    if (!resultSection || !profileResult || !singleResult || !mediaGrid) return;

    resultSection.classList.remove('hidden');
    profileResult.classList.remove('hidden');
    singleResult.classList.add('hidden');
    previousView = null;  // Reset navigation state

    // Clear queue for new profile
    mediaQueue = [];

    let items = '';
    medias.forEach((media, index) => {
        const type = escapeHtml(media.media_type_name || 'Post');
        const thumb = escapeHtml(media.thumbnail_url || '');
        const mediaUrl = escapeHtml(media.url || '');
        const likes = media.like_count || 0;
        const views = media.view_count || 0;

        items += `
            <div class="media-item" data-url="${mediaUrl}" data-index="${index}">
                <div class="media-thumb">
                    <img src="${thumb}" alt="Preview" loading="lazy">
                    <span class="type-badge ${type.toLowerCase()}">${type}</span>
                </div>
                <div class="media-stats">
                    ${likes ? `<span class="stat likes"><svg viewBox="0 0 24 24"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg> ${likes.toLocaleString()}</span>` : ''}
                    ${views ? `<span class="stat views"><svg viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg> ${views.toLocaleString()}</span>` : ''}
                </div>
            </div>
        `;
    });

    mediaGrid.innerHTML = items;

    // Add click handlers for media items
    mediaGrid.querySelectorAll('.media-item').forEach(item => {
        item.addEventListener('click', () => {
            const url = item.getAttribute('data-url');
            fetchMediaByUrl(url);
        });
    });
}

// Fetch media by URL
async function fetchMediaByUrl(url) {
    previousView = 'profile';  // Track that we came from profile grid
    showLoading(true);

    try {
        const response = await fetch(`${API_BASE}/api/fetch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
        });

        const data = await response.json();

        if (data.success && data.data) {
            renderResult(data.data);
        } else {
            showError(data.message || 'Failed to load media');
        }
    } catch (error) {
        showError('Failed to load media');
    } finally {
        showLoading(false);
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/\n/g, '<br>');
}

// Confetti Animation
function triggerConfetti() {
    const canvas = document.getElementById('confetti-canvas');
    if (!canvas) return;

    // Cancel any existing animation
    if (confettiAnimationId) {
        cancelAnimationFrame(confettiAnimationId);
        confettiAnimationId = null;
    }

    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const colors = ['#F43F5E', '#F97316', '#10B981', '#3B82F6', '#8B5CF6', '#EC4899'];
    const particles = [];
    const particleCount = 150;

    for (let i = 0; i < particleCount; i++) {
        particles.push({
            x: window.innerWidth / 2,
            y: window.innerHeight / 2,
            vx: (Math.random() - 0.5) * 15,
            vy: (Math.random() - 0.5) * 15,
            size: Math.random() * 6 + 3,
            color: colors[Math.floor(Math.random() * colors.length)],
            rotation: Math.random() * 360,
            rotationSpeed: (Math.random() - 0.5) * 10,
            gravity: 0.2,
            drag: 0.96,
        });
    }

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        let activeParticles = 0;
        particles.forEach(p => {
            if (p.y < canvas.height && Math.abs(p.vx) > 0.1) {
                activeParticles++;

                p.x += p.vx;
                p.y += p.vy;
                p.vy += p.gravity;
                p.vx *= p.drag;
                p.vy *= p.drag;
                p.rotation += p.rotationSpeed;

                ctx.save();
                ctx.translate(p.x, p.y);
                ctx.rotate((p.rotation * Math.PI) / 180);
                ctx.fillStyle = p.color;
                ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
                ctx.restore();
            }
        });

        if (activeParticles > 0) {
            confettiAnimationId = requestAnimationFrame(animate);
        } else {
            cancelAnimationFrame(confettiAnimationId);
            confettiAnimationId = null;
        }
    }

    animate();
}

// Initialize when DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    getDomElements();
    initButtons();
    attachEventListeners();
});
