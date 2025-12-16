from fastapi import FastAPI, HTTPException
import subprocess
import os
import glob
import json

app = FastAPI()

# 設置數據保存目錄 (MediaCrawler 默認是 data/)
DATA_DIR = "data"

@app.get("/")
def read_root():
    return {"status": "MediaCrawler API is ready (Synchronous Mode)"}

@app.post("/crawl")
def trigger_crawl(keywords: str):
    # 1. 構建命令
    # 注意：這裡強制指定保存為 json 格式，方便讀取
    # 如果你的 MediaCrawler 版本不支持 --format，請確保 config.py 裡設置了保存為 json
    cmd = f"python main.py --platform xhs --lt qrcode --type search --keywords '{keywords}'"
    
    print(f"Starting crawl for: {keywords}...")
    
    # 2. 執行命令 (使用 run 替代 Popen，這會阻塞直到爬蟲結束)
    # capture_output=True 可以讓我們看到爬蟲打印的日誌
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=120 # 設置 2 分鐘超時，防止卡死
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Crawling timed out (took longer than 120s)"}

    # 3. 檢查執行日誌 (方便 Debug)
    logs = result.stdout + result.stderr
    
    # 4. 嘗試讀取生成的最新數據文件
    # MediaCrawler 通常會把文件保存在 data/ 目录下
    try:
        # 尋找 data 目錄下最新的 json 文件
        list_of_files = glob.glob(os.path.join(DATA_DIR, '*.json'))
        if list_of_files:
            latest_file = max(list_of_files, key=os.path.getctime)
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {
                "status": "success",
                "data": data, # 這是爬到的具體內容
                "logs": logs[-500:] # 只返回最後 500 字日誌，避免太長
            }
        else:
            return {
                "status": "warning", 
                "message": "Crawl finished but no JSON file found. Check logs.",
                "logs": logs # 返回完整日誌看看到底哪裡錯了 (比如 Cookie 失效)
            }
    except Exception as e:
        return {"status": "error", "message": str(e), "logs": logs}
