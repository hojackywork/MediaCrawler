from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import subprocess
import os
import glob
import json

app = FastAPI()
DATA_DIR = "data"

class CrawlRequest(BaseModel):
    keywords: str
    platform: str = "xhs"

def run_crawler_task(cmd: str):
    print(f"Starting background task: {cmd}")
    try:
        # 使用 300秒 (5分鐘) 超時，足夠爬完
        subprocess.run(cmd, shell=True, timeout=300) 
        print("Task finished successfully")
    except Exception as e:
        print(f"Task failed: {e}")

@app.get("/")
def read_root():
    return {"status": "MediaCrawler API (Async Mode) is ready"}

@app.post("/crawl")
def trigger_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    # 1. 構建命令
    cmd = f"python main.py --platform {request.platform} --lt qrcode --type search --keywords '{request.keywords}'"
    
    # 2. 將爬蟲任務丟到後台執行，不讓 HTTP 連線等待
    background_tasks.add_task(run_crawler_task, cmd)
    
    return {"status": "started", "message": f"Crawling {request.keywords} in background..."}

@app.get("/results")
def get_results():
    # 獲取最新的數據文件
    try:
        list_of_files = glob.glob(os.path.join(DATA_DIR, '*.json'))
        if not list_of_files:
            return {"status": "empty", "message": "No data yet. Keep waiting."}
            
        latest_file = max(list_of_files, key=os.path.getctime)
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return {
            "status": "success",
            "file": os.path.basename(latest_file),
            "data": data
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
