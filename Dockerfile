# 使用轻量级的 Python 3.12 镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置系统环境变量
# PYTHONUNBUFFERED=1: 保证日志实时输出到 Docker 控制台
# PIP_NO_CACHE_DIR=1: 减小镜像体积
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

# 安装系统依赖（如果涉及某些科学计算库可能需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
# 先复制 requirements.txt 是为了利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 复制项目所有代码
COPY . .

# 暴露 Streamlit 默认端口 8501
EXPOSE 8501

# 启动命令：运行 Streamlit 大屏界面
# 这里的 src/dashboard/app.py 是我们之前定义的入口
CMD ["streamlit", "run", "src/dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]