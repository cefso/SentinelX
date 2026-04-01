# SentinelX Kubernetes 部署配置

## 目录结构

```
k8s/
├── namespace.yaml         # 命名空间、Secret、ConfigMap
├── postgres-deployment.yaml # PostgreSQL + TimescaleDB StatefulSet
├── redis-deployment.yaml   # Redis StatefulSet
├── backend-deployment.yaml  # Backend Deployment + Service
├── frontend-deployment.yaml # Frontend Deployment + Service + Ingress
├── backend-hpa.yaml        # Backend HPA 自动扩缩容
└── frontend-hpa.yaml      # Frontend HPA 自动扩缩容
```

## 快速部署

### 前置条件

- Kubernetes 1.25+
- Ingress Controller（如 nginx-ingress）
- metrics-server（用于 HPA）

### 部署步骤

```bash
# 1. 创建命名空间和密钥
kubectl apply -f namespace.yaml

# 2. 部署数据库和缓存
kubectl apply -f postgres-deployment.yaml
kubectl apply -f redis-deployment.yaml

# 3. 等待数据库就绪
kubectl wait --for=condition=ready pod -l app=sentinelx,component=postgres -n sentinelx --timeout=120s
kubectl wait --for=condition=ready pod -l app=sentinelx,component=redis -n sentinelx --timeout=60s

# 4. 部署后端
kubectl apply -f backend-deployment.yaml
kubectl apply -f backend-hpa.yaml

# 5. 部署前端
kubectl apply -f frontend-deployment.yaml
kubectl apply -f frontend-hpa.yaml
```

### 验证部署

```bash
# 检查 Pod 状态
kubectl get pods -n sentinelx

# 检查 Services
kubectl get svc -n sentinelx

# 检查 Ingress
kubectl get ingress -n sentinelx

# 测试后端健康检查
kubectl port-forward -n sentinelx svc/sentinelx-backend 8000:80
curl http://localhost:8000/health
```

## 资源配置

### Backend

| 资源 | Request | Limit |
|------|---------|-------|
| CPU | 250m | 500m |
| Memory | 256Mi | 512Mi |

副本数：2-10（根据 HPA 自动调整）

### Frontend

| 资源 | Request | Limit |
|------|---------|-------|
| CPU | 100m | 200m |
| Memory | 128Mi | 256Mi |

副本数：2-10（根据 HPA 自动调整）

### PostgreSQL

存储：20Gi（通过 PVC 自动provision）
副本数：1（StatefulSet）

### Redis

存储：2Gi（通过 PVC 自动provision）
副本数：1（StatefulSet）

## 环境变量配置

### Secret (sentinelx-secrets)

| Key | 说明 | 必须修改 |
|-----|------|---------|
| DB_USER | PostgreSQL 用户名 | 否 |
| DB_PASSWORD | PostgreSQL 密码 | **是** |
| JWT_SECRET_KEY | JWT 密钥 | **是** |

### ConfigMap (sentinelx-config)

| Key | 默认值 |
|-----|--------|
| APP_NAME | SentinelX |
| DEBUG | false |
| DB_HOST | postgres |
| DB_PORT | 5432 |
| DB_NAME | sentinelx |
| REDIS_HOST | redis |
| REDIS_PORT | 6379 |

## Ingress 配置

默认 Ingress 域名为 `sentinelx.example.com`，请根据实际环境修改：

```yaml
spec:
  rules:
  - host: sentinelx.example.com  # 修改为实际域名
```

## 扩缩容

```bash
# 手动扩缩容
kubectl scale deployment sentinelx-backend -n sentinelx --replicas=5

# 查看 HPA 状态
kubectl get hpa -n sentinelx
kubectl describe hpa sentinelx-backend-hpa -n sentinelx
```

## 清理

```bash
kubectl delete -f frontend-deployment.yaml
kubectl delete -f backend-deployment.yaml
kubectl delete -f redis-deployment.yaml
kubectl delete -f postgres-deployment.yaml
kubectl delete -f namespace.yaml
```
