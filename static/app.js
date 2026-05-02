/* ============================================
   自助旅遊助手 - Frontend Logic
   ============================================ */

const API_BASE = window.location.origin;

// ============================================================
// State
// ============================================================

let recognition1 = null;
let recognition2 = null;
let map = null;
let mapMarkers = [];
let isRecording1 = false;
let isRecording2 = false;

// ============================================================
// Init
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initSpeech();
    initTranslate();
    initCurrency();
    initRoute();
    initFood();
    initChat();
    initExpenses();
    initBudget();
    checkHealth();
    setInterval(checkHealth, 30000); // 每 30 秒檢查
});

// ============================================================
// Tab Switching
// ============================================================

function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            const tabId = btn.dataset.tab;
            document.getElementById(`tab-${tabId}`).classList.add('active');

            // 初始化地圖（第一次切換到路線標籤時）
            if (tabId === 'route' && !map) {
                setTimeout(initMap, 100);
            }
        });
    });
}

// ============================================================
// Health Check
// ============================================================

async function checkHealth() {
    try {
        const res = await fetch(`${API_BASE}/api/health`);
        const data = await res.json();
        const statusEl = document.getElementById('navStatus');
        statusEl.innerHTML = `
            <span class="status-dot"></span>
            <span class="status-text">${data.ollama_model} ✓</span>
        `;
    } catch (e) {
        const statusEl = document.getElementById('navStatus');
        statusEl.innerHTML = `
            <span class="status-dot error"></span>
            <span class="status-text">離線 ✗</span>
        `;
    }
}

async function warmupModel() {
    const statusEl = document.getElementById('navStatus');
    statusEl.innerHTML = `
        <span class="status-dot"></span>
        <span class="status-text">🔥 預熱中...</span>
    `;

    try {
        const res = await fetch(`${API_BASE}/api/warmup`, { method: 'POST' });
        const data = await res.json();
        if (data.status === 'warmed_up') {
            statusEl.innerHTML = `
                <span class="status-dot"></span>
                <span class="status-text">🔥 ${data.model} 已就緒 ✓</span>
            `;
        } else {
            statusEl.innerHTML = `
                <span class="status-dot error"></span>
                <span class="status-text">預熱失敗 ✗</span>
            `;
        }
    } catch (e) {
        const statusEl = document.getElementById('navStatus');
        statusEl.innerHTML = `
            <span class="status-dot error"></span>
            <span class="status-text">連線失敗 ✗</span>
        `;
    }
}

// 頁面載入後自動預熱
setTimeout(warmupModel, 2000);

// ============================================================
// Speech Recognition Setup
// ============================================================

function initSpeech() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        console.warn('Web Speech API 不支援');
        document.querySelectorAll('.mic-btn').forEach(btn => {
            btn.disabled = true;
            btn.title = '瀏覽器不支援語音輸入';
        });
        return;
    }

    // 第一組語音輸入
    recognition1 = new SpeechRecognition();
    recognition1.continuous = false;
    recognition1.interimResults = true;

    recognition1.onresult = (event) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
        }
        document.getElementById('sourceText').value = transcript;
    };

    recognition1.onend = () => {
        isRecording1 = false;
        document.getElementById('micBtn').classList.remove('recording');
    };

    // 第二組語音輸入
    recognition2 = new SpeechRecognition();
    recognition2.continuous = false;
    recognition2.interimResults = true;

    recognition2.onresult = (event) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
        }
        document.getElementById('sourceText2').value = transcript;
    };

    recognition2.onend = () => {
        isRecording2 = false;
        document.getElementById('micBtn2').classList.remove('recording');
    };

    // 麥克風按鈕
    document.getElementById('micBtn').addEventListener('click', toggleMic1);
    document.getElementById('micBtn2').addEventListener('click', toggleMic2);
}

function toggleMic1() {
    if (!recognition1) return;
    const btn = document.getElementById('micBtn');
    const sourceLang = document.getElementById('sourceLang').value;

    if (isRecording1) {
        recognition1.stop();
        isRecording1 = false;
        btn.classList.remove('recording');
    } else {
        recognition1.lang = sourceLang;
        recognition1.start();
        isRecording1 = true;
        btn.classList.add('recording');
    }
}

function toggleMic2() {
    if (!recognition2) return;
    const btn = document.getElementById('micBtn2');
    const targetLang = document.getElementById('targetLang').value;

    if (isRecording2) {
        recognition2.stop();
        isRecording2 = false;
        btn.classList.remove('recording');
    } else {
        recognition2.lang = targetLang;
        recognition2.start();
        isRecording2 = true;
        btn.classList.add('recording');
    }
}

// ============================================================
// Translation
// ============================================================

function initTranslate() {
    // 交換語言
    document.getElementById('swapLangs').addEventListener('click', () => {
        const s = document.getElementById('sourceLang');
        const t = document.getElementById('targetLang');
        [s.value, t.value] = [t.value, s.value];
    });

    // 翻譯按鈕 1
    document.getElementById('translateBtn').addEventListener('click', () => {
        translateText('sourceText', 'sourceLang', 'targetLang', 'translatedText');
    });

    // 翻譯按鈕 2
    document.getElementById('translateBtn2').addEventListener('click', () => {
        translateText('sourceText2', 'targetLang', 'sourceLang', 'translatedText2');
    });

    // 朗讀
    document.getElementById('speakBtn').addEventListener('click', () => {
        speakText('translatedText', document.getElementById('targetLang').value);
    });

    document.getElementById('speakBtn2').addEventListener('click', () => {
        speakText('translatedText2', document.getElementById('sourceLang').value);
    });

    // 複製
    document.getElementById('copyBtn').addEventListener('click', () => {
        const text = document.getElementById('translatedText').textContent;
        navigator.clipboard.writeText(text.replace('翻譯結果會顯示在這裡...', ''));
    });

    // 清除
    document.getElementById('clearSource').addEventListener('click', () => {
        document.getElementById('sourceText').value = '';
        document.getElementById('translatedText').textContent = '翻譯結果會顯示在這裡...';
    });

    document.getElementById('clearSource2').addEventListener('click', () => {
        document.getElementById('sourceText2').value = '';
        document.getElementById('translatedText2').textContent = '反向翻譯結果...';
    });
}

async function translateText(sourceId, sourceLangId, targetLangId, resultId) {
    const text = document.getElementById(sourceId).value.trim();
    if (!text) return;

    const sourceLang = document.getElementById(sourceLangId).value;
    const targetLang = document.getElementById(targetLangId).value;

    // 先檢查翻譯快取
    const cached = await TranslationCache.get(text, sourceLang, targetLang);
    if (cached) {
        document.getElementById(resultId).textContent = cached;
        return;
    }

    showLoading();
    try {
        const res = await fetch(`${API_BASE}/api/translate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text,
                source_lang: sourceLang,
                target_lang: targetLang,
            }),
        });

        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        document.getElementById(resultId).textContent = data.translated;

        // 存入快取
        await TranslationCache.put(text, sourceLang, targetLang, data.translated);
    } catch (e) {
        // 離線時嘗試從快取取得
        const offlineCached = await TranslationCache.get(text, sourceLang, targetLang);
        if (offlineCached) {
            document.getElementById(resultId).textContent = `📴 離線快取: ${offlineCached}`;
        } else {
            document.getElementById(resultId).textContent = `錯誤: ${e.message}`;
        }
    } finally {
        hideLoading();
    }
}

function speakText(elementId, lang) {
    const text = document.getElementById(elementId).textContent;
    if (!text || text.includes('翻譯結果')) return;

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang;
    utterance.rate = 0.9;
    speechSynthesis.cancel();
    speechSynthesis.speak(utterance);
}

// ============================================================
// Currency
// ============================================================

function initCurrency() {
    document.getElementById('convertBtn').addEventListener('click', convertCurrency);
    document.getElementById('currencyAmount').addEventListener('input', debounce(convertCurrency, 500));

    // 載入快速參考
    loadQuickRates();
}

async function convertCurrency() {
    const amount = parseFloat(document.getElementById('currencyAmount').value);
    const from = document.getElementById('fromCurrency').value;
    const to = document.getElementById('toCurrency').value;

    if (isNaN(amount) || amount <= 0) return;

    showLoading();
    try {
        const res = await fetch(`${API_BASE}/api/currency`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount, from_currency: from, to_currency: to }),
        });

        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        document.getElementById('currencyResult').value = `${data.result} ${to}`;
        document.getElementById('rateInfo').textContent =
            `${data.rate_info} | 更新: ${data.timestamp}`;
    } catch (e) {
        document.getElementById('rateInfo').textContent = `錯誤: ${e.message}`;
    } finally {
        hideLoading();
    }
}

async function loadQuickRates() {
    try {
        const res = await fetch(`${API_BASE}/api/currency`);
        const data = await res.json();
        const grid = document.getElementById('ratesGrid');
        const major = ['USD', 'EUR', 'JPY', 'GBP', 'CNY', 'THB', 'KRW', 'HKD'];
        const flags = {
            USD: '🇺🇸', EUR: '🇪🇺', JPY: '🇯🇵', GBP: '🇬🇧',
            CNY: '🇨🇳', THB: '🇹🇭', KRW: '🇰🇷', HKD: '🇭🇰'
        };

        grid.innerHTML = major.map(code => {
            const rate = data.rates?.[code];
            return rate ? `
                <div class="rate-item">
                    <div class="flag">${flags[code] || ''}</div>
                    <div class="code">${code}</div>
                    <div class="value">1 TWD = ${rate}</div>
                </div>
            ` : '';
        }).join('');
    } catch (e) {
        console.error('載入匯率失敗', e);
    }
}

// ============================================================
// Route Planning
// ============================================================

function initRoute() {
    // 交通方式選擇
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    // GPS 定位
    document.getElementById('gpsBtn').addEventListener('click', getLocation);

    // 規劃路線
    document.getElementById('routeBtn').addEventListener('click', planRoute);
}

function initMap() {
    map = L.map('map').setView([25.0330, 121.5654], 6);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
    }).addTo(map);
}

function getLocation() {
    if (!navigator.geolocation) {
        alert('瀏覽器不支援定位');
        return;
    }

    const btn = document.getElementById('gpsBtn');
    btn.textContent = '⏳';

    navigator.geolocation.getCurrentPosition(
        async (pos) => {
            const lat = pos.coords.latitude;
            const lon = pos.coords.longitude;

            // 反地理編碼
            try {
                const res = await fetch(
                    `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&accept-language=zh-TW`
                );
                const data = await res.json();
                document.getElementById('routeStart').value = data.display_name || `${lat}, ${lon}`;
            } catch {
                document.getElementById('routeStart').value = `${lat}, ${lon}`;
            }

            btn.textContent = '📍';
        },
        () => {
            alert('無法取得位置');
            btn.textContent = '📍';
        },
        { enableHighAccuracy: true, timeout: 10000 }
    );
}

async function planRoute() {
    const start = document.getElementById('routeStart').value.trim();
    const end = document.getElementById('routeEnd').value.trim();
    const mode = document.querySelector('.mode-btn.active')?.dataset.mode || 'foot';

    if (!start || !end) {
        alert('請輸入起點和終點');
        return;
    }

    showLoading();
    try {
        const res = await fetch(`${API_BASE}/api/route`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ start, end, mode }),
        });

        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        displayRoute(data);
    } catch (e) {
        if (!navigator.onLine) {
            alert('📴 離線狀態，無法規劃路線。上線後再試。');
        } else {
            alert(`路線規劃失敗: ${e.message}`);
        }
    } finally {
        hideLoading();
    }
}

function displayRoute(data) {
    document.getElementById('routeResult').classList.remove('hidden');
    document.getElementById('routeDistance').textContent = `${data.distance_km} km`;
    document.getElementById('routeDuration').textContent = `${data.duration_min} 分鐘`;

    const stepsEl = document.getElementById('routeSteps');
    stepsEl.innerHTML = data.steps.map((step, i) => `
        <div class="step-item">
            <span class="step-num">${i + 1}</span>
            <span>${step.instruction}</span>
        </div>
    `).join('');

    // 更新地圖
    if (map) {
        clearMapMarkers();
        // 重新 geocode 來取得座標
        Promise.all([
            geocodeLocation(data.start),
            geocodeLocation(data.end)
        ]).then(([startLoc, endLoc]) => {
            if (startLoc && endLoc) {
                const startIcon = L.divIcon({
                    html: '<div style="font-size:24px">🟢</div>',
                    iconSize: [24, 24],
                    className: ''
                });
                const endIcon = L.divIcon({
                    html: '<div style="font-size:24px">🔴</div>',
                    iconSize: [24, 24],
                    className: ''
                });

                L.marker([startLoc.lat, startLoc.lon], { icon: startIcon })
                    .addTo(map)
                    .bindPopup(`起點: ${data.start}`);
                L.marker([endLoc.lat, endLoc.lon], { icon: endIcon })
                    .addTo(map)
                    .bindPopup(`終點: ${data.end}`);

                const bounds = L.latLngBounds(
                    [startLoc.lat, startLoc.lon],
                    [endLoc.lat, endLoc.lon]
                );
                map.fitBounds(bounds, { padding: [50, 50] });
            }
        });
    }
}

async function geocodeLocation(query) {
    try {
        const res = await fetch(`${API_BASE}/api/geocode`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query }),
        });
        if (!res.ok) return null;
        return await res.json();
    } catch {
        return null;
    }
}

function clearMapMarkers() {
    mapMarkers.forEach(m => map.removeLayer(m));
    mapMarkers = [];
}

// ============================================================
// Food Recommendations
// ============================================================

function initFood() {
    document.getElementById('foodBtn').addEventListener('click', getFoodRecommendations);
}

async function getFoodRecommendations() {
    const location = document.getElementById('foodLocation').value.trim();
    if (!location) {
        alert('請輸入地點');
        return;
    }

    showLoading();
    try {
        const res = await fetch(`${API_BASE}/api/food`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                location,
                cuisine: document.getElementById('foodCuisine').value || undefined,
                budget: document.getElementById('foodBudget').value || undefined,
                count: 5,
            }),
        });

        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        displayFood(data);
    } catch (e) {
        alert(`美食推薦失敗: ${e.message}`);
    } finally {
        hideLoading();
    }
}

function displayFood(data) {
    const container = document.getElementById('foodResult');
    const foods = data.foods || [];

    if (foods.length === 0 && data.foods_raw) {
        container.innerHTML = `
            <div class="card">
                <p>${data.foods_raw}</p>
            </div>
        `;
        return;
    }

    container.innerHTML = foods.map(food => `
        <div class="food-card">
            <h4>${food.name || '未知餐廳'}</h4>
            <span class="cuisine-tag">${food.cuisine || ''}</span>
            <span class="cuisine-tag">${food.price_range || ''}</span>
            <p class="desc">${food.description || ''}</p>
            ${food.highlight ? `<p class="highlight">⭐ ${food.highlight}</p>` : ''}
        </div>
    `).join('');
}

// ============================================================
// Chat Assistant
// ============================================================

function initChat() {
    const input = document.getElementById('chatInput');
    const sendBtn = document.getElementById('chatSendBtn');

    sendBtn.addEventListener('click', sendChatMessage);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChatMessage();
    });
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;

    appendChatMsg('user', msg);
    input.value = '';

    showLoading();
    try {
        const res = await fetch(`${API_BASE}/api/assistant`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg }),
        });

        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        appendChatMsg('bot', data.reply);
    } catch (e) {
        // 離線時顯示本地提示
        if (!navigator.onLine) {
            appendChatMsg('bot', '📴 目前離線，無法連線到 AI 助手。您的行程資料已本地儲存，上線後可繼續使用。');
        } else {
            appendChatMsg('bot', `⚠️ 錯誤: ${e.message}`);
        }
    } finally {
        hideLoading();
    }
}

function appendChatMsg(role, text) {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = `chat-msg ${role}`;
    div.innerHTML = `
        <div class="msg-avatar">${role === 'user' ? '👤' : '🤖'}</div>
        <div class="msg-bubble">${text.replace(/\n/g, '<br>')}</div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

// ============================================================
// PWA - Service Worker Registration
// ============================================================

if ('serviceWorker' in navigator) {
    window.addEventListener('load', async () => {
        try {
            const registration = await navigator.serviceWorker.register('/static/sw.js', {
                scope: '/',
            });
            console.log('[PWA] Service Worker registered:', registration.scope);

            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;
                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        showUpdateNotification();
                    }
                });
            });
        } catch (error) {
            console.error('[PWA] Service Worker registration failed:', error);
        }
    });
}

// Offline status indicator
let isOnline = navigator.onLine;
navigator.addEventListener('online', updateOnlineStatus);
navigator.addEventListener('offline', updateOnlineStatus);

function updateOnlineStatus() {
    isOnline = navigator.onLine;
    const indicator = document.getElementById('onlineStatus');
    if (!indicator) return;

    if (isOnline) {
        indicator.textContent = '🟢 線上';
        indicator.style.color = '#10B981';
    } else {
        indicator.textContent = '🔴 離線';
        indicator.style.color = '#EF4444';
    }
}

// Offline Banner (top bar)
function updateOfflineBanner() {
    const banner = document.getElementById('offlineBanner');
    const queueCount = document.getElementById('queueCount');

    if (!navigator.onLine) {
        banner.style.display = 'flex';
        SyncQueue.getQueue().then(queue => {
            queueCount.textContent = queue.length > 0 ? `(${queue.length} 筆待同步)` : '';
        });
    } else {
        banner.style.display = 'none';
    }
}

// Initial offline check
updateOfflineBanner();

// PWA Install Prompt
let deferredPrompt;
if ('BeforeInstallPromptEvent' in window) {
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        showInstallBanner();
    });
}

function showInstallBanner() {
    const existing = document.querySelector('.install-banner');
    if (existing) return;

    const banner = document.createElement('div');
    banner.className = 'install-banner';
    banner.innerHTML = `
        <span>📱 安裝為 App</span>
        <button onclick="installPWA()">安裝</button>
        <button onclick="dismissInstallBanner()" style="background:transparent;color:white;border:1px solid white;">稍後</button>
    `;
    document.body.appendChild(banner);
}

async function installPWA() {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    console.log(`[PWA] User choice: ${outcome}`);
    deferredPrompt = null;
    document.querySelector('.install-banner')?.remove();
}

function dismissInstallBanner() {
    document.querySelector('.install-banner')?.remove();
}

// Show update available notification
function showUpdateNotification() {
    const btn = document.createElement('button');
    btn.textContent = '🔄 更新可用';
    btn.style.cssText = `
        position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
        padding: 10px 20px; background: #4F46E5; color: white; border: none;
        border-radius: 8px; cursor: pointer; z-index: 10000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;
    btn.addEventListener('click', async () => {
        const registration = await navigator.serviceWorker.getRegistration();
        if (registration.waiting) {
            registration.waiting.postMessage({ type: 'SKIP_WAITING' });
        }
        window.location.reload();
    });
    document.body.appendChild(btn);
}

// Background Sync registration
async function registerBackgroundSync() {
    try {
        const registration = await navigator.serviceWorker.ready;
        if ('sync' in registration) {
            await registration.sync.register('sync-trips');
        }
    } catch (error) {
        console.log('[PWA] Background Sync not available:', error);
    }
}

// Notification permission
async function requestNotificationPermission() {
    if ('Notification' in window) {
        const permission = await Notification.requestPermission();
        console.log('[PWA] Notification permission:', permission);
        return permission === 'granted';
    }
    return false;
}

// Offline trip queue
const offlineQueue = {
    storageKey: 'offline-trip-queue',

    async enqueue(request) {
        const queue = await this.getQueue();
        queue.push({
            ...request,
            timestamp: Date.now(),
            id: crypto.randomUUID(),
        });
        localStorage.setItem(this.storageKey, JSON.stringify(queue));
        await registerBackgroundSync();
    },

    async getQueue() {
        const data = localStorage.getItem(this.storageKey);
        return data ? JSON.parse(data) : [];
    },

    async processQueue() {
        const queue = await this.getQueue();
        if (queue.length === 0) return;

        const processed = [];
        for (const item of queue) {
            try {
                const res = await fetch(item.url, {
                    method: item.method,
                    headers: { 'Content-Type': 'application/json' },
                    body: item.body,
                });
                if (res.ok) {
                    processed.push(item.id);
                }
            } catch (error) {
                console.error('[PWA] Failed to sync:', item.url, error);
            }
        }

        const remaining = queue.filter(item => !processed.includes(item.id));
        localStorage.setItem(this.storageKey, JSON.stringify(remaining));
        return { processed: processed.length, remaining: remaining.length };
    },
};

// Auto-process queue when coming back online
navigator.addEventListener('online', () => {
    offlineQueue.processQueue();
});

// ============================================================
// Expense Tracker
// ============================================================

function initExpenses() {
    const form = document.getElementById('expense-form');
    if (form) {
        form.addEventListener('submit', handleExpenseSubmit);
    }
    loadExpenses();
}

async function loadExpenses() {
    const tripSelect = document.getElementById('expense-trip');
    if (!tripSelect) return;

    // 載入行程列表到下拉選單
    try {
        const trips = await TripCache.getAll();
        tripSelect.innerHTML = '<option value="">選擇行程</option>';
        trips.forEach(trip => {
            const option = document.createElement('option');
            option.value = trip.id;
            option.textContent = `${trip.destination} (${trip.days}天)`;
            tripSelect.appendChild(option);
        });
    } catch (e) {
        console.error('載入行程失敗', e);
    }

    // 載入費用列表
    renderExpenseList();
}

async function handleExpenseSubmit(e) {
    e.preventDefault();
    const tripId = document.getElementById('expense-trip').value;
    const category = document.getElementById('expense-category').value;
    const amount = parseFloat(document.getElementById('expense-amount').value);
    const note = document.getElementById('expense-note').value;

    if (!tripId || !category || isNaN(amount)) {
        alert('請填寫完整資訊');
        return;
    }

    const expense = {
        trip_id: tripId,
        category,
        amount,
        note,
        date: new Date().toISOString().split('T')[0],
    };

    try {
        // 離線時直接存入 IndexedDB
        if (!navigator.onLine) {
            await ExpenseStore.add(expense);
            renderExpenseList();
            resetExpenseForm();
            return;
        }

        // 線上時呼叫 API
        const res = await fetch(`${API_BASE}/api/expenses`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                trip_id: tripId,
                category,
                description: note,
                amount,
                currency: 'TWD',
                date: expense.date,
            }),
        });

        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();

        // 同時存入本地 IndexedDB
        await ExpenseStore.add({ ...expense, id: data.expense.id });

        renderExpenseList();
        resetExpenseForm();
    } catch (e) {
        // API 失敗時存入離線佇列
        await ExpenseStore.add(expense);
        await SyncQueue.enqueue({
            type: 'add_expense',
            url: `${API_BASE}/api/expenses`,
            method: 'POST',
            body: {
                trip_id: tripId,
                category,
                description: note,
                amount,
                currency: 'TWD',
                date: expense.date,
            },
        });
        renderExpenseList();
        resetExpenseForm();
    }
}

async function renderExpenseList() {
    const listEl = document.getElementById('expense-list');
    if (!listEl) return;

    const tripId = document.getElementById('expense-trip')?.value;
    let expenses = [];

    if (tripId) {
        expenses = await ExpenseStore.getByTrip(tripId);
    } else {
        expenses = await dbGetAll('expenses');
    }

    const total = expenses.reduce((sum, e) => sum + (parseFloat(e.amount) || 0), 0);
    const budget = tripId ? await BudgetStore.get(tripId) : 0;

    if (expenses.length === 0) {
        listEl.innerHTML = '<p class="empty-state">尚無費用記錄</p>';
        renderCategoryChart(tripId);
        return;
    }

    let summaryHtml = '';
    if (budget > 0) {
        const remaining = budget - total;
        const pct = Math.min((total / budget) * 100, 100);
        const barColor = remaining < 0 ? '#ef4444' : pct > 80 ? '#f59e0b' : '#22c55e';
        summaryHtml = `
            <div class="budget-summary">
                <div class="budget-info">
                    <span>預算: <strong>${budget.toFixed(2)} TWD</strong></span>
                    <span>已花費: <strong>${total.toFixed(2)} TWD</strong></span>
                    <span>剩餘: <strong style="color: ${remaining < 0 ? '#ef4444' : '#22c55e'}">${remaining.toFixed(2)} TWD</strong></span>
                </div>
                <div class="budget-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${pct}%; background: ${barColor};"></div>
                    </div>
                    <span class="progress-text">${pct.toFixed(1)}%</span>
                </div>
            </div>
        `;
    }

    listEl.innerHTML = `
        ${summaryHtml}
        <div class="expense-summary">
            <span>總計: <strong>${total.toFixed(2)} TWD</strong></span>
            <span>共 ${expenses.length} 筆</span>
        </div>
        ${expenses.map(e => `
            <div class="expense-item" data-id="${e.id}">
                <div class="expense-info">
                    <span class="expense-category">${e.category}</span>
                    <span class="expense-date">${e.date}</span>
                    ${e.note ? `<span class="expense-note">${e.note}</span>` : ''}
                </div>
                <div class="expense-amount">
                    <span>${e.amount.toFixed(2)} TWD</span>
                    <button class="delete-expense-btn" onclick="deleteExpense('${e.id}')">🗑️</button>
                </div>
            </div>
        `).join('')}
    `;

    renderCategoryChart(tripId);
}

async function deleteExpense(id) {
    if (!confirm('確定要刪除此筆費用嗎？')) return;

    try {
        await ExpenseStore.remove(id);
        renderExpenseList();
    } catch (e) {
        alert('刪除失敗: ' + e.message);
    }
}

function resetExpenseForm() {
    document.getElementById('expense-category').value = '';
    document.getElementById('expense-amount').value = '';
    document.getElementById('expense-note').value = '';
}

// ============================================================
// Budget Management (Phase 3)
// ============================================================

let categoryChart = null;

function initBudget() {
    const budgetTrip = document.getElementById('budget-trip');
    const btnSetBudget = document.getElementById('btn-set-budget');

    if (budgetTrip) {
        // 載入行程列表到預算下拉選單
        TripCache.getAll().then(trips => {
            budgetTrip.innerHTML = '<option value="">選擇行程</option>';
            trips.forEach(trip => {
                const option = document.createElement('option');
                option.value = trip.id;
                option.textContent = `${trip.destination} (${trip.days}天)`;
                budgetTrip.appendChild(option);
            });
        });

        budgetTrip.addEventListener('change', () => {
            loadBudget(budgetTrip.value);
            renderExpenseList();
            renderCategoryChart(budgetTrip.value);
        });
    }

    if (btnSetBudget) {
        btnSetBudget.addEventListener('click', handleSetBudget);
    }

    // 同步 expense-trip 和 budget-trip
    const expenseTrip = document.getElementById('expense-trip');
    if (expenseTrip) {
        expenseTrip.addEventListener('change', () => {
            if (budgetTrip) budgetTrip.value = expenseTrip.value;
            loadBudget(expenseTrip.value);
            renderCategoryChart(expenseTrip.value);
        });
    }
}

async function handleSetBudget() {
    const tripId = document.getElementById('budget-trip').value;
    const amount = parseFloat(document.getElementById('budget-amount').value);

    if (!tripId || isNaN(amount) || amount <= 0) {
        alert('請選擇行程並輸入有效預算');
        return;
    }

    try {
        await BudgetStore.set(tripId, amount);
        if (navigator.onLine) {
            await fetch(`${API_BASE}/api/budget`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ trip_id: tripId, amount }),
            });
        }
        loadBudget(tripId);
        renderExpenseList();
        document.getElementById('budget-amount').value = '';
    } catch (e) {
        alert('設定預算失敗: ' + e.message);
    }
}

async function loadBudget(tripId) {
    if (!tripId) return;
    const budget = await BudgetStore.get(tripId);
    // 更新預算顯示在 expense-summary 中
    renderExpenseList();
}

// 分類圖表 (Chart.js)
async function renderCategoryChart(tripId) {
    const canvas = document.getElementById('category-chart');
    if (!canvas) return;

    const categories = tripId
        ? await ExpenseStore.getCategories(tripId)
        : await ExpenseStore.getCategories(null);

    const labels = Object.keys(categories);
    const data = Object.values(categories);

    if (labels.length === 0) {
        // 清空圖表
        if (categoryChart) {
            categoryChart.destroy();
            categoryChart = null;
        }
        canvas.parentElement.innerHTML = '<h3>花費分類</h3><p class="empty-state">尚無資料</p>';
        return;
    }

    // 移除舊的 canvas 並重新建立
    canvas.remove();
    const newCanvas = document.createElement('canvas');
    newCanvas.id = 'category-chart';
    canvas.parentElement.appendChild(newCanvas);

    const colors = [
        '#6366f1', '#ec4899', '#f59e0b', '#22c55e', '#3b82f6',
        '#ef4444', '#8b5cf6', '#14b8a6', '#f97316', '#06b6d4'
    ];

    categoryChart = new Chart(newCanvas, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 2,
                borderColor: '#ffffff',
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#374151',
                        padding: 16,
                        font: { size: 13 }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `${ctx.label}: ${ctx.raw.toFixed(2)} TWD`
                    }
                }
            }
        }
    });
}

// ============================================================
// Utilities
// ============================================================

function showLoading() {
    document.getElementById('loadingOverlay').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.add('hidden');
}

function debounce(fn, delay) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}
