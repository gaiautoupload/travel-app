"""
行程規劃引擎 - Phase 1
提供 AI 行程規劃、行程 CRUD、匯出功能
"""

import os
import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field

# ============================================================
# Database Setup
# ============================================================

DB_PATH = os.path.join(os.path.dirname(__file__), "travel.db")

def get_db() -> sqlite3.Connection:
    """取得資料庫連線"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    """初始化資料庫"""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS trips (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            destination TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            days INTEGER NOT NULL,
            interests TEXT,
            budget TEXT,
            itinerary TEXT NOT NULL,
            tips TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS trip_daily (
            id TEXT PRIMARY KEY,
            trip_id TEXT NOT NULL,
            day_num INTEGER NOT NULL,
            date TEXT NOT NULL,
            theme TEXT,
            activities TEXT NOT NULL,
            meals TEXT,
            notes TEXT,
            FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE
        );
        
        CREATE INDEX IF NOT EXISTS idx_trips_destination ON trips(destination);
        CREATE INDEX IF NOT EXISTS idx_trip_daily_trip_id ON trip_daily(trip_id);
    """)
    conn.commit()
    conn.close()

# ============================================================
# Request/Response Models
# ============================================================

class TripPlanRequest(BaseModel):
    destination: str = Field(..., description="目的地")
    days: int = Field(..., ge=1, le=30, description="天數")
    start_date: Optional[str] = Field(None, description="開始日期 (YYYY-MM-DD)")
    interests: Optional[List[str]] = Field(None, description="興趣標籤")
    budget: Optional[str] = Field(None, description="預算等級: 省錢/中等/豪華")
    travelers: Optional[str] = Field("一個人", description="旅伴類型")
    title: Optional[str] = Field(None, description="行程標題")

class TripResponse(BaseModel):
    id: str
    title: str
    destination: str
    days: int
    itinerary: dict
    tips: Optional[str] = None
    created_at: str

class TripUpdate(BaseModel):
    title: Optional[str] = None
    destination: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    interests: Optional[List[str]] = None
    budget: Optional[str] = None
    itinerary: Optional[dict] = None
    tips: Optional[str] = None

# ============================================================
# Itinerary Planner (AI)
# ============================================================

async def plan_itinerary(req: TripPlanRequest, call_ollama) -> dict:
    """
    使用 AI 規劃完整行程
    
    回傳結構:
    {
        "daily": [
            {
                "day": 1,
                "date": "2026-05-10",
                "theme": "市區探索",
                "activities": [
                    {"time": "09:00", "place": "XXX", "description": "...", "duration_min": 120, "cost_twd": 0},
                    ...
                ],
                "meals": [
                    {"type": "早餐", "recommendation": "...", "budget_twd": 200},
                    ...
                ],
                "notes": "..."
            }
        ],
        "tips": "...",
        "total_budget_twd": 0
    }
    """
    if not req.start_date:
        req.start_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    end_date = (datetime.strptime(req.start_date, "%Y-%m-%d") + timedelta(days=req.days - 1)).strftime("%Y-%m-%d")
    
    interests_str = ", ".join(req.interests) if req.interests else "一般觀光"
    budget_str = req.budget or "中等"
    
    system_prompt = f"""你是一位專業的旅遊行程規劃師。
請為使用者規劃一個詳細的 {req.days} 天 {req.destination} 行程。

旅伴類型: {req.travelers}
興趣: {interests_str}
預算等級: {budget_str}
開始日期: {req.start_date} ~ {end_date}

請以 JSON 格式回傳，嚴格遵守以下格式：
{{
    "daily": [
        {{
            "day": 1,
            "date": "YYYY-MM-DD",
            "theme": "本日主題",
            "activities": [
                {{
                    "time": "HH:MM",
                    "place": "地點名稱",
                    "description": "活動說明",
                    "duration_min": 120,
                    "cost_twd": 0
                }}
            ],
            "meals": [
                {{"type": "早餐", "recommendation": "推薦", "budget_twd": 200}},
                {{"type": "午餐", "recommendation": "推薦", "budget_twd": 500}},
                {{"type": "晚餐", "recommendation": "推薦", "budget_twd": 800}}
            ],
            "notes": "注意事項"
        }}
    ],
    "tips": "整體旅行建議",
    "total_budget_twd": 15000
}}

要求:
1. 每天 3-5 個活動，時間合理分配
2. 包含交通建議和門票資訊
3. 考慮天氣和季節因素
4. 預算估算要實際
5. 用繁體中文
6. 只輸出 JSON，不要其他文字"""

    prompt = f"""請幫我規劃以下行程:
- 目的地: {req.destination}
- 天數: {req.days} 天
- 日期: {req.start_date} ~ {end_date}
- 興趣: {interests_str}
- 預算: {budget_str}
- 旅伴: {req.travelers}"""

    result = await call_ollama(prompt, system_prompt)
    
    try:
        start = result.find("{")
        end = result.rfind("}") + 1
        if start != -1 and end != 0:
            itinerary = json.loads(result[start:end])
            return itinerary
        else:
            return {"error": "AI 回傳格式異常", "raw": result}
    except json.JSONDecodeError as e:
        return {"error": f"JSON 解析失敗: {str(e)}", "raw": result}

# ============================================================
# CRUD Operations
# ============================================================

def create_trip(trip_data: dict) -> str:
    """建立行程並儲存到資料庫"""
    trip_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO trips (id, title, destination, start_date, end_date, days, interests, budget, itinerary, tips, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trip_id,
            trip_data.get("title", ""),
            trip_data.get("destination", ""),
            trip_data.get("start_date", ""),
            trip_data.get("end_date", ""),
            trip_data.get("days", 0),
            json.dumps(trip_data.get("interests", [])),
            trip_data.get("budget", ""),
            json.dumps(trip_data.get("itinerary", {})),
            trip_data.get("tips", ""),
            now,
            now
        ))
        
        # 儲存每日行程
        daily = trip_data.get("itinerary", {}).get("daily", [])
        for day in daily:
            day_id = str(uuid.uuid4())[:8]
            conn.execute("""
                INSERT INTO trip_daily (id, trip_id, day_num, date, theme, activities, meals, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                day_id, trip_id,
                day.get("day", 0),
                day.get("date", ""),
                day.get("theme", ""),
                json.dumps(day.get("activities", [])),
                json.dumps(day.get("meals", [])),
                day.get("notes", "")
            ))
        
        conn.commit()
        return trip_id
    finally:
        conn.close()

def get_trip(trip_id: str) -> Optional[dict]:
    """取得行程詳情"""
    conn = get_db()
    try:
        trip = conn.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
        if not trip:
            return None
        
        daily_rows = conn.execute(
            "SELECT * FROM trip_daily WHERE trip_id = ? ORDER BY day_num", (trip_id,)
        ).fetchall()
        
        result = dict(trip)
        result["itinerary"] = json.loads(result["itinerary"])
        result["interests"] = json.loads(result["interests"]) if result["interests"] else []
        result["daily_details"] = [dict(row) for row in daily_rows]
        
        for day in result["daily_details"]:
            day["activities"] = json.loads(day["activities"]) if day["activities"] else []
            day["meals"] = json.loads(day["meals"]) if day["meals"] else []
        
        return result
    finally:
        conn.close()

def list_trips(destination: Optional[str] = None, limit: int = 20) -> List[dict]:
    """列出行程"""
    conn = get_db()
    try:
        if destination:
            rows = conn.execute(
                "SELECT * FROM trips WHERE destination LIKE ? ORDER BY created_at DESC LIMIT ?",
                (f"%{destination}%", limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM trips ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        
        return [dict(row) for row in rows]
    finally:
        conn.close()

def update_trip(trip_id: str, updates: dict) -> bool:
    """更新行程"""
    conn = get_db()
    try:
        existing = conn.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
        if not existing:
            return False
        
        now = datetime.now().isoformat()
        fields = []
        values = []
        
        for key, value in updates.items():
            if value is not None and key != "itinerary":
                if key == "interests" and isinstance(value, list):
                    value = json.dumps(value)
                fields.append(f"{key} = ?")
                values.append(value)
        
        if "itinerary" in updates and updates["itinerary"] is not None:
            fields.append("itinerary = ?")
            values.append(json.dumps(updates["itinerary"]))
        
        if not fields:
            return False
        
        fields.append("updated_at = ?")
        values.append(now)
        values.append(trip_id)
        
        conn.execute(f"UPDATE trips SET {', '.join(fields)} WHERE id = ?", values)
        
        # 更新每日行程 (如果有)
        daily = updates.get("itinerary", {}).get("daily")
        if daily:
            conn.execute("DELETE FROM trip_daily WHERE trip_id = ?", (trip_id,))
            for day in daily:
                day_id = str(uuid.uuid4())[:8]
                conn.execute("""
                    INSERT INTO trip_daily (id, trip_id, day_num, date, theme, activities, meals, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    day_id, trip_id,
                    day.get("day", 0), day.get("date", ""), day.get("theme", ""),
                    json.dumps(day.get("activities", [])),
                    json.dumps(day.get("meals", [])),
                    day.get("notes", "")
                ))
        
        conn.commit()
        return True
    finally:
        conn.close()

def delete_trip(trip_id: str) -> bool:
    """刪除行程"""
    conn = get_db()
    try:
        cursor = conn.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def export_trip_json(trip_id: str) -> Optional[str]:
    """匯出行程為 JSON"""
    trip = get_trip(trip_id)
    if not trip:
        return None
    return json.dumps(trip, ensure_ascii=False, indent=2)
