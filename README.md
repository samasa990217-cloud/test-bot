# Discord Bot (Render Version)

功能：
- /公告：發布公告
- /買賣交易：發布交易訊息
- /我要交易：自動建立交易頻道，並紀錄交易過程

部署到 Render Web Service：
1. 確認 Python 版本（建議 3.10+）
2. 上傳所有檔案 (`bot.py`, `requirements.txt`, `trade_logs/`)
3. 在 `bot.py` 裡填入你的 Discord Bot TOKEN 與角色 ID
4. Render 會啟動 Flask 來保持 Web Service 運行
