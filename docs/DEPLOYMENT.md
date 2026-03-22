# PhishCatcher Deployment Guide

## Overview

This guide covers deploying PhishCatcher in various environments, from development to production. The application is designed to be containerized and can be deployed using Docker, Kubernetes, or traditional server setups.

## Prerequisites

### System Requirements
- **CPU**: 2+ cores (4+ recommended for production)
- **Memory**: 4GB+ RAM (8GB+ recommended for production)
- **Storage**: 20GB+ SSD (100GB+ recommended for production)
- **Network**: Stable internet connection

### Software Requirements
- Docker 20.10+
- Docker Compose 2.0+
- (Optional) Kubernetes 1.24+
- (Optional) Helm 3.0+

## Environment Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```bash
# Database Configuration
DATABASE_URL=postgresql://phishcatcher:password@postgres:5432/phishcatcher
MONGODB_URL=mongodb://phishcatcher:password@mongodb:27017/phishcatcher
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=your-super-secret-key-here-change-this-in-production
JWT_SECRET_KEY=your-jwt-secret-key-here
JWT_REFRESH_SECRET_KEY=your-jwt-refresh-secret-key-here

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Email Service (SendGrid)
SENDGRID_API_KEY=your-sendgrid-api-key
FROM_EMAIL=noreply@yourdomain.com

# Application Settings
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# ML Model
MODEL_PATH=/app/models/phishing_model.pkl
FEATURE_SCALER_PATH=/app/models/feature_scaler.pkl

# Monitoring
SENTRY_DSN=your-sentry-dsn-optional
PROMETHEUS_ENABLED=true
```

## Docker Deployment

### Development Deployment

1. **Clone and Setup**
   ```bash
   git clone https://github.com/your-username/phishcatcher.git
   cd phishcatcher
   cp phishcatcher-backend/.env.example phishcatcher-backend/.env
   ```

2. **Start Services**
   ```bash
   docker-compose up -d
   ```

3. **Initialize Database**
   ```bash
   docker-compose exec backend alembic upgrade head
   docker-compose exec backend python scripts/create_admin.py
   ```

4. **Verify Deployment**
   ```bash
   curl http://localhost:8000/health
   ```

### Production Deployment

1. **Use Production Compose File**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **Setup SSL/TLS**
   ```bash
   # Generate SSL certificates
   certbot certonly --webroot -w /var/www/html -d yourdomain.com
   
   # Update nginx configuration
   docker-compose exec nginx nginx -s reload
   ```

3. **Configure Monitoring**
   ```bash
   # Access Grafana dashboard
   open http://localhost:3001
   # Default credentials: admin/admin
   ```

## Kubernetes Deployment

### Namespace Setup

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: phishcatcher
```

### ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: phishcatcher-config
  namespace: phishcatcher
data:
  DEBUG: "false"
  LOG_LEVEL: "INFO"
  CORS_ORIGINS: "https://yourdomain.com"
  PROMETHEUS_ENABLED: "true"
```

### Secrets

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: phishcatcher-secrets
  namespace: phishcatcher
type: Opaque
data:
  DATABASE_URL: <base64-encoded-database-url>
  MONGODB_URL: <base64-encoded-mongodb-url>
  REDIS_URL: <base64-encoded-redis-url>
  SECRET_KEY: <base64-encoded-secret-key>
  GOOGLE_CLIENT_ID: <base64-encoded-google-client-id>
  GOOGLE_CLIENT_SECRET: <base64-encoded-google-client-secret>
```

### Backend Deployment

```yaml
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: phishcatcher-backend
  namespace: phishcatcher
spec:
  replicas: 3
  selector:
    matchLabels:
      app: phishcatcher-backend
  template:
    metadata:
      labels:
        app: phishcatcher-backend
    spec:
      containers:
      - name: backend
        image: phishcatcher/backend:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: phishcatcher-config
        - secretRef:
            name: phishcatcher-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: phishcatcher-backend-service
  namespace: phishcatcher
spec:
  selector:
    app: phishcatcher-backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

### Frontend Deployment

```yaml
# frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: phishcatcher-frontend
  namespace: phishcatcher
spec:
  replicas: 2
  selector:
    matchLabels:
      app: phishcatcher-frontend
  template:
    metadata:
      labels:
        app: phishcatcher-frontend
    spec:
      containers:
      - name: frontend
        image: phishcatcher/frontend:latest
        ports:
        - containerPort: 3000
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "250m"
---
apiVersion: v1
kind: Service
metadata:
  name: phishcatcher-frontend-service
  namespace: phishcatcher
spec:
  selector:
    app: phishcatcher-frontend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 3000
  type: ClusterIP
```

### Ingress Configuration

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: phishcatcher-ingress
  namespace: phishcatcher
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - yourdomain.com
    - api.yourdomain.com
    secretName: phishcatcher-tls
  rules:
  - host: yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: phishcatcher-frontend-service
            port:
              number: 80
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: phishcatcher-backend-service
            port:
              number: 80
```

### Database Deployments

```yaml
# postgresql.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgresql
  namespace: phishcatcher
spec:
  serviceName: postgresql
  replicas: 1
  selector:
    matchLabels:
      app: postgresql
  template:
    metadata:
      labels:
        app: postgresql
    spec:
      containers:
      - name: postgresql
        image: postgres:15
        env:
        - name: POSTGRES_DB
          value: phishcatcher
        - name: POSTGRES_USER
          value: phishcatcher
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: phishcatcher-secrets
              key: POSTGRES_PASSWORD
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 20Gi
```

### Deploy to Kubernetes

```bash
# Apply all configurations
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f postgresql.yaml
kubectl apply -f mongodb.yaml
kubectl apply -f redis.yaml
kubectl apply -f backend-deployment.yaml
kubectl apply -f frontend-deployment.yaml
kubectl apply -f ingress.yaml

# Check deployment status
kubectl get pods -n phishcatcher
kubectl get services -n phishcatcher
kubectl get ingress -n phishcatcher
```

## Monitoring and Logging

### Prometheus Configuration

```yaml
# prometheus.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: phishcatcher
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
    - job_name: 'phishcatcher-backend'
      static_configs:
      - targets: ['phishcatcher-backend-service:80']
      metrics_path: /metrics
    - job_name: 'postgres'
      static_configs:
      - targets: ['postgresql:5432']
```

### Grafana Dashboards

1. **Import Pre-built Dashboards**
   - FastAPI Dashboard
   - PostgreSQL Dashboard
   - MongoDB Dashboard
   - Redis Dashboard

2. **Create Custom Dashboard**
   - API response times
   - Analysis processing times
   - User activity metrics
   - Error rates

### Log Aggregation

```yaml
# fluentd.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
  namespace: phishcatcher
spec:
  selector:
    matchLabels:
      name: fluentd
  template:
    metadata:
      labels:
        name: fluentd
    spec:
      containers:
      - name: fluentd
        image: fluent/fluentd-kubernetes-daemonset:v1-debian-elasticsearch
        env:
        - name: FLUENT_ELASTICSEARCH_HOST
          value: "elasticsearch.logging.svc.cluster.local"
        - name: FLUENT_ELASTICSEARCH_PORT
          value: "9200"
        volumeMounts:
        - name: varlog
          mountPath: /var/log
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
      - name: varlibdockercontainers
        hostPath:
          path: /var/lib/docker/containers
```

## Backup and Recovery

### Database Backups

```bash
# PostgreSQL Backup
kubectl exec -n phishcatcher deployment/postgresql -- pg_dump -U phishcatcher phishcatcher > backup.sql

# MongoDB Backup
kubectl exec -n phishcatcher deployment/mongodb -- mongodump --db phishcatcher --out /backup

# Automated Backup Script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
kubectl exec -n phishcatcher deployment/postgresql -- pg_dump -U phishcatcher phishcatcher | gzip > /backups/postgres_${DATE}.sql.gz
kubectl exec -n phishcatcher deployment/mongodb -- mongodump --db phishcatcher --gzip --archive=/backups/mongodb_${DATE}.gz
```

### Restore Procedure

```bash
# PostgreSQL Restore
kubectl exec -i -n phishcatcher deployment/postgresql -- psql -U phishcatcher phishcatcher < backup.sql

# MongoDB Restore
kubectl exec -i -n phishcatcher deployment/mongodb -- mongorestore --db phishcatcher --gzip --archive=/backup/mongodb_backup.gz
```

## Security Considerations

### Network Security
- Use private networks for database communication
- Implement firewall rules
- Enable SSL/TLS termination
- Use VPN for admin access

### Application Security
- Regularly update dependencies
- Implement rate limiting
- Use secrets management
- Enable audit logging

### Infrastructure Security
- Regular security scans
- Implement intrusion detection
- Use read-only file systems where possible
- Enable automatic security updates

## Performance Optimization

### Database Optimization
```sql
-- PostgreSQL Indexes
CREATE INDEX CONCURRENTLY idx_analysis_jobs_user_id ON analysis_jobs(user_id);
CREATE INDEX CONCURRENTLY idx_analysis_jobs_created_at ON analysis_jobs(created_at);
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);

-- MongoDB Indexes
db.analysis_results.createIndex({"job_id": 1}, {unique: true});
db.analysis_results.createIndex({"created_at": -1});
```

### Caching Strategy
- Redis for session storage
- CDN for static assets
- Application-level caching
- Database query caching

### Horizontal Scaling
- Use load balancers
- Implement auto-scaling
- Container orchestration
- Geographic distribution

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check database connectivity
   kubectl exec -it -n phishcatcher deployment/postgresql -- psql -U phishcatcher -d phishcatcher
   
   # Check logs
   kubectl logs -n phishcatcher deployment/phishcatcher-backend
   ```

2. **High Memory Usage**
   ```bash
   # Monitor resource usage
   kubectl top pods -n phishcatcher
   
   # Adjust resource limits
   kubectl edit deployment phishcatcher-backend -n phishcatcher
   ```

3. **Slow API Response**
   ```bash
   # Check database performance
   kubectl exec -n phishcatcher deployment/postgresql -- psql -U phishcatcher -d phishcatcher -c "SELECT * FROM pg_stat_activity;"
   
   # Analyze slow queries
   kubectl exec -n phishcatcher deployment/postgresql -- psql -U phishcatcher -d phishcatcher -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
   ```

### Health Checks

```bash
# API Health
curl -f https://api.yourdomain.com/health || exit 1

# Database Health
kubectl exec -n phishcatcher deployment/postgresql -- pg_isready -U phishcatcher

# Service Health
kubectl get pods -n phishcatcher -o wide
kubectl get services -n phishcatcher
```

## Maintenance

### Rolling Updates

```bash
# Update backend
kubectl set image deployment/phishcatcher-backend backend=phishcatcher/backend:v1.1.0 -n phishcatcher

# Update frontend
kubectl set image deployment/phishcatcher-frontend frontend=phishcatcher/frontend:v1.1.0 -n phishcatcher

# Monitor rollout
kubectl rollout status deployment/phishcatcher-backend -n phishcatcher
```

### Scheduled Maintenance

```yaml
# maintenance-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-maintenance
  namespace: phishcatcher
spec:
  schedule: "0 2 * * 0"  # Weekly on Sunday at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: maintenance
            image: postgres:15
            command:
            - /bin/bash
            - -c
            - |
              psql -h postgresql -U phishcatcher -d phishcatcher -c "VACUUM ANALYZE;"
              psql -h postgresql -U phishcatcher -d phishcatcher -c "REINDEX DATABASE phishcatcher;"
          restartPolicy: OnFailure
```

## Disaster Recovery

### Recovery Plan
1. **Assessment**: Determine scope of impact
2. **Communication**: Notify stakeholders
3. **Isolation**: Prevent further damage
4. **Recovery**: Restore from backups
5. **Verification**: Test system functionality
6. **Post-mortem**: Document and learn

### Recovery Procedures

```bash
# Complete System Recovery
#!/bin/bash
# 1. Restore databases
kubectl apply -f postgresql.yaml
kubectl apply -f mongodb.yaml
kubectl wait --for=condition=ready pod -l app=postgresql -n phishcatcher --timeout=300s
kubectl exec -i -n phishcatcher deployment/postgresql -- psql -U phishcatcher phishcatcher < /backups/latest_postgres.sql

# 2. Restore application
kubectl apply -f backend-deployment.yaml
kubectl apply -f frontend-deployment.yaml

# 3. Verify functionality
curl -f https://api.yourdomain.com/health
curl -f https://yourdomain.com
```

This deployment guide provides comprehensive instructions for deploying PhishCatcher in various environments with proper monitoring, security, and disaster recovery procedures.
