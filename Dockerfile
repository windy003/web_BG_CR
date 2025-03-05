# 使用官方的Python镜像作为基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制当前目录下的所有文件到工作目录
COPY . .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露端口
EXPOSE 5001

# 创建指定UID的用户（使用1000作为示例，这是很多Linux系统默认用户的UID）
RUN useradd -u 1000 -m myuser && \
    chown -R myuser:myuser /app && \
    chmod -R 755 /app 
    
USER myuser
