"""
Main FastAPI app for the TradeSphere backend API service.

Implements REST endpoints for:
- User authentication and management (email, Google OAuth, password reset, etc.)
- Visual strategy builder (CRUD)
- Backtest results and query
- Paper trading and trade logs
- Portfolio tracker (CRUD, filters)
- AI assistant (scaffold)
- Health checks (including live DB check)

SQLite is used as the backend DB engine.
All code is PEP8-compliant and linter-friendly.
"""

import os
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    ForeignKey, DateTime, Boolean, Text
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship


# === DB connection parameters ===

SQLITE_DB_FILENAME = os.getenv("DB_PATH", "tradesphere.sqlite3")
DATABASE_URL = f"sqlite:///./{SQLITE_DB_FILENAME}"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# === FastAPI app ===

app = FastAPI(
    title="TradeSphere Backend API",
    description=(
        "Backend REST API for trading strategies, paper trading, "
        "portfolio, and AI integration."
    ),
    version="0.1.0",
    openapi_tags=[
        {"name": "health", "description": "Health and liveness checks"},
        {"name": "users", "description": "Signup, login, password reset, Google OAuth"},
        {"name": "dashboard", "description": "Dashboard overview/stats"},
        {"name": "strategies", "description": "Visual/drag-and-drop strategy builder"},
        {"name": "backtest", "description": "Backtest results endpoints"},
        {"name": "paper_trading", "description": "Paper trading, mock orders, trade logs"},
        {"name": "portfolio", "description": "Portfolio tracker with performance filters"},
        {"name": "ai_assistant", "description": "AI assistant endpoints (stub)"},
    ]
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Integrate with frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === SQLAlchemy DB MODELS ===


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    full_name = Column(String, nullable=True)
    google_id = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    strategies = relationship('Strategy', back_populates='owner')
    portfolios = relationship('Portfolio', back_populates='user')
    ai_sessions = relationship('AIAssistantSession', back_populates='user')
    backtests = relationship('BacktestResult', back_populates='user')


class Strategy(Base):
    __tablename__ = "strategies"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    config_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship('User', back_populates='strategies')
    backtests = relationship('BacktestResult', back_populates='strategy')


class BacktestResult(Base):
    __tablename__ = "backtest_results"
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    parameters = Column(Text)
    results_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    strategy = relationship('Strategy', back_populates='backtests')
    user = relationship('User', back_populates='backtests')


class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    stats_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='portfolios')
    trades = relationship('PaperTrade', back_populates='portfolio')


class PaperTrade(Base):
    __tablename__ = "paper_trades"
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    asset = Column(String, nullable=False)
    trade_type = Column(String, nullable=False)  # buy/sell
    amount = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship('Portfolio', back_populates='trades')


class AIAssistantSession(Base):
    __tablename__ = "ai_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    request = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='ai_sessions')


# === PYDANTIC SCHEMAS ===


# PUBLIC_INTERFACE
class UserCreate(BaseModel):
    """User registration schema."""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=4, description="User raw password")
    full_name: Optional[str] = Field(None, description="User full name")


# PUBLIC_INTERFACE
class UserLogin(BaseModel):
    """User login schema."""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User raw password")


# PUBLIC_INTERFACE
class UserOut(BaseModel):
    """Output schema for returning user details."""
    id: int
    email: EmailStr
    full_name: Optional[str]
    is_active: bool

    class Config:
        orm_mode = True


# PUBLIC_INTERFACE
class StrategyCreate(BaseModel):
    name: str
    description: Optional[str]
    config_json: Optional[str]


# PUBLIC_INTERFACE
class StrategyOut(BaseModel):
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
    strategy_id: int
    parameters: Optional[str]


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


# === DB DEPENDENCY ===

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# === HEALTH CHECK ENDPOINTS ===

# PUBLIC_INTERFACE
@app.get("/health", tags=["health"])
def app_health():
    """Application health check endpoint."""
    return {"status": "ok"}


# PUBLIC_INTERFACE
@app.get("/health/db", tags=["health"])
def health_db(db: Session = Depends(get_db)):
    """
    DB health check. Executes SELECT 1 and returns db_status.
    """
    try:
        db.execute("SELECT 1")
        return {"db_status": "ok"}
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"DB ERROR: {err}")


# === USER ENDPOINTS (Signup/Login/OAuth/Reset) ===

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# PUBLIC_INTERFACE
@app.post("/users/register", response_model=UserOut, tags=["users"])
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register new user with email and password (plain password; do NOT use in production)."""
    exists = db.query(User).filter(User.email == user.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_obj = User(
        email=user.email,
        hashed_password=user.password + "_hashed",  # Replace with hash in real code!
        full_name=user.full_name,
    )
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj


# PUBLIC_INTERFACE
@app.post("/users/login", tags=["users"])
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    """Login with email and password, returning dummy token."""
    found = db.query(User).filter(User.email == user.email).first()
    correct = found and found.hashed_password == user.password + "_hashed"
    if not correct:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "access_token": f"dummy-token-for-{found.id}",
        "token_type": "bearer"
    }


# PUBLIC_INTERFACE
@app.post("/users/request_reset", tags=["users"])
def request_password_reset(email: EmailStr, db: Session = Depends(get_db)):
    """Begin a password reset flow (scaffold only; does not actually send mail)."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")
    return {"message": f"Reset link sent to {email} (scaffold)"}


# PUBLIC_INTERFACE
@app.post("/users/google_oauth", tags=["users"])
def google_oauth_stub():
    """
    Google OAuth not implemented.
    In production, frontend should handle OAuth and send token for backend validation.
    """
    return {
        "message": "Google OAuth integration not implemented—OAuth flow will occur on frontend."
    }


# === DASHBOARD (Landing/Overview) ===

# PUBLIC_INTERFACE
@app.get("/dashboard/summary", tags=["dashboard"])
def dashboard_summary(db: Session = Depends(get_db)):
    """
    Dashboard performance summary.
    Returns static/example data for demo purposes.
    """
    return {
        "summary": {
            "performance": 0.10,
            "open_positions": 2,
            "trades_today": 4,
        }
    }


# === STRATEGY BUILDER ENDPOINTS ===

# PUBLIC_INTERFACE
@app.post("/strategies/", response_model=StrategyOut, tags=["strategies"])
def create_strategy(
    strategy: StrategyCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Create a new visual strategy (owner_id=1 stub)."""
    obj = Strategy(
        owner_id=1,  # TODO: extract from JWT in real implementation
        name=strategy.name,
        description=strategy.description,
        config_json=strategy.config_json,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# PUBLIC_INTERFACE
@app.get("/strategies/", response_model=List[StrategyOut], tags=["strategies"])
def list_strategies(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """List all strategies for user (stub owner_id=1)."""
    qset = db.query(Strategy).filter(Strategy.owner_id == 1).all()
    return qset


# PUBLIC_INTERFACE
@app.put("/strategies/{strategy_id}", response_model=StrategyOut, tags=["strategies"])
def update_strategy(
    strategy_id: int,
    strategy: StrategyCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    Update a strategy (stub owner_id=1; does not verify ownership!).
    """
    obj = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Strategy not found")
    obj.name = strategy.name
    obj.description = strategy.description
    obj.config_json = strategy.config_json
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


# === BACKTEST ENDPOINTS ===

# PUBLIC_INTERFACE
@app.post("/backtest/", response_model=BacktestResultOut, tags=["backtest"])
def create_backtest(
    backtest: BacktestResultCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Submit new backtest job for a strategy (owner_id=1 stub)."""
    bt = BacktestResult(
        strategy_id=backtest.strategy_id,
        user_id=1,  # TODO: derive from JWT
        parameters=backtest.parameters,
        results_json='{"status":"complete","pnl":0.05}',  # stub results
    )
    db.add(bt)
    db.commit()
    db.refresh(bt)
    return bt


# PUBLIC_INTERFACE
@app.get("/backtest/{backtest_id}", response_model=BacktestResultOut, tags=["backtest"])
def get_backtest(
    backtest_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Get backtest result by ID."""
    bt = db.query(BacktestResult).filter(BacktestResult.id == backtest_id).first()
    if not bt:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return bt


# === PAPER TRADING ENDPOINTS ===

# PUBLIC_INTERFACE
@app.post("/paper_trading/trade", response_model=PaperTradeOut, tags=["paper_trading"])
def paper_trade(
    trade: PaperTradeCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Record a virtual trade in a portfolio."""
    tr = PaperTrade(
        portfolio_id=trade.portfolio_id,
        asset=trade.asset,
        trade_type=trade.trade_type,
        amount=trade.amount,
        price=trade.price,
    )
    db.add(tr)
    db.commit()
    db.refresh(tr)
    return tr


# PUBLIC_INTERFACE
@app.get(
    "/paper_trading/portfolio/{portfolio_id}/trades",
    response_model=List[PaperTradeOut],
    tags=["paper_trading"]
)
def portfolio_trades(
    portfolio_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Get all trades for a specific portfolio."""
    trs = db.query(PaperTrade).filter(PaperTrade.portfolio_id == portfolio_id).all()
    return trs


# === PORTFOLIO TRACKER ENDPOINTS ===

# PUBLIC_INTERFACE
@app.post("/portfolio/", response_model=PortfolioOut, tags=["portfolio"])
def create_portfolio(
    portfolio: PortfolioCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Create a new portfolio (owner_id=1 stub)."""
    p = Portfolio(
        user_id=1,  # TODO: derive from token
        name=portfolio.name,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# PUBLIC_INTERFACE
@app.get("/portfolio/", response_model=List[PortfolioOut], tags=["portfolio"])
def list_portfolios(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """List portfolios for the current user (owner_id=1 stub)."""
    pset = db.query(Portfolio).filter(Portfolio.user_id == 1).all()
    return pset


# PUBLIC_INTERFACE
@app.get("/portfolio/{portfolio_id}", response_model=PortfolioOut, tags=["portfolio"])
def get_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Get a portfolio by ID (stub: no real user validation)."""
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return p


# === AI ASSISTANT ENDPOINTS (Scaffold) ===

# PUBLIC_INTERFACE
@app.post("/ai/ask", response_model=AIAssistantResponse, tags=["ai_assistant"])
def ask_ai(
    request: AIAssistantRequest,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    AI assistant placeholder, records request/response in DB (stub response).
    """
    session = AIAssistantSession(
        user_id=1,  # TODO: extract from token
        request=request.query,
        response="Hello! This is a demo AI assistant response.",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return AIAssistantResponse(session_id=session.id, response=session.response)


# === DB INIT ===

def initialize_db():
    Base.metadata.create_all(bind=engine)


initialize_db()
