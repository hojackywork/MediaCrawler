from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import subprocess
import os
import glob
import json
import time
import uuid
from typing import Dict, Optional

app = FastAPI()
DATA_DIR = "data"

# 用於在內存中存儲任務狀態的字典
# 格式: { "task_id": { "status": "running", "keyword": "abc", "start_time": 1234567890 } }
tasks: Dict[str, dict] = {}

class CrawlRequest(BaseModel):
    keywords: str
    platform: str = "xhs"

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

def run_crawler_task(task_id: str, cmd: str):
    print(f"[{task_id}] Starting task: {cmd}")
    tasks[task_id]["status"] = "running"
    
    try:
        # 執行爬蟲，設置 5 分鐘超時
        subprocess.run(cmd, shell=True, timeout=300)
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["end_time"] = time.time()
        print(f"[{task_id}] Task finished")
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
        print(f"[{task_id}] Task failed: {e}")

@app.get("/")
def read_root():
    return {"status": "MediaCrawler API (Task Mode) is ready"}

@app.post("/crawl", response_model=TaskResponse)
def trigger_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    # 1. 生成唯一的 Task ID
    task_id = str(uuid.uuid4())
    
    # 2. 記錄任務信息
    tasks[task_id] = {
        "status": "pending",
        "keyword": request.keywords,
        "platform": request.platform,
        "start_time": time.time()
    }

    # 3. 構建命令
    cmd = f"python main.py --platform {request.platform} --lt qrcode --type search --keywords '{request.keywords}'"
    
    # 4. 後台執行
    background_tasks.add_task(run_crawler_task, task_id, cmd)
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": "Task created. Use /results/{task_id} to check progress."
    }

@app.get("/results/{task_id}")
def get_result(task_id: str):
    # 1. 檢查任務是否存在
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task ID not found")
    
    task = tasks[task_id]
    
    # 2. 如果任務還在跑，直接返回狀態
    if task["status"] in ["pending", "running"]:
        return {
            "task_id": task_id,
            "status": task["status"],
            "message": "Crawling in progress, please wait..."
        }
        
    # 3. 如果任務失敗
    if task["status"] == "failed":
        return {
            "task_id": task_id,
            "status": "failed",
            "error": task.get("error")
        }

    # 4. 如果任務完成，尋找對應的檔案
    # 邏輯：找包含「關鍵字」且「修改時間」大於「任務開始時間」的檔案
    try:
        # 獲取 data 目錄下所有 json 文件
        all_files = glob.glob(os.path.join(DATA_DIR, '*.json'))
        
        # 過濾文件
        candidates = []
        for f in all_files:
            # 檢查文件名是否包含關鍵字 (防止拿到別人的結果)
            # 注意：小紅書 ID 或關鍵字通常會出現在文件名裡
            # 如果文件名沒有關鍵字，我們改用時間判斷
            file_mtime = os.path.getmtime(f)
            
            # 條件：文件修改時間 > 任務開始時間 - 10秒 (容錯)
            if file_mtime > (task["start_time"] - 10):
                candidates.append((f, file_mtime))
        
        if not candidates:
            return {"status": "empty", "message": "Task finished but no new file found."}
            
        # 找到最新的那個 (假設是這個任務產生的)
        # 如果並發很高，還可以進一步檢查內容，但在 n8n 場景下這樣足夠了
        latest_file = max(candidates, key=lambda x: x[1])[0]
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return {
            "task_id": task_id,
            "status": "success",
            "data": data
        }
            
    except Exception as e:
        return {"status": "error", "message": str(e)}
