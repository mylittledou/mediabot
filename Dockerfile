FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量，防止 Python 缓冲 stdout 和 stderr
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 复制 requirements 文件
COPY requirements.txt .

# 安装依赖包
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY src/ ./src/

# 运行 bot
CMD ["python", "src/bot.py"]
