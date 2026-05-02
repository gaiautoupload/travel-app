"""
Travel App Phase 2 - PWA Offline Mode Tests
Tests for expense API endpoints and offline functionality
"""
import sys
import os
import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import app

@pytest.fixture
def transport():
    return ASGITransport(app=app, raise_app_exceptions=False)

@pytest.fixture
def client(transport):
    return AsyncClient(transport=transport, base_url="http://test")

# ==================== Expense API Tests ====================

class TestExpenseAPI:
    """測試費用記錄 API 端點"""

    @pytest.mark.asyncio
    async def test_add_expense_success(self, client):
        """測試新增費用成功"""
        res = await client.post("/api/expenses", json={
            "trip_id": "test-trip-001",
            "category": "餐飲",
            "description": "午餐",
            "amount": 350.0,
            "currency": "TWD",
            "date": "2026-05-02",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["expense"]["trip_id"] == "test-trip-001"
        assert data["expense"]["category"] == "餐飲"
        assert data["expense"]["amount"] == 350.0

    @pytest.mark.asyncio
    async def test_add_expense_no_date(self, client):
        """測試新增費用不指定日期，使用今天"""
        res = await client.post("/api/expenses", json={
            "trip_id": "test-trip-001",
            "category": "交通",
            "description": "計程車",
            "amount": 200.0,
            "currency": "TWD",
        })
        assert res.status_code == 200
        data = res.json()
        assert "date" in data["expense"]

    @pytest.mark.asyncio
    async def test_add_expense_missing_fields(self, client):
        """測試新增費用缺少必填欄位"""
        res = await client.post("/api/expenses", json={
            "trip_id": "test-trip-001",
        })
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_add_expense_negative_amount(self, client):
        """測試新增費用金額為負數"""
        res = await client.post("/api/expenses", json={
            "trip_id": "test-trip-001",
            "category": "餐飲",
            "description": "晚餐",
            "amount": -100.0,
            "currency": "TWD",
        })
        # API 接受負數（退款情境），但前端應驗證
        assert res.status_code == 200

    @pytest.mark.asyncio
    async def test_get_expenses_by_trip(self, client):
        """測試取得行程費用"""
        res = await client.get("/api/expenses/test-trip-001")
        assert res.status_code == 200
        data = res.json()
        assert "expenses" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_delete_expense(self, client):
        """測試刪除費用"""
        import json as json_module
        res = await client.request(
            "DELETE",
            "/api/expenses",
            content=json_module.dumps({"id": "test-expense-001"}),
            headers={"Content-Type": "application/json"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "deleted"
        assert data["id"] == "test-expense-001"

    @pytest.mark.asyncio
    async def test_delete_expense_missing_id(self, client):
        """測試刪除費用缺少 ID"""
        import json as json_module
        res = await client.request(
            "DELETE",
            "/api/expenses",
            content=json_module.dumps({}),
            headers={"Content-Type": "application/json"},
        )
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_expense_with_different_currency(self, client):
        """測試不同幣別"""
        res = await client.post("/api/expenses", json={
            "trip_id": "test-trip-001",
            "category": "購物",
            "description": "紀念品",
            "amount": 5000.0,
            "currency": "JPY",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["expense"]["currency"] == "JPY"

# ==================== Health Check Tests ====================

class TestHealthCheck:
    """測試健康檢查端點"""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """測試 health 端點"""
        res = await client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert "ollama_model" in data
        assert "ollama_url" in data
        assert "time" in data

# ==================== Static File Tests ====================

class TestStaticFiles:
    """測試靜態檔案服務"""

    @pytest.mark.asyncio
    async def test_index_html(self, client):
        """測試首頁 HTML"""
        res = await client.get("/")
        assert res.status_code == 200
        assert b"<!DOCTYPE html>" in res.content

    @pytest.mark.asyncio
    async def test_manifest_json(self, client):
        """測試 PWA manifest"""
        res = await client.get("/static/manifest.json")
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Travel Planner"
        assert data["display"] == "standalone"
        assert "shortcuts" in data

    @pytest.mark.asyncio
    async def test_service_worker(self, client):
        """測試 Service Worker"""
        res = await client.get("/static/sw.js")
        assert res.status_code == 200
        assert b"serviceWorker" in res.content or b"cache" in res.content

    @pytest.mark.asyncio
    async def test_indexeddb_js(self, client):
        """測試 IndexedDB 模組"""
        res = await client.get("/static/indexeddb.js")
        assert res.status_code == 200
        assert b"IndexedDB" in res.content
        assert b"TripCache" in res.content
        assert b"ExpenseStore" in res.content
        assert b"SyncQueue" in res.content
        assert b"TranslationCache" in res.content

    @pytest.mark.asyncio
    async def test_app_js(self, client):
        """測試主應用程式"""
        res = await client.get("/static/app.js")
        assert res.status_code == 200
        assert b"serviceWorker" in res.content
        assert b"ExpenseStore" in res.content

    @pytest.mark.asyncio
    async def test_css(self, client):
        """測試 CSS 樣式"""
        res = await client.get("/static/style.css")
        assert res.status_code == 200
        assert b"offline-banner" in res.content
        assert b"install-banner" in res.content
        assert b"expense-item" in res.content

# ==================== PWA Feature Tests ====================

class TestPWAFeatures:
    """測試 PWA 功能"""

    @pytest.mark.asyncio
    async def test_manifest_has_shortcuts(self, client):
        """測試 manifest 包含快捷方式"""
        res = await client.get("/static/manifest.json")
        data = res.json()
        shortcuts = data["shortcuts"]
        assert len(shortcuts) >= 3
        names = [s["name"] for s in shortcuts]
        assert "行程規劃" in names
        assert "即時翻譯" in names
        assert "路線規劃" in names

    @pytest.mark.asyncio
    async def test_sw_has_cache_handling(self, client):
        """測試 Service Worker 包含快取處理"""
        res = await client.get("/static/sw.js")
        content = res.text
        assert "CACHE_NAME" in content
        assert "fetch" in content
        assert "caches" in content

    @pytest.mark.asyncio
    async def test_indexeddb_has_all_stores(self, client):
        """測試 IndexedDB 包含所有資料儲存"""
        res = await client.get("/static/indexeddb.js")
        content = res.text
        assert "'trips'" in content
        assert "'expenses'" in content
        assert "'syncQueue'" in content
        assert "'translations'" in content

    @pytest.mark.asyncio
    async def test_app_has_offline_detection(self, client):
        """測試應用程式包含離線偵測"""
        res = await client.get("/static/app.js")
        content = res.text
        assert "navigator.onLine" in content
        assert "updateOfflineBanner" in content
        assert "SyncQueue" in content

    @pytest.mark.asyncio
    async def test_app_has_pwa_install(self, client):
        """測試應用程式包含 PWA 安裝提示"""
        res = await client.get("/static/app.js")
        content = res.text
        assert "beforeinstallprompt" in content
        assert "installPWA" in content
        assert "showInstallBanner" in content

# ==================== Integration Tests ====================

class TestIntegration:
    """整合測試"""

    @pytest.mark.asyncio
    async def test_full_expense_workflow(self, client):
        """測試完整費用記錄流程"""
        # 1. 新增費用
        res1 = await client.post("/api/expenses", json={
            "trip_id": "integration-test",
            "category": "餐飲",
            "description": "早餐",
            "amount": 150.0,
            "currency": "TWD",
        })
        assert res1.status_code == 200

        # 2. 新增第二筆費用
        res2 = await client.post("/api/expenses", json={
            "trip_id": "integration-test",
            "category": "交通",
            "description": "地鐵",
            "amount": 80.0,
            "currency": "TWD",
        })
        assert res2.status_code == 200

        # 3. 取得費用列表
        res3 = await client.get("/api/expenses/integration-test")
        assert res3.status_code == 200

        # 4. 刪除費用
        import json as json_module
        res4 = await client.request(
            "DELETE",
            "/api/expenses",
            content=json_module.dumps({"id": res1.json()["expense"]["id"]}),
            headers={"Content-Type": "application/json"},
        )
        assert res4.status_code == 200

    @pytest.mark.asyncio
    async def test_all_static_files_accessible(self, client):
        """測試所有靜態檔案可存取"""
        files = [
            "/",
            "/static/manifest.json",
            "/static/sw.js",
            "/static/indexeddb.js",
            "/static/app.js",
            "/static/style.css",
        ]
        for path in files:
            res = await client.get(path)
            assert res.status_code == 200, f"Failed to load {path}"
