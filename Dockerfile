FROM python:3.11-slim

# Cài đặt ffmpeg để xử lý âm thanh
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# Nâng cấp yt-dlp lên bản mới nhất để chống chặn
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
