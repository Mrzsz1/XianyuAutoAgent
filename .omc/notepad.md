# Notepad

## Priority Context
<!-- Always loaded on session start. Keep under 500 chars. -->
XianyuAutoAgent 闲鱼客服机器人已部署在 F:\咸鱼客服
API: https://wzw.pp.ua/v1, 模型: gpt-5.2
启动命令: python main.py

## Working Memory
<!-- Timestamped notes, auto-pruned after 7 days -->

### 2026-01-29 21:44
- 成功部署 XianyuAutoAgent (https://github.com/shaxiu/XianyuAutoAgent)
- 依赖已安装: openai, websockets, loguru, python-dotenv, requests
- .env 配置完成: API_KEY, COOKIES_STR, MODEL_BASE_URL, MODEL_NAME
- 提示词文件已配置: classify_prompt.txt, default_prompt.txt, price_prompt.txt, tech_prompt.txt
- Cookie 更新后程序运行成功，Token获取正常，心跳正常
- 切换人工/AI模式: 发送中文句号 "。"

## MANUAL
<!-- Never auto-pruned. User-controlled permanent notes. -->

### 闲鱼客服机器人使用说明
- 位置: F:\咸鱼客服
- 启动: `cd "F:\咸鱼客服" && python main.py`
- 停止: Ctrl+C
- Cookie过期时需要重新获取并更新 .env 文件中的 COOKIES_STR
- 获取Cookie方法: 浏览器访问闲鱼网页版 -> F12开发者工具 -> Network -> 复制Cookie
