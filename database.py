"""
database.py — SQLAlchemy models and DB session for CodeWar contest platform.
"""
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey, Enum, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import enum

# Support both SQLite (local) and PostgreSQL (Render)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./codewar.db")

# Render's PostgreSQL connection string uses postgres:// but SQLAlchemy 2.0+ requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
Base = declarative_base()


# ── Dependency ─────────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Enums ──────────────────────────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    student = "student"
    admin   = "admin"

class ContestStatus(str, enum.Enum):
    scheduled = "scheduled"
    live      = "live"
    ended     = "ended"

class Difficulty(str, enum.Enum):
    easy   = "easy"
    medium = "medium"
    hard   = "hard"

class Verdict(str, enum.Enum):
    accepted           = "Accepted"
    wrong_answer       = "Wrong Answer"
    compilation_error  = "Compilation Error"
    runtime_error      = "Runtime Error"
    time_limit_exceeded = "Time Limit Exceeded"
    pending            = "Pending"


# ── Models ─────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String(64), unique=True, nullable=False, index=True)
    email         = Column(String(128), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    role          = Column(Enum(UserRole), default=UserRole.student, nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)

    submissions = relationship("Submission", back_populates="user")


class Contest(Base):
    __tablename__ = "contests"
    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(256), nullable=False)
    description = Column(Text, default="")
    start_time  = Column(DateTime, nullable=False)
    end_time    = Column(DateTime, nullable=False)
    status      = Column(Enum(ContestStatus), default=ContestStatus.scheduled, nullable=False)
    created_by  = Column(Integer, ForeignKey("users.id"))
    created_at  = Column(DateTime, default=datetime.utcnow)

    problems    = relationship("Problem",    back_populates="contest", cascade="all, delete")
    submissions = relationship("Submission", back_populates="contest", cascade="all, delete")


class Problem(Base):
    __tablename__ = "problems"
    id               = Column(Integer, primary_key=True, index=True)
    contest_id       = Column(Integer, ForeignKey("contests.id"), nullable=False)
    title            = Column(String(256), nullable=False)
    description      = Column(Text, nullable=False)
    difficulty       = Column(Enum(Difficulty), nullable=False)
    topic            = Column(String(128), nullable=False)
    constraints      = Column(Text, default="")
    examples         = Column(Text, default="[]")   # JSON: [{input, output, explanation}]
    test_cases       = Column(Text, default="[]")   # JSON: [{input, expected_output}]  — hidden
    driver_py        = Column(Text, default="")     # hidden driver wrapper - python
    driver_c         = Column(Text, default="")     # hidden driver wrapper - c
    driver_java      = Column(Text, default="")     # hidden driver wrapper - java
    func_sig_py           = Column(Text, default="")     # solution stub - python
    func_sig_c            = Column(Text, default="")     # solution stub - c
    func_sig_java         = Column(Text, default="")     # solution stub - java
    reference_solution_py = Column(Text, default="")     # LLM reference solution (for custom input checking)
    time_limit_ms         = Column(Integer, default=2000)
    memory_limit_mb       = Column(Integer, default=256)
    base_score            = Column(Integer, default=100)
    order_index           = Column(Integer, default=0)
    created_at            = Column(DateTime, default=datetime.utcnow)

    contest     = relationship("Contest",    back_populates="problems")
    submissions = relationship("Submission", back_populates="problem", cascade="all, delete")


class Submission(Base):
    __tablename__ = "submissions"
    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"),    nullable=False)
    problem_id     = Column(Integer, ForeignKey("problems.id"), nullable=False)
    contest_id     = Column(Integer, ForeignKey("contests.id"), nullable=False)
    language       = Column(String(16), nullable=False)
    code           = Column(Text, nullable=False)
    verdict        = Column(Enum(Verdict), default=Verdict.pending, nullable=False)
    passed_cases   = Column(Integer, default=0)
    total_cases    = Column(Integer, default=0)
    score          = Column(Float, default=0.0)
    execution_ms   = Column(Float, default=0.0)
    stderr         = Column(Text, default="")
    submitted_at   = Column(DateTime, default=datetime.utcnow)

    user    = relationship("User",    back_populates="submissions")
    problem = relationship("Problem", back_populates="submissions")
    contest = relationship("Contest", back_populates="submissions")


# ── Init & Auto-Migration ──────────────────────────────────────────────────────
def _run_migrations():
    """
    SQLite does not support ALTER TABLE … ADD COLUMN via SQLAlchemy's create_all.
    This function inspects every mapped table and adds any missing columns so the
    live DB stays in sync with the models without data loss.
    """
    import logging
    from sqlalchemy import inspect, text

    log = logging.getLogger(__name__)
    inspector = inspect(engine)

    with engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            # Tables that don't exist yet are handled by create_all above
            if not inspector.has_table(table.name):
                continue

            existing_cols = {col["name"] for col in inspector.get_columns(table.name)}

            for col in table.columns:
                if col.name in existing_cols:
                    continue  # already present — nothing to do

                # Build a safe default for the ALTER TABLE statement
                col_type = col.type.compile(dialect=engine.dialect)
                if col.default is not None and col.default.is_scalar:
                    default_val = col.default.arg
                    if isinstance(default_val, str):
                        default_clause = f"DEFAULT '{default_val}'"
                    else:
                        default_clause = f"DEFAULT {default_val}"
                elif col.nullable is not False:
                    default_clause = "DEFAULT NULL"
                else:
                    default_clause = "DEFAULT ''"

                sql = f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type} {default_clause}"
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    log.info("[db] Migration: added column '%s.%s'", table.name, col.name)
                except Exception as exc:
                    log.warning("[db] Could not add column '%s.%s': %s", table.name, col.name, exc)


def init_db():
    Base.metadata.create_all(bind=engine)
    _run_migrations()

