from fastapi import FastAPI, HTTPException
import subprocess
import os
import glob
import json
import time

app = FastAPI()

# 設置數據保存目錄
DATA_DIR = "data"

@app.get("/")
def read_root():
    return {"status": "MediaCrawler API is ready"}

@app.post("/crawl")
def trigger_crawl(keywords: str):
    # 1. 清理舊數據（可選，避免讀到舊文件）
    # os.system(f"rm {DATA_DIR}/*.json") 
    
    # 2. 構建命令：強制使用 search 模式
    # 注意：這裡假設你的 main.py 支持 --keywords 參數 (新版通常支持)
    # 如果不支持，它可能會去爬默認關鍵詞，請留意日誌
    cmd = f"python main.py --platform xhs --lt qrcode --type search --keywords '{keywords}'"
    
    print(f"Executing: {cmd}")
    
    # 3. 執行爬蟲 (設置超時時間 3 分鐘)
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=180 
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Crawling timed out"}

    # 4. 讀取最新的 JSON 結果
    try:
        list_of_files = glob.glob(os.path.join(DATA_DIR, '*.json'))
        if not list_of_files:
            return {"status": "empty", "message": "No data found", "logs": result.stderr[-1000:]}
            
        # 找到最新生成的文件
        latest_file = max(list_of_files, key=os.path.getctime)
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return {
            "status": "success",
            "count": len(data),
            "data": data,  # 這裡就是你要的所有資訊
            "source_file": latest_file
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "logs": result.stderr[-500:]}
