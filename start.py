#!/usr/bin/env python3
import uvicorn
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

if not os.path.exists("bio_tracker.db"):
    print("首次运行，正在导入花名册...")
    import import_roster
    import_roster.import_roster()
    print("花名册导入完成！")

print("="*50)
print("  生物学情管理平台 启动中...")
print("="*50)
print("访问地址：")
print("  本机:    http://localhost:8000")
print("  局域网:  http://<<本机IP>:8000")
print("="*50)
print("按 Ctrl+C 停止服务")
print("="*50)

uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
