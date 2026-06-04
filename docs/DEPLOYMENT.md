# SentinelX 部署指南

## 部署方式概览

| 部署方式 | 适用场景 | 复杂度 |
|---------|---------|--------|
| Docker Compose | 开发/测试/小规模生产 | 低 |
| Helm (Kubernetes) | 生产环境/大规模部署 | 中 |
| 直接部署 | 开发调试 | 低 |

## Docker Compose 部署

### 快速启动

```bash
# 克隆项目
git clone https://github.com/your-repo/SentinelX.git
cd SentinelX

# 启动所有服务
docker compose -f docker/docker-compose.yml up -d

# 查看状态
docker compose -f docker/docker-compose.yml ps
```

### 仅启动基础设施

本地开发时，后端和前端在本地运行，只启动数据库和缓存：

```bash
docker compose -f docker/docker-compose.infra.yml up -d
```

### 带管理工具

```bash
docker compose --profile tools up -d
```

访问地址：
- 前端: http://localhost:3000
- pgAdmin: http://localhost:5050
- Redis Commander: http://localhost:8081

## Helm (Kubernetes) 部署

详见 [helm/sentinelx/README.md](../helm/sentinelx/README.md)

### 前提条件

- Kubernetes 1.25+
- Helm 3.x
- kubectl 配置完成
- Ingress Controller（nginx-ingress）
- metrics-server（用于 HPA）

### 部署步骤

```bash
# 安装 Chart（必须设置 JWT 与数据库密码）
helm install sentinelx ./helm/sentinelx \
  -n sentinelx \
  --create-namespace \
  --set secrets.jwtSecretKey="$(openssl rand -hex 32)" \
  --set secrets.dbPassword="$(openssl rand -hex 16)" \
  --set ingress.host=sentinelx.your-domain.com

# 等待 Pod 就绪
kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=sentinelx -n sentinelx --timeout=300s

# 查看 Ingress
kubectl get ingress -n sentinelx
```

生产环境使用外置数据库时，可参考 `helm/sentinelx/values-production.yaml` 并通过 `-f` 传入。

## 生产环境配置

### 数据库

- 建议使用托管数据库服务（RDS、Cloud SQL 等）
- 启用 TimescaleDB 扩展以支持时序数据
- 配置定期备份
- 推荐 PostgreSQL 16+

### Redis

- 生产环境建议使用 Redis Cluster 或托管服务（ElastiCache、Memorystore）
- 配置持久化（AOF）
- 设置合理的内存策略

### 安全配置

必须修改以下配置：

```bash
# JWT 密钥（必须修改）
JWT_SECRET_KEY=your-very-long-random-secret-key

# 数据库密码
DB_PASSWORD=your-secure-db-password

# AI API Key（可选）
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
```

### 性能优化

1. **数据库连接池**
   ```env
   DB_POOL_SIZE=20
   DB_MAX_OVERFLOW=40
   ```

2. **Redis 连接数**
   ```env
   REDIS_POOL_SIZE=20
   ```

3. **日志级别**
   ```env
   LOG_LEVEL=INFO
   LOG_FORMAT=json
   ```

## 负载均衡配置

### Nginx 配置示例

```nginx
upstream sentinelx_backend {
    server backend-1:8000;
    server backend-2:8000;
    keepalive 64;
}

server {
    listen 80;
    server_name sentinelx.example.com;

    location /api/ {
        proxy_pass http://sentinelx_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location / {
        proxy_pass http://frontend:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 监控配置

### Prometheus 抓取配置

```yaml
scrape_configs:
  - job_name: 'sentinelx'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: /metrics
```

### 健康检查端点

- `/health` - 基础健康检查
- `/health/ready` - 就绪探针（依赖数据库和 Redis）
- `/health/live` - 存活探针

## 备份策略

### 数据库备份

```bash
# 全量备份
pg_dump -h localhost -U postgres -d sentinelx > backup.sql

# 定时备份（crontab）
0 2 * * * pg_dump -h $DB_HOST -U postgres -d sentinelx | gzip > /backup/sentinelx_$(date +\%Y\%m\%d).sql.gz
```

### Redis 备份

```bash
# RDB 快照
redis-cli SAVE

# AOF 持久化（已启用）
# 备份 /data/appendonly.aof
```

## 故障排查

### 数据库连接失败

```bash
# 检查数据库日志
kubectl logs -n sentinelx -l app.kubernetes.io/component=postgresql

# 测试连接
kubectl exec -n sentinelx deploy/sentinelx-backend -- python -c "from apps.core.database import async_session; print('OK')"
```

### 告警未收到

1. 检查规则是否正确配置
2. 检查通知渠道是否启用
3. 查看后端日志中的告警处理记录
4. 使用 Trace ID 诊断告警处理流程

### 性能问题

1. 检查数据库索引
2. 查看慢查询日志
3. 检查 Redis 命中率
4. 调整 HPA 配置

## 升级指南

### Docker Compose 升级

```bash
# 拉取新镜像
docker compose pull

# 重启服务
docker compose up -d
```

### Helm 升级

```bash
# 更新镜像 tag 并滚动升级
helm upgrade sentinelx ./helm/sentinelx -n sentinelx \
  --reuse-values \
  --set backend.image.tag=v2.0.0 \
  --set frontend.image.tag=v2.0.0

kubectl rollout status deployment/sentinelx-backend -n sentinelx
```
