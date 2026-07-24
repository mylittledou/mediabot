FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量，防止 Python 缓冲 stdout 和 stderr
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src

# 复制 requirements 文件
COPY requirements.txt .

# 安装依赖包
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY src/ ./src/

# 暴露 Web 端口
EXPOSE 8080

# 运行 Web 和 Bot，并将所有原始输出重定向到 data 目录，以便在容器完全静默时排查
CMD sh -c "python src/web.py > /app/data/docker_raw.log 2>&1"
