from fastapi import FastAPI, BackgroundTasks
import subprocess
import os

app = FastAPI()

def run_crawler_task(keywords: str):
    # 這是實際執行爬蟲的命令，根據需要修改參數
    # 注意：這裡假設你已經把 Cookie 放在環境變量或配置文件裡了
    cmd = f"python main.py --platform xhs --lt qrcode --type search --keywords '{keywords}'"
    print(f"Executing: {cmd}")
    subprocess.run(cmd, shell=True)

@app.get("/")
def read_root():
    return {"status": "MediaCrawler API is running"}

@app.post("/crawl")
def trigger_crawl(keywords: str, background_tasks: BackgroundTasks):
    # 收到請求後，在後台啟動爬蟲，立刻返回「已接收」
    background_tasks.add_task(run_crawler_task, keywords)
    return {"message": f"Started crawling for: {keywords}", "status": "processing"}