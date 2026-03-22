# PhishCatcher Development Guide

## Overview

This guide covers setting up a development environment, contributing to the PhishCatcher project, and following best practices for code quality and collaboration.

## Development Environment Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git
- PostgreSQL 15+ (for local development)
- MongoDB 6.0+ (for local development)
- Redis 7.0+ (for local development)

### Backend Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/phishcatcher.git
   cd phishcatcher/phishcatcher-backend
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv .venv
   
   # macOS/Linux
   source .venv/bin/activate
   
   # Windows
   .venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

4. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

5. **Database Setup**
   ```bash
   # Start local databases with Docker
   docker-compose -f docker-compose.dev.yml up -d postgres mongodb redis
   
   # Run migrations
   alembic upgrade head
   
   # Create admin user
   python scripts/create_admin.py
   ```

6. **Start Development Server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Navigate to Frontend Directory**
   ```bash
   cd ../phishcatcher-frontend/app
   ```

2. **Install Dependencies**
   ```bash
   npm install
   ```

3. **Environment Configuration**
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your configuration
   ```

4. **Start Development Server**
   ```bash
   npm run dev
   ```

## Project Structure

### Backend Structure

```
phishcatcher-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py              # Configuration management
│   ├── database.py             # Database connections and sessions
│   ├── core/                   # Core functionality
│   │   ├── __init__.py
│   │   ├── auth.py             # Authentication logic
│   │   ├── security.py         # Security utilities
│   │   └── session_manager.py  # Session management
│   ├── ml/                     # Machine learning components
│   │   ├── __init__.py
│   │   ├── phishing_detector.py
│   │   ├── email_parser.py
│   │   ├── feature_extractor.py
│   │   └── risk_scorer.py
│   ├── models/                 # Database models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── analysis_job.py
│   │   └── audit_log.py
│   ├── schemas/                # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── analysis.py
│   │   └── user.py
│   ├── services/               # Business logic
│   │   ├── __init__.py
│   │   ├── email.py
│   │   ├── gmail.py
│   │   └── security.py
│   ├── routers/                # API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── analysis.py
│   │   ├── gmail.py
│   │   └── admin.py
│   ├── middleware/             # Custom middleware
│   │   ├── __init__.py
│   │   └── session_middleware.py
│   └── tasks/                  # Background tasks
│       ├── __init__.py
│       ├── analysis.py
│       └── celery_app.py
├── alembic/                    # Database migrations
├── scripts/                    # Utility scripts
├── tests/                      # Test files
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
└── alembic.ini                 # Alembic configuration
```

### Frontend Structure

```
phishcatcher-frontend/app/
├── public/                     # Static assets
├── src/
│   ├── components/             # Reusable components
│   │   ├── ui/                 # UI components (buttons, forms, etc.)
│   │   ├── layout/             # Layout components
│   │   └── common/             # Common components
│   ├── pages/                  # Page components
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── analysis/
│   │   └── settings/
│   ├── hooks/                  # Custom React hooks
│   ├── services/               # API services
│   ├── utils/                  # Utility functions
│   ├── types/                  # TypeScript type definitions
│   ├── store/                  # State management
│   └── styles/                 # Global styles
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## Development Workflow

### Git Workflow

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write code following style guidelines
   - Add tests for new functionality
   - Update documentation

3. **Run Tests**
   ```bash
   # Backend tests
   cd phishcatcher-backend
   pytest tests/ -v --cov=app
   
   # Frontend tests
   cd phishcatcher-frontend/app
   npm test
   npm run lint
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   # Create Pull Request on GitHub
   ```

### Code Style Guidelines

#### Python (Backend)

- **PEP 8** compliance
- **Black** for code formatting
- **isort** for import sorting
- **mypy** for type checking
- **flake8** for linting

```bash
# Format code
black app/
isort app/

# Type checking
mypy app/

# Linting
flake8 app/
```

**Code Example:**
```python
"""User service module."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash


class UserService:
    """Service for user operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize user service."""
        self.db = db

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        hashed_password = get_password_hash(user_data.password)
        
        user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            password_hash=hashed_password,
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
```

#### TypeScript (Frontend)

- **Prettier** for code formatting
- **ESLint** for linting
- **TypeScript** strict mode
- **Consistent naming conventions**

```bash
# Format code
npm run format

# Lint code
npm run lint

# Type check
npm run type-check
```

**Code Example:**
```typescript
/** User service for API calls. */
import { apiClient } from '@/lib/api-client';
import { User, UserCreate, UserUpdate } from '@/types/user';

export class UserService {
  /** Create a new user. */
  static async createUser(userData: UserCreate): Promise<User> {
    const response = await apiClient.post<User>('/users', userData);
    return response.data;
  }

  /** Get user by ID. */
  static async getUserById(userId: string): Promise<User> {
    const response = await apiClient.get<User>(`/users/${userId}`);
    return response.data;
  }

  /** Update user profile. */
  static async updateUser(userId: string, userData: UserUpdate): Promise<User> {
    const response = await apiClient.put<User>(`/users/${userId}`, userData);
    return response.data;
  }
}
```

## Testing

### Backend Testing

#### Unit Tests
```python
# tests/test_user_service.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user import UserService
from app.schemas.user import UserCreate


@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    """Test user creation."""
    user_service = UserService(db_session)
    
    user_data = UserCreate(
        email="test@example.com",
        full_name="Test User",
        password="SecurePassword123!"
    )
    
    user = await user_service.create_user(user_data)
    
    assert user.email == user_data.email
    assert user.full_name == user_data.full_name
    assert user.password_hash is not None
    assert user.id is not None
```

#### Integration Tests
```python
# tests/test_auth_api.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_user_registration(client: AsyncClient):
    """Test user registration endpoint."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "full_name": "Test User"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "User registered successfully"
    assert data["user"]["email"] == "test@example.com"
```

#### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_user_service.py

# Run with verbose output
pytest -v
```

### Frontend Testing

#### Unit Tests
```typescript
// src/components/__tests__/Button.test.tsx
import { render, screen } from '@testing-library/react';
import { Button } from '../Button';

describe('Button', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    
    screen.getByText('Click me').click();
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
```

#### Integration Tests
```typescript
// src/pages/__tests__/Dashboard.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { Dashboard } from '../Dashboard';

// Mock API calls
jest.mock('@/services/analysis');

describe('Dashboard', () => {
  it('displays user statistics', async () => {
    render(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('Total Analyses')).toBeInTheDocument();
    });
  });
});
```

#### Running Tests
```bash
# Run all tests
npm test

# Run in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage

# Run specific test file
npm test Button.test.tsx
```

## Database Development

### Migrations

1. **Create Migration**
   ```bash
   alembic revision --autogenerate -m "Add new feature"
   ```

2. **Review Migration**
   ```bash
   cat alembic/versions/xxx_add_new_feature.py
   ```

3. **Apply Migration**
   ```bash
   alembic upgrade head
   ```

4. **Downgrade Migration**
   ```bash
   alembic downgrade -1
   ```

### Database Schema

#### Models Example
```python
# app/models/analysis_job.py
from sqlalchemy import Column, String, DateTime, Integer, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class AnalysisJob(Base):
    """Analysis job model."""
    
    __tablename__ = "analysis_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(String(20), default="pending", index=True)
    risk_score = Column(Integer, nullable=True)
    is_phishing = Column(Boolean, nullable=True)
    confidence = Column(Integer, nullable=True)
    findings = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
```

## API Development

### Adding New Endpoints

1. **Create Schema**
```python
# app/schemas/feature.py
from pydantic import BaseModel
from typing import Optional


class FeatureCreate(BaseModel):
    name: str
    description: str
    enabled: bool = True


class FeatureResponse(BaseModel):
    id: str
    name: str
    description: str
    enabled: bool
    created_at: str
    
    class Config:
        from_attributes = True
```

2. **Create Service**
```python
# app/services/feature.py
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feature import Feature
from app.schemas.feature import FeatureCreate, FeatureResponse


class FeatureService:
    async def create_feature(
        self, db: AsyncSession, feature_data: FeatureCreate
    ) -> FeatureResponse:
        # Implementation
        pass
    
    async def get_features(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[FeatureResponse]:
        # Implementation
        pass
```

3. **Create Router**
```python
# app/routers/feature.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.feature import FeatureService
from app.schemas.feature import FeatureCreate, FeatureResponse

router = APIRouter(prefix="/features", tags=["features"])


@router.post("/", response_model=FeatureResponse)
async def create_feature(
    feature_data: FeatureCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new feature."""
    service = FeatureService()
    return await service.create_feature(db, feature_data)


@router.get("/", response_model=List[FeatureResponse])
async def get_features(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get all features."""
    service = FeatureService()
    return await service.get_features(db, skip=skip, limit=limit)
```

4. **Register Router**
```python
# app/main.py
from app.routers import feature

app.include_router(feature.router, prefix="/api/v1")
```

## Frontend Development

### Component Development

#### Creating Components
```typescript
// src/components/ui/Button.tsx
import { forwardRef } from 'react';
import { cn } from '@/lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline';
  size?: 'default' | 'sm' | 'lg';
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => {
    return (
      <button
        className={cn(
          'inline-flex items-center justify-center rounded-md font-medium transition-colors',
          {
            'bg-primary text-primary-foreground hover:bg-primary/90': variant === 'default',
            'bg-destructive text-destructive-foreground hover:bg-destructive/90': variant === 'destructive',
            'border border-input hover:bg-accent hover:text-accent-foreground': variant === 'outline',
          },
          {
            'h-10 px-4 py-2': size === 'default',
            'h-9 px-3': size === 'sm',
            'h-11 px-8': size === 'lg',
          },
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);

Button.displayName = 'Button';
```

#### Custom Hooks
```typescript
// src/hooks/useAuth.ts
import { useState, useEffect } from 'react';
import { User } from '@/types/user';
import { authService } from '@/services/auth';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      try {
        const currentUser = await authService.getCurrentUser();
        setUser(currentUser);
      } catch (error) {
        console.error('Auth initialization failed:', error);
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    const response = await authService.login(email, password);
    setUser(response.user);
    return response;
  };

  const logout = async () => {
    await authService.logout();
    setUser(null);
  };

  return {
    user,
    loading,
    login,
    logout,
  };
}
```

## Machine Learning Development

### Model Training

```python
# scripts/train_model.py
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

def train_phishing_model():
    """Train phishing detection model."""
    # Load dataset
    df = pd.read_csv('data/phishing_dataset.csv')
    
    # Feature engineering
    X = df.drop('is_phishing', axis=1)
    y = df['is_phishing']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Train model
    model = GradientBoostingClassifier(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=3,
        random_state=42
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred))
    
    # Save model
    joblib.dump(model, 'models/phishing_model.pkl')
    
    return model

if __name__ == "__main__":
    train_phishing_model()
```

### Feature Extraction

```python
# app/ml/feature_extractor.py
import re
from typing import Dict, Any
from email import message_from_string
from urllib.parse import urlparse


class FeatureExtractor:
    """Extract features from email for phishing detection."""
    
    def extract_features(self, email_content: str) -> Dict[str, Any]:
        """Extract all features from email."""
        email_msg = message_from_string(email_content)
        
        features = {
            'sender_features': self._extract_sender_features(email_msg),
            'content_features': self._extract_content_features(email_msg),
            'url_features': self._extract_url_features(email_msg),
            'structural_features': self._extract_structural_features(email_msg),
        }
        
        return self._flatten_features(features)
    
    def _extract_sender_features(self, email_msg) -> Dict[str, Any]:
        """Extract sender-related features."""
        sender = email_msg.get('From', '')
        return {
            'sender_domain_age': self._get_domain_age(sender),
            'sender_has_spf': self._check_spf_record(sender),
            'sender_has_dkim': self._check_dkim_signature(email_msg),
            'sender_email_suspicious': self._is_suspicious_email(sender),
        }
    
    def _extract_content_features(self, email_msg) -> Dict[str, Any]:
        """Extract content-related features."""
        body = self._get_email_body(email_msg)
        return {
            'urgency_words_count': len(re.findall(r'\b(urgent|immediate|asap)\b', body, re.I)),
            'suspicious_links_count': len(re.findall(r'(click|verify|confirm|update)', body, re.I)),
            'grammar_errors': self._count_grammar_errors(body),
            'personalization': self._has_personalization(body),
        }
    
    def _extract_url_features(self, email_msg) -> Dict[str, Any]:
        """Extract URL-related features."""
        urls = self._extract_urls(email_msg)
        return {
            'total_urls': len(urls),
            'suspicious_urls': len([url for url in urls if self._is_suspicious_url(url)]),
            'has_ip_urls': any(self._is_ip_url(url) for url in urls),
            'has_shortened_urls': any(self._is_shortened_url(url) for url in urls),
        }
```

## Debugging

### Backend Debugging

1. **Logging**
```python
# app/core/logging.py
import logging
from app.config import get_settings

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
```

2. **Debug Endpoints**
```python
# app/routers/debug.py
from fastapi import APIRouter
from app.database import get_db

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/db-status")
async def db_status():
    """Check database connections."""
    try:
        db = get_db()
        # Test connection
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

### Frontend Debugging

1. **React DevTools**
   - Install React Developer Tools browser extension
   - Use Redux DevTools for state debugging

2. **Console Logging**
```typescript
// src/utils/logger.ts
export const logger = {
  info: (message: string, data?: any) => {
    console.log(`[INFO] ${message}`, data);
  },
  error: (message: string, error?: any) => {
    console.error(`[ERROR] ${message}`, error);
  },
  warn: (message: string, data?: any) => {
    console.warn(`[WARN] ${message}`, data);
  },
};
```

## Performance Optimization

### Backend Optimization

1. **Database Optimization**
```python
# Use database indexes
# Add to model
class AnalysisJob(Base):
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_status_created', 'status', 'created_at'),
    )

# Use connection pooling
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30
)
```

2. **Caching**
```python
# app/core/cache.py
import redis
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(expiration: int = 3600):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            redis_client.setex(cache_key, expiration, json.dumps(result))
            
            return result
        return wrapper
    return decorator
```

### Frontend Optimization

1. **Code Splitting**
```typescript
// src/pages/Dashboard.tsx
import { lazy, Suspense } from 'react';

const AnalysisChart = lazy(() => import('@/components/AnalysisChart'));

export function Dashboard() {
  return (
    <div>
      <Suspense fallback={<div>Loading chart...</div>}>
        <AnalysisChart />
      </Suspense>
    </div>
  );
}
```

2. **Memoization**
```typescript
import { memo, useMemo } from 'react';

export const AnalysisResult = memo(({ data }: { data: AnalysisData }) => {
  const processedData = useMemo(() => {
    return processAnalysisData(data);
  }, [data]);

  return <div>{/* Render processed data */}</div>;
});
```

## Contributing Guidelines

### Code Review Process

1. **Self-Review Checklist**
   - Code follows style guidelines
   - Tests are written and passing
   - Documentation is updated
   - No sensitive data is committed
   - Error handling is appropriate

2. **Review Guidelines**
   - Focus on logic and architecture
   - Check security implications
   - Verify test coverage
   - Ensure documentation accuracy

### Release Process

1. **Version Bumping**
   - Update version numbers
   - Update changelog
   - Tag release

2. **Deployment**
   - Run full test suite
   - Deploy to staging
   - Run integration tests
   - Deploy to production

This development guide provides comprehensive instructions for contributing to the PhishCatcher project with best practices for code quality, testing, and collaboration.
