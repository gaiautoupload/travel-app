"""
自助旅遊 App - FastAPI Backend
整合 Ollama (Qwen3.6 26B) + OpenStreetMap + 即時匯率
"""

import os
import json
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import datetime

from itinerary import (
    init_db, plan_itinerary,
    create_trip, get_trip, list_trips, update_trip, delete_trip, export_trip_json,
    TripPlanRequest, TripResponse, TripUpdate
)

# ============================================================
# Config
# ============================================================

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.6:27b")

# 匯率 API (免費)
EXCHANGE_API = "https://open.er-api.com/v6/latest/TWD"

# OSRM 公開路由服務
OSRM_BASE = "https://router.project-osrm.org/route/v1"
# Nominatim 地理編碼
NOMINATIM_BASE = "https://nominatim.openstreetmap.org"

# ============================================================
# Request/Response Models
# ============================================================

class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "zh-TW"
    target_lang: str = "en"

class CurrencyRequest(BaseModel):
    amount: float
    from_currency: str = "TWD"
    to_currency: str = "USD"

class RouteRequest(BaseModel):
    start: str
    end: str
    mode: str = "foot"  # foot, bike, car

class GeoRequest(BaseModel):
    query: str
    country_codes: Optional[str] = None

class FoodRequest(BaseModel):
    location: str
    cuisine: Optional[str] = None
    budget: Optional[str] = None
    count: int = 5

# ============================================================
# Ollama Helper
# ============================================================

async def call_ollama(prompt: str, system: str = "") -> str:
    """
    呼叫 Ollama 取得回應
    使用長 timeout (600s) 來處理模型冷啟動載入時間
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx": 8192,
        }
    }
    if system:
        payload["system"] = system

    async with httpx.AsyncClient(timeout=600.0) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "").strip()
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail=f"無法連線到 Ollama ({OLLAMA_BASE_URL})。請確認 Ollama 正在執行。"
            )
        except httpx.ReadTimeout:
            raise HTTPException(
                status_code=504,
                detail="Ollama 回應超時。可能是模型正在載入中，請稍後再試。"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ollama 錯誤: {str(e)}")


async def warmup_ollama() -> bool:
    """
    預熱 Ollama 模型，避免第一次請求時冷啟動超時
    發送一個簡單的測試請求來觸發模型載入
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": "Hi",
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code == 200
    except Exception as e:
        print(f"[Warmup] Ollama 預熱失敗: {e}")
        return False

# ============================================================
# App Setup (放在最後，因為 lifespan 需要上面的函數)
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """伺服器啟動時初始化資料庫並預熱模型"""
    print("[Startup] 初始化資料庫...")
    init_db()
    print("[Startup] ✓ 資料庫就緒")

    print(f"[Startup] 正在預熱 Ollama 模型: {OLLAMA_MODEL}...")
    success = await warmup_ollama()
    if success:
        print("[Startup] ✓ 模型預熱完成")
    else:
        print("[Startup] ✗ 模型預熱失敗，第一次請求時會自動載入")
    yield
    print("[Shutdown] 伺服器關閉")

app = FastAPI(title="自助旅遊助手", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Warmup Endpoint
# ============================================================

@app.post("/api/warmup")
async def warmup():
    """手動觸發模型預熱"""
    success = await warmup_ollama()
    return {
        "status": "warmed_up" if success else "failed",
        "model": OLLAMA_MODEL,
    }

# ============================================================
# 1. 翻譯 API
# ============================================================

@app.post("/api/translate")
async def translate(req: TranslateRequest):
    """使用 Qwen3.6 進行翻譯"""
    system_prompt = f"""你是一位專業的翻譯員。請將以下文字從 {req.source_lang} 翻譯成 {req.target_lang}。
只輸出翻譯結果，不要加任何說明或額外文字。
保持原文的語氣和風格。"""

    result = await call_ollama(req.text, system_prompt)
    return {
        "original": req.text,
        "source_lang": req.source_lang,
        "target_lang": req.target_lang,
        "translated": result,
    }

# ============================================================
# 2. 匯率 API
# ============================================================

@app.post("/api/currency")
async def currency_convert(req: CurrencyRequest):
    """即時匯率轉換"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(EXCHANGE_API)
            resp.raise_for_status()
            data = resp.json()
            rates = data.get("rates", {})

            if req.from_currency not in rates:
                raise HTTPException(400, detail=f"不支援的貨幣: {req.from_currency}")
            if req.to_currency not in rates:
                raise HTTPException(400, detail=f"不支援的貨幣: {req.to_currency}")

            # 透過 TWD 為基準計算
            if req.from_currency == "TWD":
                result = req.amount / rates[req.to_currency]
            elif req.to_currency == "TWD":
                result = req.amount * rates[req.from_currency]
            else:
                # 交叉匯率
                in_twd = req.amount * rates[req.from_currency]
                result = in_twd / rates[req.to_currency]

            return {
                "amount": req.amount,
                "from": req.from_currency,
                "to": req.to_currency,
                "result": round(result, 2),
                "rate_info": f"1 {req.from_currency} = {round(rates.get(req.from_currency, 0)/rates.get(req.to_currency, 1), 4)} {req.to_currency}",
                "timestamp": data.get("time_last_update_utc", ""),
            }
        except httpx.HTTPError as e:
            raise HTTPException(502, detail=f"匯率 API 錯誤: {str(e)}")

@app.get("/api/currencies")
async def get_currencies():
    """取得支援的貨幣列表"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(EXCHANGE_API)
        data = resp.json()
        return {"currencies": list(data.get("rates", {}).keys())}

# ============================================================
# 3. 路線規劃 API
# ============================================================

@app.post("/api/geocode")
async def geocode(req: GeoRequest):
    """將地址轉為座標 (Nominatim)"""
    params = {
        "q": req.query,
        "format": "json",
        "limit": 1,
        "accept-language": "zh-TW",
    }
    if req.country_codes:
        params["countrycodes"] = req.country_codes

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{NOMINATIM_BASE}/search", params=params)
        data = resp.json()
        if not data:
            raise HTTPException(404, detail="找不到該地址")
        loc = data[0]
        return {
            "name": loc["display_name"],
            "lat": float(loc["lat"]),
            "lon": float(loc["lon"]),
        }

@app.post("/api/route")
async def get_route(req: RouteRequest):
    """
    查詢路線 (OSRM)
    先 geocode 起終點，再查詢路線
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        start_resp = await client.get(f"{NOMINATIM_BASE}/search", params={
            "q": req.start, "format": "json", "limit": 1, "accept-language": "zh-TW"
        })
        start_data = start_resp.json()
        if not start_data:
            raise HTTPException(404, detail=f"找不到起點: {req.start}")

        end_resp = await client.get(f"{NOMINATIM_BASE}/search", params={
            "q": req.end, "format": "json", "limit": 1, "accept-language": "zh-TW"
        })
        end_data = end_resp.json()
        if not end_data:
            raise HTTPException(404, detail=f"找不到終點: {req.end}")

    s_lon = float(start_data[0]["lon"])
    s_lat = float(start_data[0]["lat"])
    e_lon = float(end_data[0]["lon"])
    e_lat = float(end_data[0]["lat"])

    modes = {"foot": "foot", "bike": "bike", "car": "car"}
    mode = modes.get(req.mode, "foot")

    url = f"{OSRM_BASE}/{mode}/{s_lon},{s_lat};{e_lon},{e_lat}"
    params = {"overview": "full", "steps": "true"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        data = resp.json()

    if data.get("code") != "Ok":
        raise HTTPException(400, detail="無法規劃路線")

    route = data["routes"][0]
    steps = []
    for leg in route.get("legs", []):
        for step in leg.get("steps", []):
            steps.append({
                "instruction": step.get("maneuver", {}).get("instruction", ""),
                "distance": step.get("distance", 0),
                "duration": step.get("duration", 0),
            })

    return {
        "start": start_data[0]["display_name"],
        "end": end_data[0]["display_name"],
        "distance_km": round(route["distance"] / 1000, 2),
        "duration_min": round(route["duration"] / 60, 1),
        "mode": mode,
        "steps": steps[:20],
    }

# ============================================================
# 4. 美食推薦 API
# ============================================================

@app.post("/api/food")
async def food_recommend(req: FoodRequest):
    """使用 Qwen3.6 推薦在地美食"""
    system_prompt = """你是一位旅遊美食專家。請根據使用者的位置和偏好推薦美食。
請以 JSON 格式回傳，格式如下：
[
  {"name": "餐廳名稱", "cuisine": "菜系", "description": "推薦原因", "price_range": "$$$", "highlight": "招牌菜"},
  ...
]
只輸出 JSON，不要其他文字。"""

    prompt = f"""請推薦 {req.location} 的美食，共 {req.count} 間。"""
    if req.cuisine:
        prompt += f"\n偏好菜系: {req.cuisine}"
    if req.budget:
        prompt += f"\n預算範圍: {req.budget}"
    prompt += "\n\n請用繁體中文回答。"

    result = await call_ollama(prompt, system_prompt)

    try:
        start = result.find("[")
        end = result.rfind("]") + 1
        if start != -1 and end != 0:
            foods = json.loads(result[start:end])
            return {"location": req.location, "foods": foods, "count": len(foods)}
        else:
            return {"location": req.location, "foods_raw": result}
    except json.JSONDecodeError:
        return {"location": req.location, "foods_raw": result}

# ============================================================
# 5. 旅行助手 (綜合 Agent)
# ============================================================

@app.post("/api/assistant")
async def travel_assistant(message: dict):
    """綜合旅行助手 - 回答任何旅遊相關問題"""
    user_msg = message.get("message", "")
    system_prompt = """你是一位專業的自助旅遊助手。
你可以幫助規劃行程、推薦景點、解答旅遊問題。
回答要實用、具體、有幫助。
用繁體中文回答。
如果涉及安全問題，請提醒使用者注意安全。"""

    result = await call_ollama(user_msg, system_prompt)
    return {"reply": result}

# ============================================================
# 6. 行程規劃引擎 (Phase 1)
# ============================================================

@app.post("/api/itinerary/plan")
async def plan_trip(req: TripPlanRequest):
    """
    AI 行程規劃
    根據目的地、天數、興趣、預算生成完整行程
    """
    itinerary_data = await plan_itinerary(req, call_ollama)

    if "error" in itinerary_data:
        return JSONResponse(
            status_code=500,
            content={"error": itinerary_data["error"]}
        )

    trip_data = {
        "title": req.title or f"{req.destination} {req.days}日遊",
        "destination": req.destination,
        "start_date": req.start_date or "",
        "end_date": "",
        "days": req.days,
        "interests": req.interests or [],
        "budget": req.budget or "",
        "itinerary": itinerary_data,
        "tips": itinerary_data.get("tips", ""),
    }

    trip_id = create_trip(trip_data)

    return {
        "id": trip_id,
        "title": trip_data["title"],
        "destination": req.destination,
        "days": req.days,
        "itinerary": itinerary_data,
        "tips": trip_data["tips"],
    }

@app.get("/api/itinerary")
async def get_trip_list(destination: Optional[str] = None, limit: int = 20):
    """列出所有行程"""
    trips = list_trips(destination=destination, limit=limit)
    return {"trips": trips, "count": len(trips)}

@app.get("/api/itinerary/{trip_id}")
async def get_trip_detail(trip_id: str):
    """取得行程詳情"""
    trip = get_trip(trip_id)
    if not trip:
        raise HTTPException(404, detail="找不到該行程")
    return trip

@app.put("/api/itinerary/{trip_id}")
async def update_trip_detail(trip_id: str, updates: TripUpdate):
    """更新行程"""
    success = update_trip(trip_id, updates.model_dump(exclude_none=True))
    if not success:
        raise HTTPException(404, detail="找不到該行程")
    return {"status": "updated", "id": trip_id}

@app.delete("/api/itinerary/{trip_id}")
async def delete_trip_detail(trip_id: str):
    """刪除行程"""
    success = delete_trip(trip_id)
    if not success:
        raise HTTPException(404, detail="找不到該行程")
    return {"status": "deleted", "id": trip_id}

@app.get("/api/itinerary/{trip_id}/export")
async def export_trip(trip_id: str):
    """匯出行程為 JSON"""
    data = export_trip_json(trip_id)
    if not data:
        raise HTTPException(404, detail="找不到該行程")
    return JSONResponse(
        content=json.loads(data),
        headers={"Content-Disposition": f"attachment; filename=trip-{trip_id}.json"}
    )

# ============================================================
# Static Files & Frontend
# ============================================================

static_dir = os.path.join(os.path.dirname(__file__), "static")

@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join(static_dir, "index.html"))

if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")

# PWA manifest - 讓瀏覽器能安裝為 App
@app.get("/manifest.json")
async def get_manifest():
    return FileResponse(
        os.path.join(static_dir, "manifest.json"),
        media_type="application/manifest+json",
        headers={"Cache-Control": "public, max-age=86400"}
    )

# Service Worker 需要從根路徑可存取
@app.get("/sw.js")
async def get_service_worker():
    return FileResponse(
        os.path.join(static_dir, "sw.js"),
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"}
    )

# ============================================================
# Health Check
# ============================================================

class ExpenseRequest(BaseModel):
    trip_id: str
    category: str
    description: str
    amount: float
    currency: str = "TWD"
    date: Optional[str] = None

class ExpenseDeleteRequest(BaseModel):
    id: str

class BudgetRequest(BaseModel):
    trip_id: str
    amount: float

# ============================================================
# 7. 費用記錄 API (Phase 2 - PWA)
# ============================================================

@app.post("/api/expenses")
async def add_expense(req: ExpenseRequest):
    """新增費用記錄 (離線可用 - 前端 IndexedDB 儲存)"""
    expense = {
        "id": req.trip_id + "-" + datetime.now().strftime("%Y%m%d%H%M%S"),
        "trip_id": req.trip_id,
        "category": req.category,
        "description": req.description,
        "amount": req.amount,
        "currency": req.currency,
        "date": req.date or datetime.now().strftime("%Y-%m-%d"),
        "created_at": datetime.now().isoformat(),
    }
    # 前端會透過 IndexedDB 儲存，這裡只回傳確認
    return {"status": "ok", "expense": expense}

@app.get("/api/expenses/{trip_id}")
async def get_expenses(trip_id: str):
    """取得行程的所有費用 (離線時由前端 IndexedDB 提供)"""
    # 實際應用中會從資料庫讀取，這裡回傳空陣列讓前端使用本地資料
    return {"expenses": [], "total": 0}

@app.delete("/api/expenses")
async def delete_expense(req: ExpenseDeleteRequest):
    """刪除費用記錄"""
    return {"status": "deleted", "id": req.id}

# ============================================================
# 8. 預算管理 API (Phase 3)
# ============================================================

@app.post("/api/budget")
async def set_budget(req: BudgetRequest):
    """設定行程預算"""
    return {"status": "ok", "trip_id": req.trip_id, "budget": req.amount}

@app.get("/api/budget/{trip_id}")
async def get_budget(trip_id: str):
    """取得行程預算"""
    return {"trip_id": trip_id, "budget": 0}

@app.delete("/api/budget/{trip_id}")
async def delete_budget(trip_id: str):
    """刪除行程預算"""
    return {"status": "deleted", "trip_id": trip_id}

# ============================================================
# Health Check
# ============================================================

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "ollama_model": OLLAMA_MODEL,
        "ollama_url": OLLAMA_BASE_URL,
        "time": datetime.now().isoformat(),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
