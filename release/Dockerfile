# 1. 使用轻量级的 Python 官方镜像
FROM python:3.9-slim

# 2. 设置容器内的工作目录
WORKDIR /app

# 3. 复制项目文件到容器内
# 注意：确保 config.py, diagnose.py, therapy.py 以及 requirements.txt 都在当前目录
COPY . /app

# 4. 安装项目依赖
RUN pip install --no-cache-dir -r requirements.txt

# 5. 声明容器内部暴露的端口
EXPOSE 8000

# 6. 启动命令（关键：必须指定 host=0.0.0.0）
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]