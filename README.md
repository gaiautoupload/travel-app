# 🌍 自助旅遊助手 - 操作手冊

> 基於 Ollama (Qwen3.6 26B) + OpenStreetMap + 即時匯率的離線旅遊應用程式

---

## 📋 目錄

1. [系統需求](#系統需求)
2. [安裝步驟](#安裝步驟)
3. [啟動應用程式](#啟動應用程式)
4. [功能說明](#功能說明)
5. [冷啟動機制](#冷啟動機制)
6. [疑難排解](#疑難排解)
7. [API 文件](#api-文件)

---

## 系統需求

| 項目 | 需求 |
|------|------|
| 作業系統 | Windows 10/11, macOS, Linux |
| Python | 3.10 或以上 |
| Ollama | 最新版本 |
| 記憶體 | 建議 32GB+ (26B 模型需要約 16GB VRAM/RAM) |
| 網路 | 需要連線 (OpenStreetMap、匯率 API) |

---

## 安裝步驟

### 1. 安裝 Ollama

前往 [ollama.com](https://ollama.com) 下載並安裝。

### 2. 下載模型

```bash
ollama pull qwen3.6:26b
```

確認模型已安裝：
```bash
ollama list
```

### 3. 安裝 Python 依賴

```bash
cd travel_app
pip install -r requirements.txt
```

需要的套件：
- `fastapi` - Web 框架
- `uvicorn` - ASGI 伺服器
- `httpx` - HTTP 客戶端
- `pydantic` - 資料驗證

---

## 啟動應用程式

### 方法一：直接執行（推薦）

```bash
cd travel_app
python main.py
```

### 方法二：使用 uvicorn

```bash
cd travel_app
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 存取應用程式

開啟瀏覽器，前往：
```
http://localhost:8000
```

### 確認狀態

- 頁面頂部會顯示 Ollama 模型狀態
- 綠色圓點 = 連線正常 ✓
- 紅色圓點 = 離線 ✗

---

## 功能說明

### 1. 🌐 AI 翻譯

- 支援多國語言互譯
- 使用 Qwen3.6 26B 進行高品質翻譯
- 保留原文語氣和風格

**使用方式：**
1. 輸入要翻譯的文字
2. 選擇來源語言和目标語言
3. 點擊「翻譯」

### 2. 💱 即時匯率

- 即時查詢全球貨幣匯率
- 以 TWD (新台幣) 為基準
- 支援交叉匯率計算

**使用方式：**
1. 輸入金額
2. 選擇來源貨幣和目标貨幣
3. 點擊「轉換」

### 3. 🗺️ 路線規劃

- 整合 OpenStreetMap 和 OSRM
- 支援步行、自行車、開車三種模式
- 提供詳細的轉彎指引

**使用方式：**
1. 輸入起點和終點
2. 選擇交通方式
3. 點擊「規劃路線」

### 4. 🍜 美食推薦

- AI 根據位置和偏好推薦餐廳
- 可指定菜系和預算
- 提供餐廳名稱、招牌菜、價格範圍

**使用方式：**
1. 輸入目的地
2. (選填) 指定偏好菜系和預算
3. 點擊「推薦美食」

### 5. 💬 旅行助手

- 綜合旅遊諮詢 AI
- 可詢問任何旅遊相關問題
- 行程規劃、景點推薦、安全提醒

**使用方式：**
1. 在對話框輸入問題
2. 點擊「發送」或按 Enter

---

## 冷啟動機制

### 什麼是冷啟動？

Ollama 在第一次被呼叫時，需要將模型載入記憶體。對於 26B 參數的模型，這可能需要 **3-5 分鐘**。

### 應用程式的防護措施

| 層級 | 說明 |
|------|------|
| **伺服器啟動預熱** | 伺服器啟動時自動發送測試請求，觸發模型載入 |
| **前端自動預熱** | 頁面載入 2 秒後自動呼叫預熱 API |
| **超長 Timeout** | 所有 Ollama 請求的 timeout 設為 600 秒 (10 分鐘) |
| **手動預熱按鈕** | 可手動觸發 `/api/warmup` 端點 |

### 預熱狀態指示

- 🔥 **預熱中...** - 模型正在載入
- ✅ **已就緒** - 模型載入完成
- ❌ **預熱失敗** - 無法連線到 Ollama

---

## 疑難排解

### 問題 1：無法連線到 Ollama

**症狀：** 狀態顯示「離線 ✗」

**解決方案：**
```bash
# 確認 Ollama 正在執行
ollama serve

# 在另一個終端確認模型存在
ollama list

# 如果模型不存在，下載它
ollama pull qwen3.6:26b
```

### 問題 2：回應超時

**症狀：** 請求發出後很久沒有回應

**可能原因：**
- 模型正在冷啟動載入中
- 系統資源不足

**解決方案：**
- 等待 3-5 分鐘讓模型載入完成
- 確認系統有足夠的 RAM/VRAM
- 關閉其他佔用記憶體的程式

### 問題 3：模型名稱錯誤

**症狀：** 收到 404 或模型找不到的錯誤

**解決方案：**
```bash
# 查看你實際安裝的模型
ollama list

# 修改 main.py 中的模型名稱
# 或使用環境變數
set OLLAMA_MODEL=你的模型名稱
```

### 問題 4：匯率 API 無法連線

**症狀：** 匯率轉換失敗

**解決方案：**
- 確認網路連線正常
- 匯率 API 是免費服務，可能有速率限制
- 稍後再試

### 問題 5：路線規劃找不到地址

**症狀：** 起點或終點找不到

**解決方案：**
- 使用更完整的地址
- 加上城市或國家名稱
- 嘗試用英文地址

---

## API 文件

### 健康檢查

```
GET /api/health
```

**回應：**
```json
{
  "status": "ok",
  "ollama_model": "qwen3.6:26b",
  "ollama_url": "http://localhost:11434",
  "time": "2026-05-01T18:30:00"
}
```

### 預熱模型

```
POST /api/warmup
```

**回應：**
```json
{
  "status": "warmed_up",
  "model": "qwen3.6:26b"
}
```

### 翻譯

```
POST /api/translate
```

**請求：**
```json
{
  "text": "你好世界",
  "source_lang": "zh-TW",
  "target_lang": "en"
}
```

**回應：**
```json
{
  "original": "你好世界",
  "source_lang": "zh-TW",
  "target_lang": "en",
  "translated": "Hello World"
}
```

### 匯率轉換

```
POST /api/currency
```

**請求：**
```json
{
  "amount": 1000,
  "from_currency": "TWD",
  "to_currency": "USD"
}
```

**回應：**
```json
{
  "amount": 1000,
  "from": "TWD",
  "to": "USD",
  "result": 30.5,
  "rate_info": "1 TWD = 0.0305 USD",
  "timestamp": "2026-05-01"
}
```

### 路線規劃

```
POST /api/route
```

**請求：**
```json
{
  "start": "台北101",
  "end": "故宮博物院",
  "mode": "car"
}
```

**回應：**
```json
{
  "start": "台北101, 台北市...",
  "end": "故宮博物院, 新北市...",
  "distance_km": 35.2,
  "duration_min": 45.5,
  "mode": "car",
  "steps": [
    {
      "instruction": "向北行駛",
      "distance": 500,
      "duration": 60
    }
  ]
}
```

### 美食推薦

```
POST /api/food
```

**請求：**
```json
{
  "location": "東京",
  "cuisine": "拉麵",
  "budget": "中等",
  "count": 5
}
```

### 旅行助手

```
POST /api/assistant
```

**請求：**
```json
{
  "message": "請幫我規劃東京 3 天 2 夜的行程"
}
```

---

## 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 伺服器位址 |
| `OLLAMA_MODEL` | `qwen3.6:26b` | 使用的模型名稱 |

**設定方式 (Windows)：**
```bash
set OLLAMA_MODEL=qwen3.6:26b
python main.py
```

**設定方式 (Linux/macOS)：**
```bash
export OLLAMA_MODEL=qwen3.6:26b
python main.py
```

---

## 檔案結構

```
travel_app/
├── main.py              # FastAPI 後端主程式
├── requirements.txt     # Python 依賴清單
├── .env.example         # 環境變數範例
├── README.md            # 本操作手冊
└── static/
    ├── index.html       # 前端頁面
    ├── style.css        # 響應式樣式
    └── app.js           # 前端邏輯
```

---

## 技術架構

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   前端 UI    │────▶│  FastAPI    │────▶│   Ollama    │
│  (瀏覽器)    │◀────│   後端      │◀────│  Qwen3.6    │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │  OpenStreet │
                    │    Map      │
                    │  + 匯率API  │
                    └─────────────┘
```

---

## 授權與注意事項

- Ollama 模型需自行下載安裝
- OpenStreetMap 和 OSRM 為免費公開服務
- 匯率資料來自 er-api.com (免費額度)
- 本應用程式適合個人學習和測試使用

---

**最後更新：** 2026-05-01
**版本：** 1.0.0
