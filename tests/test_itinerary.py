"""
Phase 1 QA - 行程規劃引擎單元測試
"""
import os
import sys
import json
import pytest
import sqlite3
from unittest.mock import AsyncMock, patch, MagicMock

# 加入專案根目錄
sys.path.insert(0, os.path.dirname(__file__))

from itinerary import (
    init_db, get_db, plan_itinerary,
    create_trip, get_trip, list_trips, update_trip, delete_trip, export_trip_json,
    TripPlanRequest, TripUpdate,
    DB_PATH
)

# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    """每個測試使用臨時資料庫"""
    test_db = str(tmp_path / "test_travel.db")
    # 覆蓋 DB_PATH
    import itinerary
    original = itinerary.DB_PATH
    itinerary.DB_PATH = test_db
    init_db()
    yield
    itinerary.DB_PATH = original

@pytest.fixture
def sample_trip_data():
    return {
        "title": "東京5日遊",
        "destination": "東京",
        "start_date": "2026-06-01",
        "end_date": "2026-06-05",
        "days": 5,
        "interests": ["美食", "購物"],
        "budget": "中等",
        "itinerary": {
            "daily": [
                {
                    "day": 1,
                    "date": "2026-06-01",
                    "theme": "市區探索",
                    "activities": [
                        {"time": "09:00", "place": "淺草寺", "description": "參拜", "duration_min": 120, "cost_twd": 0},
                        {"time": "13:00", "place": "秋葉原", "description": "購物", "duration_min": 180, "cost_twd": 2000},
                    ],
                    "meals": [
                        {"type": "早餐", "recommendation": "淺草飯糰", "budget_twd": 300},
                        {"type": "午餐", "recommendation": "壽司", "budget_twd": 800},
                    ],
                    "notes": "第一天注意行李寄放"
                }
            ],
            "tips": "建議購買東京地鐵券",
            "total_budget_twd": 25000
        },
        "tips": "建議購買東京地鐵券",
    }

@pytest.fixture
def sample_plan_request():
    return TripPlanRequest(
        destination="東京",
        days=5,
        start_date="2026-06-01",
        interests=["美食", "購物"],
        budget="中等",
        travelers="兩個人",
        title="東京5日遊"
    )

# ============================================================
# Test: Database Initialization
# ============================================================

class TestDatabase:
    def test_init_db_creates_tables(self, tmp_path):
        """測試資料庫初始化建立表格"""
        test_db = str(tmp_path / "test.db")
        import itinerary
        original = itinerary.DB_PATH
        itinerary.DB_PATH = test_db
        
        init_db()
        conn = get_db()
        
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        
        assert "trips" in table_names
        assert "trip_daily" in table_names
        
        conn.close()
        itinerary.DB_PATH = original

    def test_init_db_idempotent(self, tmp_path):
        """測試重複初始化不會出錯"""
        test_db = str(tmp_path / "test.db")
        import itinerary
        original = itinerary.DB_PATH
        itinerary.DB_PATH = test_db
        
        init_db()
        init_db()  # 第二次應該不會出錯
        
        itinerary.DB_PATH = original

# ============================================================
# Test: Trip CRUD
# ============================================================

class TestTripCRUD:
    def test_create_trip(self, sample_trip_data):
        """測試建立行程"""
        trip_id = create_trip(sample_trip_data)
        
        assert trip_id is not None
        assert len(trip_id) == 8
        
        trip = get_trip(trip_id)
        assert trip is not None
        assert trip["title"] == "東京5日遊"
        assert trip["destination"] == "東京"
        assert trip["days"] == 5

    def test_get_trip_not_found(self):
        """測試取得不存在的行程"""
        result = get_trip("nonexistent")
        assert result is None

    def test_list_trips(self, sample_trip_data):
        """測試列出行程"""
        create_trip(sample_trip_data)
        create_trip({
            "title": "大阪3日遊",
            "destination": "大阪",
            "start_date": "2026-07-01",
            "end_date": "2026-07-03",
            "days": 3,
            "interests": [],
            "budget": "",
            "itinerary": {"daily": []},
            "tips": "",
        })
        
        trips = list_trips()
        assert len(trips) == 2
        
        tokyo_trips = list_trips(destination="東京")
        assert len(tokyo_trips) == 1
        assert tokyo_trips[0]["destination"] == "東京"

    def test_update_trip(self, sample_trip_data):
        """測試更新行程"""
        trip_id = create_trip(sample_trip_data)
        
        updates = {
            "title": "東京7日遊 (更新)",
            "days": 7,
            "budget": "豪華",
        }
        success = update_trip(trip_id, updates)
        assert success is True
        
        trip = get_trip(trip_id)
        assert trip["title"] == "東京7日遊 (更新)"
        assert trip["days"] == 7
        assert trip["budget"] == "豪華"

    def test_update_trip_not_found(self):
        """測試更新不存在的行程"""
        success = update_trip("nonexistent", {"title": "test"})
        assert success is False

    def test_delete_trip(self, sample_trip_data):
        """測試刪除行程"""
        trip_id = create_trip(sample_trip_data)
        
        success = delete_trip(trip_id)
        assert success is True
        
        trip = get_trip(trip_id)
        assert trip is None

    def test_delete_trip_not_found(self):
        """測試刪除不存在的行程"""
        success = delete_trip("nonexistent")
        assert success is False

    def test_create_trip_stores_daily_details(self, sample_trip_data):
        """測試建立行程時每日詳情也被儲存"""
        trip_id = create_trip(sample_trip_data)
        
        trip = get_trip(trip_id)
        assert len(trip["daily_details"]) == 1
        
        day1 = trip["daily_details"][0]
        assert day1["day_num"] == 1
        assert day1["theme"] == "市區探索"
        assert len(day1["activities"]) == 2
        assert len(day1["meals"]) == 2

    def test_update_trip_with_new_daily(self, sample_trip_data):
        """測試更新行程時替換每日詳情"""
        trip_id = create_trip(sample_trip_data)
        
        new_daily = [
            {
                "day": 1,
                "date": "2026-06-01",
                "theme": "新主題",
                "activities": [
                    {"time": "10:00", "place": "新地點", "description": "新活動", "duration_min": 60, "cost_twd": 500}
                ],
                "meals": [],
                "notes": ""
            },
            {
                "day": 2,
                "date": "2026-06-02",
                "theme": "第二天",
                "activities": [],
                "meals": [],
                "notes": ""
            }
        ]
        
        update_trip(trip_id, {"itinerary": {"daily": new_daily}})
        
        trip = get_trip(trip_id)
        assert len(trip["daily_details"]) == 2
        assert trip["daily_details"][0]["theme"] == "新主題"

# ============================================================
# Test: Export
# ============================================================

class TestExport:
    def test_export_trip_json(self, sample_trip_data):
        """測試匯出行程為 JSON"""
        trip_id = create_trip(sample_trip_data)
        
        json_str = export_trip_json(trip_id)
        assert json_str is not None
        
        data = json.loads(json_str)
        assert data["id"] == trip_id
        assert data["title"] == "東京5日遊"
        assert "daily_details" in data

    def test_export_nonexistent(self):
        """測試匯出不存在的行程"""
        result = export_trip_json("nonexistent")
        assert result is None

# ============================================================
# Test: Pydantic Models
# ============================================================

class TestModels:
    def test_trip_plan_request_valid(self):
        """測試有效的行程規劃請求"""
        req = TripPlanRequest(
            destination="東京",
            days=5,
            interests=["美食"],
            budget="中等"
        )
        assert req.destination == "東京"
        assert req.days == 5
        assert req.travelers == "一個人"  # 預設值

    def test_trip_plan_request_invalid_days(self):
        """測試天數超出範圍"""
        with pytest.raises(Exception):
            TripPlanRequest(destination="東京", days=0)
        
        with pytest.raises(Exception):
            TripPlanRequest(destination="東京", days=31)

    def test_trip_update_partial(self):
        """測試部分更新"""
        update = TripUpdate(title="新標題")
        assert update.title == "新標題"
        assert update.destination is None
        assert update.budget is None

# ============================================================
# Test: AI Planning (Mocked)
# ============================================================

class TestAIPlanning:
    @pytest.mark.asyncio
    async def test_plan_itinerary_success(self, sample_plan_request):
        """測試 AI 行程規劃成功"""
        mock_response = json.dumps({
            "daily": [
                {
                    "day": 1,
                    "date": "2026-06-01",
                    "theme": "市區探索",
                    "activities": [
                        {"time": "09:00", "place": "淺草寺", "description": "參拜", "duration_min": 120, "cost_twd": 0}
                    ],
                    "meals": [
                        {"type": "早餐", "recommendation": "飯糰", "budget_twd": 300}
                    ],
                    "notes": ""
                }
            ],
            "tips": "建議買地鐵券",
            "total_budget_twd": 20000
        })
        
        mock_call_ollama = AsyncMock(return_value=mock_response)
        result = await plan_itinerary(sample_plan_request, mock_call_ollama)
        
        assert "daily" in result
        assert len(result["daily"]) == 1
        assert result["tips"] == "建議買地鐵券"

    @pytest.mark.asyncio
    async def test_plan_itinerary_with_markdown_wrapper(self, sample_plan_request):
        """測試 AI 回傳包含 markdown 程式碼塊"""
        mock_response = "```json\n" + json.dumps({
            "daily": [],
            "tips": "test",
            "total_budget_twd": 0
        }) + "\n```"
        
        mock_call_ollama = AsyncMock(return_value=mock_response)
        result = await plan_itinerary(sample_plan_request, mock_call_ollama)
        
        assert "daily" in result

    @pytest.mark.asyncio
    async def test_plan_itinerary_invalid_json(self, sample_plan_request):
        """測試 AI 回傳無效 JSON"""
        mock_call_ollama = AsyncMock(return_value="這不是 JSON")
        result = await plan_itinerary(sample_plan_request, mock_call_ollama)
        
        assert "error" in result

    @pytest.mark.asyncio
    async def test_plan_itinerary_default_date(self, sample_plan_request):
        """測試未提供日期時使用預設值"""
        sample_plan_request.start_date = None
        mock_call_ollama = AsyncMock(return_value=json.dumps({
            "daily": [], "tips": "", "total_budget_twd": 0
        }))
        
        await plan_itinerary(sample_plan_request, mock_call_ollama)
        assert sample_plan_request.start_date is not None  # 應該被設定

# ============================================================
# Test: Edge Cases
# ============================================================

class TestEdgeCases:
    def test_empty_interests(self):
        """測試空興趣列表"""
        trip_id = create_trip({
            "title": "測試",
            "destination": "大阪",
            "start_date": "2026-07-01",
            "end_date": "2026-07-01",
            "days": 1,
            "interests": [],
            "budget": "",
            "itinerary": {"daily": []},
            "tips": "",
        })
        trip = get_trip(trip_id)
        assert trip["interests"] == []

    def test_unicode_content(self):
        """測試 Unicode 內容"""
        trip_id = create_trip({
            "title": "東京🗼大阪🏯京都⛩️",
            "destination": "日本",
            "start_date": "2026-07-01",
            "end_date": "2026-07-05",
            "days": 5,
            "interests": ["美食🍣", "購物🛍️"],
            "budget": "豪華",
            "itinerary": {"daily": []},
            "tips": "注意⚠️",
        })
        trip = get_trip(trip_id)
        assert "🗼" in trip["title"]

    def test_list_trips_limit(self, sample_trip_data):
        """測試列出行程的 limit 參數"""
        for i in range(5):
            create_trip({
                "title": f"行程{i}",
                "destination": "東京",
                "start_date": "2026-07-01",
                "end_date": "2026-07-01",
                "days": 1,
                "interests": [],
                "budget": "",
                "itinerary": {"daily": []},
                "tips": "",
            })
        
        trips = list_trips(limit=3)
        assert len(trips) == 3

    def test_update_with_empty_dict(self, sample_trip_data):
        """測試空更新"""
        trip_id = create_trip(sample_trip_data)
        success = update_trip(trip_id, {})
        assert success is False
