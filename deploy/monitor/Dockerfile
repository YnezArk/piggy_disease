# 猪咳嗽声智能监测服务 —— Docker 镜像
FROM python:3.10-slim

WORKDIR /app

# 系统依赖：libsndfile(读音频) + ffmpeg(mp3/格式转换兜底)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libsndfile1 ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py config.py start.sh ./
COPY src ./src
COPY models ./models
COPY static ./static

ENV PORT=8000
ENV TZ=Asia/Shanghai
EXPOSE 8000

CMD ["sh", "start.sh"]