from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import os
import glob
import json
import time

app = FastAPI()

# 定義請求數據模型 (這是新加的，用來接收 n8n 傳來的 JSON)
class CrawlRequest(BaseModel):
    keywords: str
    platform: str = "xhs"  # 預設為 xhs，可選: dy, ks, bilibili, wb

# 設置數據保存目錄 (MediaCrawler 默認是 data/)
DATA_DIR = "data"

@app.get("/")
def read_root():
    return {"status": "MediaCrawler API is ready (Multi-Platform Supported)"}

@app.post("/crawl")
def trigger_crawl(request: CrawlRequest):
    # 1. 驗證平台參數
    valid_platforms = ["xhs", "dy", "ks", "bilibili", "wb"]
    if request.platform not in valid_platforms:
        return {"status": "error", "message": f"Invalid platform. Choose from {valid_platforms}"}

    # 2. 構建命令
    # 使用 f-string 動態插入 platform 和 keywords
    # 注意：這裡的 main.py 參數必須符合你使用的 MediaCrawler 版本
    cmd = f"python main.py --platform {request.platform} --lt qrcode --type search --keywords '{request.keywords}'"
    
    print(f"Executing command: {cmd}")
    
    # 3. 執行爬蟲 (設置超時時間 3 分鐘)
    # capture_output=True 會抓取標準輸出，方便我們 debug
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=180 
        )
    except subprocess.TimeoutExpired:
        # 如果超時，嘗試殺死進程並返回錯誤
        return {"status": "error", "message": "Crawling timed out (took > 180s)"}

    # 4. 讀取結果
    # 邏輯：尋找 data/ 目錄下最新生成的 json 文件
    try:
        list_of_files = glob.glob(os.path.join(DATA_DIR, '*.json'))
        
        if not list_of_files:
            # 如果沒找到文件，通常是爬蟲報錯了，返回 logs 讓用戶去 debug
            # 截取最後 1000 個字符的日誌
            return {
                "status": "empty", 
                "message": "No data found. Check logs for cookie issues.", 
                "logs": result.stderr[-1000:] + result.stdout[-1000:]
            }
            
        # 找到最新文件
        latest_file = max(list_of_files, key=os.path.getctime)
        
        # 讀取內容
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return {
            "status": "success",
            "platform": request.platform,
            "keyword": request.keywords,
            "count": len(data),
            "data": data,
            "source_file": latest_file
        }
            
    except Exception as e:
        return {
            "status": "error", 
            "message": str(e), 
            "logs": result.stderr[-500:] if 'result' in locals() else "Unknown error"
        }
