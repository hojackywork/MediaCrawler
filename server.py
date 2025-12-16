from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import subprocess
import os
import glob
import json
import time
import requests # 需要在 requirements.txt 加入 requests

app = FastAPI()
DATA_DIR = "data"

class UrlRequest(BaseModel):
    url: str

# 輔助函式：將短網址還原並提取 Note ID
def extract_note_id(url: str):
    try:
        # 1. 如果是短網址 (xhslink.com)，先請求一次獲取真實網址
        if "xhslink.com" in url:
            resp = requests.head(url, allow_redirects=True, timeout=10)
            real_url = resp.url
        else:
            real_url = url
            
        # 2. 從真實網址中提取 ID
        # 網址通常長這樣: https://www.xiaohongshu.com/explore/64ecxxxx?params...
        # 或者: https://www.xiaohongshu.com/discovery/item/64ecxxxx?params...
        if "/explore/" in real_url:
            note_id = real_url.split("/explore/")[1].split("?")[0]
        elif "/item/" in real_url:
            note_id = real_url.split("/item/")[1].split("?")[0]
        else:
            return None, "無法解析 Note ID"
            
        return note_id, None
    except Exception as e:
        return None, str(e)

@app.post("/enrich")
def enrich_note(request: UrlRequest):
    # 1. 解析 Note ID
    note_id, error = extract_note_id(request.url)
    
    if not note_id:
        return {"status": "error", "message": f"無效的連結: {error}"}
    
    print(f"解析成功，Note ID: {note_id}，開始採集...")

    # 2. 構建命令 (使用 --type detail 和 --note_id)
    # 注意：這裡假設你的 MediaCrawler 支援 --type detail 配合 --note_id
    # 如果原版不支援，我們需要用一種 trick：直接調用內部腳本
    # 為了保險，我們使用 MediaCrawler 的標準 detail 模式
    
    cmd = f"python main.py --platform xhs --lt qrcode --type detail --note_id {note_id}"
    
    try:
        # 執行爬蟲 (設置 60秒超時，單篇很快)
        # 這裡用 capture_output 抓取日誌
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        
        # 3. 尋找結果文件
        # MediaCrawler detail 模式通常會存入 data/detail_xhs_xxxx.json 或類似
        # 我們直接找最新生成的 json
        list_of_files = glob.glob(os.path.join(DATA_DIR, '*.json'))
        if not list_of_files:
             return {"status": "error", "message": "爬取失敗，未生成檔案", "log": result.stderr}
             
        latest_file = max(list_of_files, key=os.path.getctime)
        
        # 讀取數據
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 過濾數據：如果是列表，找 ID 匹配的那一個；如果是單個對象直接返回
        # 這裡做一個簡單處理，直接返回最新數據
        return {
            "status": "success",
            "note_id": note_id,
            "data": data
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/")
def read_root():
    return {"status": "Enrich API Ready"}
