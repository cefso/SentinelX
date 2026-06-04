# SentinelX Helm Chart

使用 Helm 在 Kubernetes 上部署 SentinelX 全栈（backend、frontend、PostgreSQL、Redis、Ingress、HPA）。

## 前置条件

- Kubernetes 1.25+
- Helm 3.x
- kubectl 已配置集群访问
- Ingress Controller（推荐 nginx-ingress）
- metrics-server（HPA 需要）

## 快速安装

```bash
# 安装（必须提供密钥）
helm install sentinelx ./helm/sentinelx \
  -n sentinelx \
  --create-namespace \
  --set secrets.jwtSecretKey="$(openssl rand -hex 32)" \
  --set secrets.dbPassword="$(openssl rand -hex 16)" \
  --set ingress.host=sentinelx.your-domain.com
```

镜像默认从 `ghcr.io/cefso/sentinelx` 拉取（backend、frontend、postgres）。可通过 `global.imageRegistry` 与各组件 `image.repository` / `image.tag` 覆盖。

## 升级与回滚

```bash
# 升级
helm upgrade sentinelx ./helm/sentinelx -n sentinelx \
  --reuse-values \
  --set backend.image.tag=v1.2.0

# 查看历史
helm history sentinelx -n sentinelx

# 回滚
helm rollback sentinelx 1 -n sentinelx
```

## 卸载

```bash
helm uninstall sentinelx -n sentinelx
```

注意：StatefulSet 的 PVC 默认不会自动删除，需按需手动清理。

## 生产环境（外置数据库）

使用 [values-production.yaml](values-production.yaml) 关闭内置 PostgreSQL 与 Redis，并指向托管服务：

```bash
helm install sentinelx ./helm/sentinelx \
  -n sentinelx \
  --create-namespace \
  -f helm/sentinelx/values-production.yaml \
  --set secrets.jwtSecretKey="..." \
  --set secrets.dbPassword="..." \
  --set backend.externalDbHost=your-rds.example.com \
  --set backend.externalRedisHost=your-redis.example.com
```

## 主要配置项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `global.imageRegistry` | 镜像仓库前缀 | `ghcr.io/cefso/sentinelx` |
| `namespace.name` | 目标命名空间 | `sentinelx` |
| `postgresql.enabled` | 是否部署内置 PostgreSQL | `true` |
| `postgresql.serviceName` | DB 连接 Service 名（`DB_HOST`） | `postgres` |
| `redis.enabled` | 是否部署内置 Redis | `true` |
| `redis.serviceName` | Redis 连接 Service 名 | `redis` |
| `backend.replicaCount` | 后端副本数 | `2` |
| `frontend.containerPort` | 前端容器端口（nginx 为 80） | `80` |
| `ingress.host` | Ingress 域名 | `sentinelx.example.com` |
| `secrets.jwtSecretKey` | JWT 密钥（必填） | `""` |
| `secrets.dbPassword` | 数据库密码（必填） | `""` |
| `hpa.backend.enabled` | 后端 HPA | `true` |
| `hpa.frontend.enabled` | 前端 HPA | `true` |

完整默认值见 [values.yaml](values.yaml)。

## 验证部署

```bash
kubectl get pods -n sentinelx
kubectl get ingress -n sentinelx

# 端口转发测试后端
kubectl port-forward -n sentinelx svc/sentinelx-backend 8000:80
curl http://localhost:8000/health
```

当 release 名与 Chart 名均为 `sentinelx` 时，资源名称为 `sentinelx-backend`、`sentinelx-frontend` 等；若 release 名不同，会加上 release 前缀。

## 密钥管理建议

- 不要将真实密码写入 `values.yaml` 并提交到 Git
- 安装时使用 `--set` 或 `--set-file`
- 生产环境可配合 External Secrets Operator 等方案
