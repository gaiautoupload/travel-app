/* ============================================
   IndexedDB Offline Storage Layer
   離線行程快取、離線費用記錄、離線佇列
   ============================================ */

const DB_NAME = 'TravelAppDB';
const DB_VERSION = 2;

/**
 * 開啟 IndexedDB 連線
 */
function openDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onupgradeneeded = (event) => {
            const db = event.target.result;

            // 行程快取
            if (!db.objectStoreNames.contains('trips')) {
                const tripStore = db.createObjectStore('trips', { keyPath: 'id' });
                tripStore.createIndex('destination', 'destination', { unique: false });
                tripStore.createIndex('created_at', 'created_at', { unique: false });
            }

            // 離線費用記錄
            if (!db.objectStoreNames.contains('expenses')) {
                const expenseStore = db.createObjectStore('expenses', { keyPath: 'id' });
                expenseStore.createIndex('trip_id', 'trip_id', { unique: false });
                expenseStore.createIndex('date', 'date', { unique: false });
            }

            // 離線請求佇列
            if (!db.objectStoreNames.contains('syncQueue')) {
                const queueStore = db.createObjectStore('syncQueue', { keyPath: 'id' });
                queueStore.createIndex('timestamp', 'timestamp', { unique: false });
            }

            // 離線翻譯快取
            if (!db.objectStoreNames.contains('translations')) {
                const transStore = db.createObjectStore('translations', { keyPath: 'id' });
                transStore.createIndex('source', 'source', { unique: false });
                transStore.createIndex('lang_pair', 'lang_pair', { unique: false });
            }

            // 預算設定
            if (!db.objectStoreNames.contains('budgets')) {
                const budgetStore = db.createObjectStore('budgets', { keyPath: 'id' });
                budgetStore.createIndex('trip_id', 'trip_id', { unique: false });
            }
        };

        request.onsuccess = (event) => resolve(event.target.result);
        request.onerror = (event) => reject(event.target.error);
    });
}

/**
 * 通用 CRUD 操作
 */
async function dbPut(storeName, data) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(storeName, 'readwrite');
        const store = tx.objectStore(storeName);
        const request = store.put(data);
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

async function dbGet(storeName, id) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(storeName, 'readonly');
        const store = tx.objectStore(storeName);
        const request = store.get(id);
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

async function dbGetAll(storeName) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(storeName, 'readonly');
        const store = tx.objectStore(storeName);
        const request = store.getAll();
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

async function dbDelete(storeName, id) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(storeName, 'readwrite');
        const store = tx.objectStore(storeName);
        const request = store.delete(id);
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
    });
}

async function dbClear(storeName) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(storeName, 'readwrite');
        const store = tx.objectStore(storeName);
        const request = store.clear();
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
    });
}

/**
 * 行程快取操作
 */
const TripCache = {
    async save(trip) {
        await dbPut('trips', { ...trip, cached_at: new Date().toISOString() });
    },

    async get(id) {
        return await dbGet('trips', id);
    },

    async getAll() {
        return await dbGetAll('trips');
    },

    async remove(id) {
        await dbDelete('trips', id);
    },

    async getByDestination(destination) {
        const all = await this.getAll();
        return all.filter(t => t.destination?.toLowerCase().includes(destination.toLowerCase()));
    }
};

/**
 * 費用記錄操作
 */
const ExpenseStore = {
    async add(expense) {
        expense.id = expense.id || crypto.randomUUID();
        expense.date = expense.date || new Date().toISOString().split('T')[0];
        expense.created_at = new Date().toISOString();
        await dbPut('expenses', expense);
        return expense;
    },

    async getByTrip(tripId) {
        const all = await dbGetAll('expenses');
        return all.filter(e => e.trip_id === tripId);
    },

    async getTotalByTrip(tripId) {
        const expenses = await this.getByTrip(tripId);
        return expenses.reduce((sum, e) => sum + (parseFloat(e.amount) || 0), 0);
    },

    async remove(id) {
        await dbDelete('expenses', id);
    },

    async getCategories(tripId) {
        const expenses = await this.getByTrip(tripId);
        const cats = {};
        expenses.forEach(e => {
            const cat = e.category || '其他';
            cats[cat] = (cats[cat] || 0) + (parseFloat(e.amount) || 0);
        });
        return cats;
    }
};

/**
 * 預算設定儲存
 */
const BudgetStore = {
    async set(tripId, amount) {
        const existing = await dbGetAll('budgets');
        const old = existing.find(b => b.trip_id === tripId);
        if (old) {
            await dbUpdate('budgets', old.id, { amount });
        } else {
            await dbPut('budgets', {
                id: crypto.randomUUID(),
                trip_id: tripId,
                amount: parseFloat(amount),
                created_at: new Date().toISOString(),
            });
        }
    },

    async get(tripId) {
        const all = await dbGetAll('budgets');
        const b = all.find(b => b.trip_id === tripId);
        return b ? b.amount : 0;
    },

    async remove(tripId) {
        const all = await dbGetAll('budgets');
        const b = all.find(b => b.trip_id === tripId);
        if (b) await dbDelete('budgets', b.id);
    }
};

/**
 * 離線請求佇列
 */
const SyncQueue = {
    async enqueue(request) {
        const item = {
            id: crypto.randomUUID(),
            timestamp: Date.now(),
            retries: 0,
            maxRetries: 5,
            ...request
        };
        await dbPut('syncQueue', item);
        return item;
    },

    async dequeue() {
        const all = await dbGetAll('syncQueue');
        if (all.length === 0) return null;
        const item = all.sort((a, b) => a.timestamp - b.timestamp)[0];
        await dbDelete('syncQueue', item.id);
        return item;
    },

    async getAll() {
        return await dbGetAll('syncQueue');
    },

    async size() {
        const all = await this.getAll();
        return all.length;
    },

    async getQueue() {
        return await this.getAll();
    },

    async process() {
        let processed = 0;
        let failed = 0;

        while (true) {
            const item = await this.dequeue();
            if (!item) break;

            try {
                const res = await fetch(item.url, {
                    method: item.method || 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: item.body ? JSON.stringify(item.body) : undefined,
                });

                if (res.ok) {
                    processed++;
                    // 如果是行程規劃，快取結果
                    if (item.type === 'plan_trip' && item.body) {
                        const data = await res.json();
                        if (data.id) {
                            await TripCache.save(data);
                        }
                    }
                } else {
                    failed++;
                    // 重試：放回佇列
                    item.retries++;
                    if (item.retries < item.maxRetries) {
                        await this.enqueue(item);
                    }
                }
            } catch (e) {
                failed++;
                item.retries++;
                if (item.retries < item.maxRetries) {
                    await this.enqueue(item);
                }
            }
        }

        return { processed, failed };
    }
};

/**
 * 翻譯快取
 */
const TranslationCache = {
    async get(source, sourceLang, targetLang) {
        const id = `${sourceLang}-${targetLang}-${source.substring(0, 50)}`;
        const cached = await dbGet('translations', id);
        if (cached && (Date.now() - cached.timestamp) < 7 * 24 * 60 * 60 * 1000) {
            // 7 天內有效
            return cached.translated;
        }
        return null;
    },

    async put(source, sourceLang, targetLang, translated) {
        const id = `${sourceLang}-${targetLang}-${source.substring(0, 50)}`;
        await dbPut('translations', {
            id,
            source,
            translated,
            lang_pair: `${sourceLang}-${targetLang}`,
            timestamp: Date.now(),
        });
    }
};
