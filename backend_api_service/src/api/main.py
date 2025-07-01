"""Main FastAPI app for the TradeSphere backend API service.

Exposes core REST endpoints (users, strategies, backtest, trading, portfolio,
AI assistant scaffold, health checks) and manages connection to SQLite DB.
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    ForeignKey, DateTime, Boolean, Text
)
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
import os


# SQLite database setup
SQLITE_DB_PATH = os.getenv("DB_PATH", "tradesphere.sqlite3")
DATABASE_URL = f"sqlite:///./{SQLITE_DB_PATH}"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# FastAPI app
app = FastAPI(
    title="TradeSphere Backend API",
    description=(
        "REST backend for trading strategy platform: user auth, strategy builder, "
        "backtest, portfolios, trading, AI assistant."
    ),
    version="0.1.0",
    openapi_tags=[
        {'name': 'health', 'description': 'Health check endpoints'},
        {'name': 'users', 'description': 'User management and authentication'},
        {'name': 'strategies', 'description': 'Strategy editor and listing'},
        {'name': 'backtest', 'description': 'Backtest execution and result data'},
        {'name': 'paper_trading', 'description': 'Paper trading, trade logs, virtual portfolio'},
        {'name': 'portfolio', 'description': 'Portfolio tracker and stats'},
        {'name': 'ai_assistant', 'description': 'AI assistant endpoints (scaffold)'},
    ]
)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== DATABASE MODELS ==========


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    full_name = Column(String, nullable=True)
    google_id = Column(String, nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Strategy(Base):
    __tablename__ = "strategies"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    config_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class BacktestResult(Base):
    __tablename__ = "backtest_results"
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    parameters = Column(Text, nullable=True)
    results_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    stats_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class PaperTrade(Base):
    __tablename__ = "paper_trades"
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    asset = Column(String, nullable=False)
    trade_type = Column(String, nullable=False)  # buy/sell
    amount = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow)


class AIAssistantSession(Base):
    __tablename__ = "ai_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    request = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ========== Pydantic SCHEMAS ==========


# PUBLIC_INTERFACE
class UserCreate(BaseModel):
    """Pydantic schema for creating a new user."""
    email: EmailStr
    password: str
    full_name: Optional[str] = None


# PUBLIC_INTERFACE
class UserLogin(BaseModel):
    """Pydantic schema for user login."""
    email: EmailStr
    password: str


# PUBLIC_INTERFACE
class UserOut(BaseModel):
    """Pydantic schema for returning user data."""
    id: int
    email: EmailStr
    full_name: Optional[str]
    is_active: bool

    class Config:
        orm_mode = True


# PUBLIC_INTERFACE
class StrategyCreate(BaseModel):
    """Schema for creating a strategy."""
    name: str
    description: Optional[str] = None
    config_json: Optional[str] = None


# PUBLIC_INTERFACE
class StrategyOut(BaseModel):
    """Schema for reading a strategy record."""
    id: int
    owner_id: int
    name: str
    description: Optional[str]
    config_json: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# PUBLIC_INTERFACE
class BacktestResultCreate(BaseModel):
    """Schema for submitting a backtest job."""
    strategy_id: int
    parameters: Optional[str] = None


# PUBLIC_INTERFACE
class BacktestResultOut(BaseModel):
    id: int
    strategy_id: int
    user_id: Optional[int]
    parameters: Optional[str]
    results_json: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True


# PUBLIC_INTERFACE
class PortfolioCreate(BaseModel):
    """Schema for creating a portfolio."""
    name: str


# PUBLIC_INTERFACE
class PortfolioOut(BaseModel):
    id: int
    user_id: int
    name: str
    stats_json: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# PUBLIC_INTERFACE
class PaperTradeCreate(BaseModel):
    portfolio_id: int
    asset: str
    trade_type: str
    amount: float
    price: float


# PUBLIC_INTERFACE
class PaperTradeOut(BaseModel):
    id: int
    portfolio_id: int
    asset: str
    trade_type: str
    amount: float
    price: float
    executed_at: datetime

    class Config:
        orm_mode = True


# PUBLIC_INTERFACE
class AIAssistantRequest(BaseModel):
    query: str


# PUBLIC_INTERFACE
class AIAssistantResponse(BaseModel):
    session_id: int
    response: Optional[str]


# ========== Utility Dependency ==========


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ========== HEALTH ENDPOINTS ==========


# PUBLIC_INTERFACE
@app.get("/health", tags=["health"])
def service_health():
    """Application health check endpoint."""
    return {"status": "ok"}


# PUBLIC_INTERFACE
@app.get("/health/db", tags=["health"])
def db_health(db: Session = Depends(get_db)):
    """Database health check; attempts a trivial SQL query."""
    try:
        db.execute("SELECT 1")
        return {"db_status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DB ERROR: {exc}")


# ========== USER ENDPOINTS (AUTH & MANAGEMENT) ==========

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# PUBLIC_INTERFACE
@app.post("/users/register", response_model=UserOut, tags=["users"])
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register new user with email+password."""
    # Placeholder: do not store plain password; hash it.
    user_obj = User(
        email=user.email,
        hashed_password=user.password + "_hashed",  # TODO: Use a real hasher
        full_name=user.full_name
    )
    db.add(user_obj)
    try:
        db.commit()
        db.refresh(user_obj)
        return user_obj
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Email already registered or DB error: {e}"
        )


# PUBLIC_INTERFACE
@app.post("/users/login", tags=["users"])
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    """User login (email + password). Returns dummy token if successful."""
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or db_user.hashed_password != user.password + "_hashed":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Placeholder: return static/fake token
    return {
        "access_token": f"dummy-token-for-{db_user.id}",
        "token_type": "bearer"
    }


# PUBLIC_INTERFACE
@app.post("/users/request_reset", tags=["users"])
def request_password_reset(email: EmailStr, db: Session = Depends(get_db)):
    """Begin password reset (scaffolding only)."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")
    # This would email/reset-token in real workflow:
    return {"message": f"Reset link sent to {email}"}


# PUBLIC_INTERFACE
@app.post("/users/google_oauth", tags=["users"])
def google_oauth_placeholder():
    """
    Placeholder: Google OAuth endpoint (to be implemented with real OAuth flow).
    """
    return {
        "message": (
            "Google OAuth not implemented—frontend should perform OAuth; "
            "server would validate token."
        )
    }


# ========== DASHBOARD PORTFOLIO & TRADER ==========


# PUBLIC_INTERFACE
@app.get("/dashboard/summary", tags=["portfolio"])
def dashboard_summary(db: Session = Depends(get_db)):
    """Get dummy dashboard summary (would aggregate real data in prod)."""
    # Placeholder: return static data; in real code, aggregate actual performance summary.
    return {
        "summary": {
            "performance": 0.12,
            "open_positions": 3,
            "trades_today": 2
        }
    }


# ========== STRATEGY BUILDER ENDPOINTS ==========


# PUBLIC_INTERFACE
@app.post("/strategies/", response_model=StrategyOut, tags=["strategies"])
def create_strategy(
    strategy: StrategyCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Create new strategy (dummy owner=1)."""
    strategy_obj = Strategy(
        owner_id=1,  # TODO: decode from JWT token
        name=strategy.name,
        description=strategy.description,
        config_json=strategy.config_json
    )
    db.add(strategy_obj)
    db.commit()
    db.refresh(strategy_obj)
    return strategy_obj


# PUBLIC_INTERFACE
@app.get("/strategies/", response_model=List[StrategyOut], tags=["strategies"])
def list_strategies(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """List strategies for dummy user (id=1)."""
    strategies = db.query(Strategy).filter(Strategy.owner_id == 1).all()
    return strategies


# ========== BACKTEST RESULTS ==========


# PUBLIC_INTERFACE
@app.post("/backtest/", response_model=BacktestResultOut, tags=["backtest"])
def create_backtest(
    backtest: BacktestResultCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Submit new backtest job (results stub)."""
    backtest_obj = BacktestResult(
        strategy_id=backtest.strategy_id,
        user_id=1,  # TODO: decode from JWT
        parameters=backtest.parameters,
        results_json='{"status": "complete", "pnl": 0.034}'  # stub
    )
    db.add(backtest_obj)
    db.commit()
    db.refresh(backtest_obj)
    return backtest_obj


# PUBLIC_INTERFACE
@app.get("/backtest/{backtest_id}", response_model=BacktestResultOut, tags=["backtest"])
def get_backtest(
    backtest_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Fetch backtest result by ID."""
    backtest = db.query(BacktestResult).filter(BacktestResult.id == backtest_id).first()
    if not backtest:
        raise HTTPException(status_code=404, detail="Not found")
    return backtest


# ========== PAPER TRADING ==========


# PUBLIC_INTERFACE
@app.post("/paper_trading/trade", response_model=PaperTradeOut, tags=["paper_trading"])
def record_paper_trade(
    trade: PaperTradeCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Record trade in virtual portfolio (paper trading)."""
    trade_obj = PaperTrade(
        portfolio_id=trade.portfolio_id,
        asset=trade.asset,
        trade_type=trade.trade_type,
        amount=trade.amount,
        price=trade.price,
    )
    db.add(trade_obj)
    db.commit()
    db.refresh(trade_obj)
    return trade_obj


# PUBLIC_INTERFACE
@app.get(
    "/paper_trading/portfolio/{portfolio_id}/trades",
    response_model=List[PaperTradeOut],
    tags=["paper_trading"]
)
def list_portfolio_trades(
    portfolio_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """List all trades in a portfolio."""
    trades = db.query(PaperTrade).filter(PaperTrade.portfolio_id == portfolio_id).all()
    return trades


# ========== PORTFOLIO TRACKER ==========


# PUBLIC_INTERFACE
@app.post("/portfolio/", response_model=PortfolioOut, tags=["portfolio"])
def create_portfolio(
    portfolio: PortfolioCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Create new portfolio for user."""
    portfolio_obj = Portfolio(
        user_id=1,  # TODO: derive from token (stub)
        name=portfolio.name
    )
    db.add(portfolio_obj)
    db.commit()
    db.refresh(portfolio_obj)
    return portfolio_obj


# PUBLIC_INTERFACE
@app.get("/portfolio/", response_model=List[PortfolioOut], tags=["portfolio"])
def list_portfolios(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """List all user portfolios (dummy: user=1)."""
    portfolios = db.query(Portfolio).filter(Portfolio.user_id == 1).all()
    return portfolios


# ========== AI ASSISTANT SCAFFOLD ==========


# PUBLIC_INTERFACE
@app.post("/ai/ask", response_model=AIAssistantResponse, tags=["ai_assistant"])
def ask_ai(
    request: AIAssistantRequest,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """AI assistant scaffolding endpoint (stub, does not use real LLM)."""
    session = AIAssistantSession(
        user_id=1,
        request=request.query,
        response="AI says: this is a placeholder response."
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return AIAssistantResponse(session_id=session.id, response=session.response)


# ========== INITIALIZE DB SCHEMA IF NEEDED ==========


def initialize_db():
    """Create database tables if they do not already exist."""
    Base.metadata.create_all(bind=engine)


initialize_db()
