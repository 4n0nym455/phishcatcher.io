# PhishCatcher Backend

A comprehensive, security-focused backend API for the PhishCatcher email phishing detection system. Built with FastAPI, PostgreSQL, MongoDB, Redis, and machine learning.

## Features

- **Authentication & Security**
  - JWT-based authentication with refresh tokens
  - OTP (One-Time Password) verification
  - Password strength validation
  - Account lockout protection
  - Google OAuth integration
  - Comprehensive audit logging

- **Email Analysis**
  - ML-based phishing detection using XGBoost
  - Real-time email parsing and feature extraction
  - Risk scoring (0-100)
  - Detailed findings with recommendations
  - Support for .eml, .msg, and .txt files

- **Gmail Integration**
  - OAuth 2.0 authentication
  - Email fetching and synchronization
  - Push notifications support
  - Automatic token refresh

- **Data Storage**
  - PostgreSQL for user data and metadata
  - MongoDB for analysis results
  - Redis for caching and sessions
  - MinIO for file storage

- **Background Processing**
  - Celery task queue for async analysis
  - Flower monitoring dashboard
  - Scheduled sync tasks

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│                    (React Frontend)                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                    ┌───────▼───────┐
                    │   FastAPI     │
                    │     API       │
                    └───────┬───────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼───────┐  ┌───────▼───────┐  ┌───────▼───────┐
│  PostgreSQL   │  │    MongoDB    │  │     Redis     │
│  (Users,      │  │  (Analysis    │  │  (Cache,      │
│   Metadata)   │  │   Results)    │  │   Sessions)   │
└───────────────┘  └───────────────┘  └───────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                    ┌───────▼───────┐
                    │    Celery     │
                    │    Worker     │
                    └───────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Google OAuth credentials (for Gmail integration)

### Using Docker Compose

1. Clone the repository:
```bash
git clone <repository-url>
cd phishcatcher-backend
```

2. Create environment file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start all services:
```bash
docker-compose up -d
```

4. Access the services:
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Flower (Celery Monitor): http://localhost:5555
- MinIO Console: http://localhost:9001

### Local Development

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start databases:
```bash
docker-compose up -d postgres mongodb redis minio
```

4. Run migrations:
```bash
alembic upgrade head
```

5. Start the API:
```bash
uvicorn app.main:app --reload
```

6. Start Celery worker (in another terminal):
```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login (returns OTP) |
| POST | `/api/v1/auth/verify-otp` | Verify OTP and get tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Logout user |
| POST | `/api/v1/auth/forgot-password` | Request password reset |
| POST | `/api/v1/auth/reset-password` | Reset password with token |
| GET | `/api/v1/auth/google/url` | Get Google OAuth URL |
| GET | `/api/v1/auth/google/callback` | Google OAuth callback |
| GET | `/api/v1/auth/me` | Get current user info |
| PUT | `/api/v1/auth/me/password` | Change password |

### Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/analysis/upload` | Upload email for analysis |
| GET | `/api/v1/analysis/history` | Get analysis history |
| GET | `/api/v1/analysis/{id}` | Get analysis results |
| GET | `/api/v1/analysis/{id}/status` | Get analysis status |
| DELETE | `/api/v1/analysis/{id}` | Delete analysis |
| GET | `/api/v1/analysis/{id}/download` | Download report |
| GET | `/api/v1/analysis/reports/weekly` | Get weekly report |

### Email Providers

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/providers/gmail/auth-url` | Get Gmail OAuth URL |
| POST | `/api/v1/providers/gmail/connect` | Connect Gmail account |
| GET | `/api/v1/providers` | List connected providers |
| GET | `/api/v1/providers/{id}` | Get provider details |
| PUT | `/api/v1/providers/{id}` | Update provider |
| POST | `/api/v1/providers/{id}/sync` | Sync emails |
| GET | `/api/v1/providers/{id}/health` | Check provider health |
| DELETE | `/api/v1/providers/{id}` | Disconnect provider |

### Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/users` | List all users |
| GET | `/api/v1/admin/users/{id}` | Get user details |
| PUT | `/api/v1/admin/users/{id}` | Update user |
| DELETE | `/api/v1/admin/users/{id}` | Delete user |
| GET | `/api/v1/admin/stats` | Get system statistics |
| GET | `/api/v1/admin/model-info` | Get ML model info |
| POST | `/api/v1/admin/model/retrain` | Retrain ML model |
| GET | `/api/v1/admin/audit-logs` | Get audit logs |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check |
| GET | `/health/ready` | Readiness probe |
| GET | `/health/live` | Liveness probe |
| GET | `/health/detailed` | Detailed health check |

## Machine Learning

### Model Architecture

The phishing detection model uses XGBoost with the following features:

**Header Features:**
- SPF/DKIM/DMARC authentication results
- Reply-To mismatch detection
- Domain validation

**Content Features:**
- Urgency keyword count
- Suspicious phrase detection
- HTML-to-text ratio
- Form and script presence

**Link Features:**
- URL length and structure
- IP-based URLs
- URL shorteners
- Suspicious TLDs

**Attachment Features:**
- Executable file detection
- Script file detection
- File hash analysis

### Training the Model

```python
from app.ml.phishing_detector import PhishingDetector
from app.ml.feature_extractor import FeatureExtractor

# Load training data
# X: feature matrix, y: labels (0=safe, 1=phishing)

# Train model
detector = PhishingDetector()
metrics = detector.train(X, y)

# Save model
detector.save_model()

print(f"Accuracy: {metrics['accuracy']:.4f}")
print(f"F1 Score: {metrics['f1_score']:.4f}")
```

## Security Features

### Authentication
- Bcrypt password hashing (12 rounds)
- JWT tokens with short expiry
- OTP verification for login
- Account lockout after failed attempts

### Data Protection
- AES-256 encryption for sensitive data
- TLS 1.3 for all communications
- Field-level encryption for tokens
- Secure session management

### API Security
- Rate limiting (100 req/min for API, 5 req/min for auth)
- Input validation with Pydantic
- CORS protection
- SQL injection prevention
- XSS protection

### Audit Logging
All sensitive operations are logged:
- Authentication attempts
- User management actions
- Analysis operations
- Provider connections

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key | Required |
| `DATABASE_URL` | PostgreSQL connection | Required |
| `MONGODB_URL` | MongoDB connection | Required |
| `REDIS_URL` | Redis connection | Required |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Optional |
| `GOOGLE_CLIENT_SECRET` | Google OAuth secret | Optional |
| `VIRUSTOTAL_API_KEY` | VirusTotal API key | Optional |
| `SMTP_HOST` | SMTP server host | Optional |

See `.env.example` for complete list.

## Testing

Run tests with pytest:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py
```

## Deployment

### Production Checklist

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Set `DEBUG=false` and `ENVIRONMENT=production`
- [ ] Configure production databases
- [ ] Set up SSL/TLS certificates
- [ ] Configure Google OAuth credentials
- [ ] Set up email (SMTP) for OTP
- [ ] Configure threat intelligence API keys
- [ ] Set up monitoring and logging
- [ ] Configure backups

### Kubernetes Deployment

```yaml
# Example deployment configuration
apiVersion: apps/v1
kind: Deployment
metadata:
  name: phishcatcher-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: phishcatcher-api
  template:
    metadata:
      labels:
        app: phishcatcher-api
    spec:
      containers:
      - name: api
        image: phishcatcher-api:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: phishcatcher-config
        - secretRef:
            name: phishcatcher-secrets
```

## Monitoring

### Health Checks
- `/health` - Basic health
- `/health/ready` - Readiness probe
- `/health/live` - Liveness probe
- `/health/detailed` - Component status

### Celery Monitoring
- Flower dashboard: http://localhost:5555
- Task queue monitoring
- Worker status

### Metrics
- API response times
- Error rates
- ML inference times
- Queue lengths

## Troubleshooting

### Common Issues

**Database connection errors:**
```bash
# Check database status
docker-compose ps postgres

# View logs
docker-compose logs postgres
```

**Celery worker not processing tasks:**
```bash
# Restart worker
docker-compose restart worker

# Check worker logs
docker-compose logs worker
```

**ML model not loaded:**
```bash
# Check models directory
ls -la models/

# Retrain model if needed
python -c "from app.ml.phishing_detector import PhishingDetector; d = PhishingDetector(); d.save_model()"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support, email support@phishcatcher.io or open an issue on GitHub.

## Acknowledgments

- FastAPI framework
- XGBoost machine learning library
- Google Gmail API
- All open-source contributors
