import json

manifest_path = r"C:\Users\III-AIPC-02\.nanobot\workspace\travel_app\static\manifest.json"

with open(manifest_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Add shortcuts if missing
if "shortcuts" not in data:
    data["shortcuts"] = [
        {
            "name": "行程規劃",
            "short_name": "行程",
            "description": "建立新的行程規劃",
            "url": "/?tab=plan",
            "icons": [{"src": "/static/icons/icon-192.png", "sizes": "192x192"}]
        },
        {
            "name": "即時翻譯",
            "short_name": "翻譯",
            "description": "離線即時翻譯",
            "url": "/?tab=translate",
            "icons": [{"src": "/static/icons/icon-192.png", "sizes": "192x192"}]
        },
        {
            "name": "路線規劃",
            "short_name": "路線",
            "description": "規劃最佳路線",
            "url": "/?tab=route",
            "icons": [{"src": "/static/icons/icon-192.png", "sizes": "192x192"}]
        }
    ]

with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("Manifest updated successfully")
print("Shortcuts:", len(data.get("shortcuts", [])))