FROM timescale/timescaledb:latest-pg16

# 复制数据库初始化脚本
COPY init-db.sh /docker-entrypoint-initdb.d/init-db.sh
RUN chmod +x /docker-entrypoint-initdb.d/init-db.sh
