# PhishCatcher Architecture Documentation

## Overview

PhishCatcher is built on a microservices architecture with a focus on security, scalability, and maintainability. The system uses modern technologies and follows best practices for distributed systems design.

## System Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   External      │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   Services      │
│                 │    │                 │    │                 │
│ - UI Components │    │ - REST API      │    │ - Google OAuth  │
│ - State Mgmt    │    │ - Auth Service  │    │ - SendGrid      │
│ - Client Logic  │    │ - ML Pipeline   │    │ - VirusTotal    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Data Layer    │
                       │                 │
                       │ - PostgreSQL    │
                       │ - MongoDB       │
                       │ - Redis         │
                       └─────────────────┘
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer                           │
│                      (Nginx/HAProxy)                          │
└─────────────────────┬───────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Frontend  │ │   Backend   │ │   Admin     │
│  Containers │ │  Containers │ │  Containers │
│             │ │             │ │             │
│ - React App │ │ - FastAPI   │ │ - Grafana   │
│ - Nginx     │ │ - Workers   │ │ - Prometheus│
└─────────────┘ └─────────────┘ └─────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Database Cluster                          │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │ PostgreSQL  │  │   MongoDB   │  │    Redis    │           │
│  │ (Primary)   │  │ (Replica)   │  │ (Cluster)   │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Backend Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| **API Framework** | FastAPI | High-performance async API framework |
| **ASGI Server** | Uvicorn | ASGI server for Python async |
| **Database ORM** | SQLAlchemy | SQL toolkit and ORM |
| **Migration Tool** | Alembic | Database migration management |
| **Task Queue** | Celery | Distributed task queue |
| **Message Broker** | Redis | Message broker and caching |
| **ML Framework** | scikit-learn | Machine learning algorithms |
| **Email Parser** | email-parser | Email content extraction |
| **OAuth Library** | authlib | OAuth 2.0 implementation |

### Frontend Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Framework** | React 18 | User interface library |
| **Build Tool** | Vite | Fast build tool |
| **Language** | TypeScript | Type-safe JavaScript |
| **Styling** | TailwindCSS | Utility-first CSS framework |
| **State Management** | Zustand | Lightweight state management |
| **HTTP Client** | Axios | HTTP request library |
| **Routing** | React Router | Client-side routing |
| **UI Components** | Radix UI | Accessible component primitives |

### Database Technologies

| Database | Purpose | Features |
|----------|---------|----------|
| **PostgreSQL** | Primary data storage | ACID compliance, JSON support |
| **MongoDB** | Analysis results storage | Document store, flexible schema |
| **Redis** | Caching and sessions | In-memory, pub/sub support |

### Infrastructure Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Containerization** | Docker | Application containerization |
| **Orchestration** | Kubernetes | Container orchestration |
| **Load Balancer** | Nginx | HTTP load balancing |
| **Monitoring** | Prometheus | Metrics collection |
| **Visualization** | Grafana | Metrics dashboard |
| **Logging** | ELK Stack | Log aggregation |
| **CI/CD** | GitHub Actions | Continuous integration |

## Data Architecture

### Data Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Email     │    │   Parser    │    │  Feature    │
│   Upload    │───►│             │───►│ Extractor   │
│             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
                                            │
                                            ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Results   │◄───│   ML Model  │◄───│  Features   │
│   Storage   │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
```

### Database Schema Design

#### PostgreSQL Schema

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    gmail_credentials JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Analysis jobs table
CREATE TABLE analysis_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'pending',
    risk_score INTEGER,
    is_phishing BOOLEAN,
    confidence INTEGER,
    findings TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Audit logs table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    status VARCHAR(20) NOT NULL,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Email providers table
CREATE TABLE email_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    provider_name VARCHAR(50) NOT NULL,
    provider_email VARCHAR(255) NOT NULL,
    credentials JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### MongoDB Schema

```javascript
// Analysis results collection
{
  _id: ObjectId,
  job_id: String, // UUID from PostgreSQL
  analysis_results: {
    sender_analysis: {
      sender_email: String,
      sender_reputation: String,
      domain_age_days: Number,
      spf_record: Boolean,
      dkim_signature: Boolean,
      dmarc_policy: String
    },
    content_analysis: {
      suspicious_keywords: [String],
      urgency_indicators: Boolean,
      grammar_errors: Number,
      personalization: Boolean
    },
    url_analysis: {
      total_urls: Number,
      suspicious_urls: Number,
      url_details: [{
        url: String,
        risk_level: String,
        redirects: Boolean,
        domain_reputation: String
      }]
    },
    findings: [{
      type: String,
      severity: String,
      description: String,
      recommendation: String
    }]
  },
  raw_email_content: String, // For re-analysis
  processing_metadata: {
    model_version: String,
    processing_time_ms: Number,
    feature_extraction_time_ms: Number
  },
  created_at: Date,
  updated_at: Date
}

// ML model metrics collection
{
  _id: ObjectId,
  model_version: String,
  metrics: {
    accuracy: Number,
    precision: Number,
    recall: Number,
    f1_score: Number,
    confusion_matrix: [[Number]]
  },
  training_data_size: Number,
  feature_importance: [{
    feature: String,
    importance: Number
  }],
  created_at: Date
}
```

### Data Relationships

```
Users (1) ──────── (N) AnalysisJobs
  │                     │
  │                     │
  │                     ▼
  │              AnalysisResults (MongoDB)
  │
  │
  └─────── (N) EmailProviders
  │
  └─────── (N) AuditLogs
```

## Security Architecture

### Authentication & Authorization

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │    │   Auth      │    │   Token     │
│   Request   │───►│   Service   │───►│   Service   │
│             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
                           │
                           ▼
                   ┌─────────────┐
                   │   User      │
                   │   Store     │
                   │ (PostgreSQL)│
                   └─────────────┘
```

### Security Layers

1. **Network Security**
   - TLS/SSL encryption
   - VPN access for admin
   - Firewall rules
   - DDoS protection

2. **Application Security**
   - JWT authentication
   - Rate limiting
   - Input validation
   - SQL injection prevention
   - XSS protection

3. **Data Security**
   - Encryption at rest
   - Encryption in transit
   - Data masking
   - Secure backups

4. **Infrastructure Security**
   - Container security
   - Secret management
   - Access control
   - Audit logging

## Microservices Architecture

### Service Decomposition

```
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway                                │
│                    (Authentication)                            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Auth      │ │   Analysis  │ │   Gmail     │
│  Service    │ │  Service    │ │  Service    │
│             │ │             │ │             │
│ - Login     │ │ - Upload     │ │ - OAuth     │
│ - Register  │ │ - Process    │ │ - Fetch     │
│ - Tokens    │ │ - Results    │ │ - Sync      │
└─────────────┘ └─────────────┘ └─────────────┘
        │             │             │
        └─────────────┼─────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Shared Services                           │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │   User      │  │   Email     │  │   ML        │           │
│  │  Service    │  │  Service    │ │  Service    │           │
│  │             │  │             │  │             │           │
│  │ - Profile   │  │ - Parsing   │  │ - Features  │           │
│  │ - Settings  │  │ - Validation│  │ - Scoring   │           │
│  │ - Admin     │  │ - Storage   │  │ - Models    │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Service Communication

#### Synchronous Communication
- **REST APIs** for request-response patterns
- **gRPC** for internal service communication
- **GraphQL** for flexible data queries

#### Asynchronous Communication
- **Message Queues** for background processing
- **Event Streaming** for real-time updates
- **Webhooks** for external integrations

### Service Discovery

```python
# Service registry configuration
SERVICE_REGISTRY = {
    "auth_service": {
        "url": "http://auth-service:8001",
        "health_check": "/health",
        "timeout": 30
    },
    "analysis_service": {
        "url": "http://analysis-service:8002",
        "health_check": "/health",
        "timeout": 60
    },
    "gmail_service": {
        "url": "http://gmail-service:8003",
        "health_check": "/health",
        "timeout": 30
    }
}
```

## Machine Learning Architecture

### ML Pipeline

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Email     │    │   Feature   │    │   Model     │
│   Input     │───►│ Extraction  │───►│ Prediction  │
│             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
                                            │
                                            ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Results   │◄───│   Post-     │◄───│   Risk      │
│   Storage   │    │ Processing  │    │   Scoring   │
│             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
```

### Model Architecture

```python
# Feature extraction pipeline
class FeatureExtractor:
    def __init__(self):
        self.extractors = [
            SenderFeatureExtractor(),
            ContentFeatureExtractor(),
            URLFeatureExtractor(),
            StructuralFeatureExtractor()
        ]
    
    def extract(self, email_content):
        features = {}
        for extractor in self.extractors:
            features.update(extractor.extract(email_content))
        return features

# ML model pipeline
class PhishingDetector:
    def __init__(self):
        self.feature_extractor = FeatureExtractor()
        self.model = joblib.load('models/phishing_model.pkl')
        self.scaler = joblib.load('models/feature_scaler.pkl')
    
    def predict(self, email_content):
        # Extract features
        features = self.feature_extractor.extract(email_content)
        
        # Scale features
        scaled_features = self.scaler.transform([features])
        
        # Make prediction
        prediction = self.model.predict(scaled_features)[0]
        probability = self.model.predict_proba(scaled_features)[0]
        
        return {
            'is_phishing': bool(prediction),
            'confidence': float(max(probability)),
            'risk_score': self._calculate_risk_score(probability)
        }
```

### Feature Engineering

#### Sender Features
- Domain reputation
- Email authentication (SPF, DKIM, DMARC)
- Domain age
- Sender history

#### Content Features
- Keyword analysis
- Urgency indicators
- Grammar and spelling errors
- Personalization level

#### URL Features
- URL reputation
- Redirect chains
- IP address usage
- Shortened URL detection

#### Structural Features
- HTML structure analysis
- Email formatting
- Attachment analysis
- Header analysis

## Scalability Architecture

### Horizontal Scaling

```
┌─────────────────────────────────────────────────────────────────┐
│                      Load Balancer                             │
│                      (Round Robin)                            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Backend   │ │   Backend   │ │   Backend   │
│ Instance 1  │ │ Instance 2  │ │ Instance 3  │
│             │ │             │ │             │
│ - FastAPI   │ │ - FastAPI   │ │ - FastAPI   │
│ - Workers   │ │ - Workers   │ │ - Workers   │
└─────────────┘ └─────────────┘ └─────────────┘
        │             │             │
        └─────────────┼─────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Database Cluster                           │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │ PostgreSQL  │  │ PostgreSQL  │  │ PostgreSQL  │           │
│  │  Primary    │  │  Replica 1  │  │  Replica 2  │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Caching Strategy

#### Multi-Level Caching

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │    │   CDN       │    │   App       │
│   Cache     │───►│   Cache     │───►│   Cache     │
│ (Browser)   │    │ (CloudFlare)│    │ (Redis)     │
└─────────────┘    └─────────────┘    └─────────────┘
                                            │
                                            ▼
                                    ┌─────────────┐
                                    │   Database  │
                                    │   Cache     │
                                    │ (PostgreSQL)│
                                    └─────────────┘
```

#### Cache Implementation

```python
# Redis caching decorator
def cache_result(key_prefix: str, expiration: int = 3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = await redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            await redis_client.setex(
                cache_key, 
                expiration, 
                json.dumps(result, default=str)
            )
            
            return result
        return wrapper
    return decorator

# Usage
@cache_result("user_profile", expiration=1800)
async def get_user_profile(user_id: str):
    # Database query
    pass
```

### Database Scaling

#### Read Replicas

```python
# Database routing configuration
class DatabaseRouter:
    def __init__(self):
        self.primary_db = create_engine(PRIMARY_DB_URL)
        self.replica_dbs = [
            create_engine(url) for url in REPLICA_DB_URLS
        ]
    
    def get_read_session(self):
        """Get read-only session from replica."""
        replica = random.choice(self.replica_dbs)
        return sessionmaker(bind=replica)()
    
    def get_write_session(self):
        """Get write session from primary."""
        return sessionmaker(bind=self.primary_db)()
```

#### Sharding Strategy

```python
# User-based sharding
def get_shard_key(user_id: str) -> int:
    """Determine shard based on user ID."""
    return hash(user_id) % NUM_SHARDS

def get_database_connection(user_id: str):
    """Get database connection for specific shard."""
    shard_id = get_shard_key(user_id)
    return SHARD_CONNECTIONS[shard_id]
```

## Monitoring & Observability

### Monitoring Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Application                                │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │   API       │  │   Workers   │  │   Database  │           │
│  │  Services   │  │             │  │             │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Metrics Collection                            │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │ Prometheus  │  │   Grafana   │  │   AlertMgr  │           │
│  │             │  │             │  │             │           │
│  │ - Metrics   │  │ - Dashboards│  │ - Alerts    │           │
│  │ - Storage   │  │ - Visualization│ │ - Notifications│        │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Key Metrics

#### Application Metrics
- Request rate and latency
- Error rates by endpoint
- Active user sessions
- Queue depth and processing time
- Memory and CPU usage

#### Business Metrics
- Analysis completion rate
- Phishing detection accuracy
- User engagement metrics
- Gmail integration success rate

#### Infrastructure Metrics
- Database connection pool usage
- Cache hit rates
- Network latency
- Disk I/O and storage usage

### Logging Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Applications                              │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │   API       │  │   Workers   │  │   Frontend  │           │
│  │  Services   │  │             │  │             │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Log Aggregation                           │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │   Fluentd   │  │ Elasticsearch│  │   Kibana    │           │
│  │             │  │             │  │             │           │
│  │ - Collector │  │ - Storage   │  │ - Search    │           │
│  │ - Parser    │  │ - Indexing  │  │ - Visualization│          │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Distributed Tracing

```python
# OpenTelemetry configuration
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Setup tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)

span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Usage in code
@tracer.start_as_current_span("process_email")
async def process_email(email_id: str):
    with tracer.start_as_current_span("extract_features"):
        features = await extract_features(email_id)
    
    with tracer.start_as_current_span("ml_prediction"):
        result = await predict_phishing(features)
    
    return result
```

## Deployment Architecture

### Container Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                      Docker Registry                           │
│                    (ECR / Docker Hub)                         │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Kubernetes Cluster                        │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │   Pods      │  │   Pods      │  │   Pods      │           │
│  │ (Frontend)  │  │ (Backend)   │  │ (Database)  │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Ingress Controller                        │
│                      (Nginx / Traefik)                         │
└─────────────────────────────────────────────────────────────────┘
```

### CI/CD Pipeline

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Code      │    │   Build     │    │   Test      │
│   Commit    │───►│   Stage     │───►│   Stage     │
│             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
                                            │
                                            ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Deploy    │◄───│   Security   │◄───│   Quality   │
│   Stage     │    │   Scan       │    │   Gate      │
│             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
        │
        ▼
┌─────────────┐
│ Production  │
│  Deploy     │
│             │
└─────────────┘
```

## Future Architecture Considerations

### Event-Driven Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Event     │    │   Event     │    │   Event     │
│   Producer  │───►│   Bus       │───►│  Consumer   │
│             │    │ (Kafka)     │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
```

### Serverless Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      Serverless Layer                           │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │   AWS       │  │   AWS       │  │   AWS       │           │
│  │  Lambda     │  │  Lambda     │  │  Lambda     │           │
│  │ (Image Proc)│  │ (Email Send)│  │ (Webhooks)  │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Microservice Mesh

```
┌─────────────────────────────────────────────────────────────────┐
│                      Service Mesh                              │
│                     (Istio / Linkerd)                         │
└─────────────────────┬───────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Service   │ │   Service   │ │   Service   │
│     A       │ │     B       │ │     C       │
└─────────────┘ └─────────────┘ └─────────────┘
```

This architecture documentation provides a comprehensive overview of the PhishCatcher system design, covering all major components and their interactions. The architecture is designed to be scalable, secure, and maintainable while supporting the complex requirements of email phishing detection.
