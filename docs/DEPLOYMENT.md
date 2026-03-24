# OpenCredit Production Deployment Guide

This guide covers deploying OpenCredit to production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Local Docker Deployment](#local-docker-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Database Setup](#database-setup)
7. [Monitoring & Logging](#monitoring--logging)
8. [Security Checklist](#security-checklist)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Docker 24.0+ and Docker Compose 2.0+
- Python 3.11+ (for local development)
- PostgreSQL 16+ (production database)
- Redis 7+ (caching and event streaming)

---

## Environment Configuration

### Required Environment Variables

```bash
# Security (REQUIRED - Generate your own!)
JWT_SECRET=<openssl rand -hex 32>

# Database
POSTGRES_DB=opencredit
POSTGRES_USER=opencredit
POSTGRES_PASSWORD=<strong-password>
DATABASE_URL=postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}

# Redis
REDIS_URL=redis://redis:6379/0
```

### Generating Secrets

```bash
# Generate JWT secret
openssl rand -hex 32

# Generate database password
openssl rand -base64 24

# Generate API key (for testing)
python -c "import secrets; print(f'oc_live_{secrets.token_urlsafe(32)}')"
```

### Environment-Specific Settings

| Setting | Development | Production |
|---------|------------|------------|
| `ENV` | `dev` | `prod` |
| `DATABASE_URL` | `sqlite:///./opencredit.db` | PostgreSQL URL |
| `CORS_ORIGINS` | `http://localhost:*` | Your domain(s) |
| `JWT_EXPIRE_MINUTES` | `60` | `15-30` |

---

## Local Docker Deployment

### Quick Start

```bash
# 1. Clone and navigate to project
cd opencredit

# 2. Create .env from template
cp .env.example .env

# 3. Generate and set secrets
JWT_SECRET=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -base64 24)

# Edit .env with your secrets
nano .env

# 4. Start all services
docker compose up -d

# 5. Create admin user
docker compose exec api python -m scripts.seed_admin

# 6. Run database migrations
docker compose exec api alembic upgrade head

# 7. Verify deployment
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

### Service URLs

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

---

## Cloud Deployment

### AWS (ECS/Fargate)

1. **Create ECR repository**
```bash
aws ecr create-repository --repository-name opencredit
```

2. **Build and push image**
```bash
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker build -t opencredit .
docker tag opencredit:latest <account>.dkr.ecr.<region>.amazonaws.com/opencredit:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/opencredit:latest
```

3. **Create ECS task definition** with environment variables from AWS Secrets Manager

4. **Create ECS service** with Application Load Balancer

### Google Cloud (Cloud Run)

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT_ID/opencredit

# Deploy to Cloud Run
gcloud run deploy opencredit \
  --image gcr.io/PROJECT_ID/opencredit \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "ENV=prod" \
  --set-secrets "JWT_SECRET=jwt-secret:latest,DATABASE_URL=db-url:latest"
```

### Azure (Container Apps)

```bash
# Create container app
az containerapp create \
  --name opencredit \
  --resource-group myResourceGroup \
  --environment myContainerAppEnv \
  --image myregistry.azurecr.io/opencredit:latest \
  --target-port 8000 \
  --ingress external \
  --secrets jwt-secret=<value> \
  --env-vars JWT_SECRET=secretref:jwt-secret
```

---

## Kubernetes Deployment

### Sample Kubernetes Manifests

Create `k8s/` directory with the following files:

**k8s/namespace.yaml**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: opencredit
```

**k8s/secrets.yaml**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: opencredit-secrets
  namespace: opencredit
type: Opaque
stringData:
  JWT_SECRET: "<your-jwt-secret>"
  POSTGRES_PASSWORD: "<your-db-password>"
```

**k8s/configmap.yaml**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: opencredit-config
  namespace: opencredit
data:
  ENV: "prod"
  APP_NAME: "OpenCredit"
  API_PREFIX: "/api/v1"
  POSTGRES_DB: "opencredit"
  POSTGRES_USER: "opencredit"
```

**k8s/deployment.yaml**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: opencredit-api
  namespace: opencredit
spec:
  replicas: 3
  selector:
    matchLabels:
      app: opencredit-api
  template:
    metadata:
      labels:
        app: opencredit-api
    spec:
      containers:
      - name: api
        image: opencredit:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: opencredit-config
        - secretRef:
            name: opencredit-secrets
        env:
        - name: DATABASE_URL
          value: "postgresql+psycopg://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@postgres:5432/$(POSTGRES_DB)"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
```

**k8s/service.yaml**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: opencredit-api
  namespace: opencredit
spec:
  selector:
    app: opencredit-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

**k8s/ingress.yaml**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: opencredit-ingress
  namespace: opencredit
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.opencredit.example.com
    secretName: opencredit-tls
  rules:
  - host: api.opencredit.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: opencredit-api
            port:
              number: 80
```

### Apply Kubernetes Resources

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

---

## Database Setup

### Initial Setup

```bash
# Run migrations
alembic upgrade head

# Create admin user
python -m scripts.seed_admin
```

### Backup & Restore

```bash
# Backup
pg_dump -h localhost -U opencredit -d opencredit > backup.sql

# Restore
psql -h localhost -U opencredit -d opencredit < backup.sql
```

---

## Monitoring & Logging

### Log Aggregation

Logs are output in JSON format (in production) for easy parsing:

```json
{
  "timestamp": "2026-03-23T07:00:00Z",
  "level": "INFO",
  "logger": "app.api.routes.payments",
  "message": "Payment processed",
  "request_id": "abc-123",
  "user_id": 42,
  "duration_ms": 150
}
```

Configure your log aggregator (ELK, Datadog, CloudWatch) to parse JSON logs.

### Health Checks

| Endpoint | Purpose | Frequency |
|----------|---------|-----------|
| `GET /health` | Liveness probe | Every 30s |
| `GET /ready` | Readiness probe | Every 10s |
| `GET /info` | Service info | On demand |

---

## Security Checklist

Before going to production, verify:

- [ ] JWT_SECRET is a strong random value (32+ bytes)
- [ ] Database password is unique and strong
- [ ] .env file is NOT in version control
- [ ] HTTPS is enabled (via reverse proxy or load balancer)
- [ ] CORS_ORIGINS is set to your specific domains
- [ ] Rate limiting is enabled
- [ ] Admin user is created with strong password
- [ ] Database backups are configured
- [ ] Log aggregation is set up
- [ ] Monitoring alerts are configured

---

## Troubleshooting

### Common Issues

**Database connection failed**
```bash
# Check PostgreSQL is running
docker compose ps postgres

# Check connection
docker compose exec postgres psql -U opencredit -d opencredit -c "SELECT 1"
```

**Redis connection failed**
```bash
# Check Redis is running
docker compose exec redis redis-cli ping
```

**Migrations failed**
```bash
# Check current migration state
alembic current

# Rollback and retry
alembic downgrade -1
alembic upgrade head
```

**Permission denied**
```bash
# Ensure non-root user can write
docker compose exec api ls -la /app
```

### Getting Help

- Check logs: `docker compose logs -f api`
- API docs: http://localhost:8000/docs
- Health check: `curl http://localhost:8000/ready`
