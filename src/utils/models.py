from sqlalchemy import Column, String, Float, Integer, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class ExecutionSession(Base):
    __tablename__ = 'execution_sessions'
    
    session_id = Column(String, primary_key=True)
    timestamp = Column(Float, nullable=False)
    
    execution_times = relationship("ExecutionTime", back_populates="session", cascade="all, delete-orphan")
    execution_orders = relationship("ExecutionOrder", back_populates="session", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="session", cascade="all, delete-orphan")
    git_tracking = relationship("GitTracking", back_populates="session", uselist=False, cascade="all, delete-orphan")

class ExecutionTime(Base):
    __tablename__ = 'execution_times'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey('execution_sessions.session_id', ondelete='CASCADE'))
    function_name = Column(String)
    execution_time = Column(Float)
    
    session = relationship("ExecutionSession", back_populates="execution_times")

class ExecutionOrder(Base):
    __tablename__ = 'execution_order'
    
    session_id = Column(String, ForeignKey('execution_sessions.session_id', ondelete='CASCADE'), primary_key=True)
    order_index = Column(Integer, primary_key=True)
    function_name = Column(String)
    execution_time = Column(Float)
    
    session = relationship("ExecutionSession", back_populates="execution_orders")

class TimelineEvent(Base):
    __tablename__ = 'timeline_events'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey('execution_sessions.session_id', ondelete='CASCADE'))
    function_name = Column(String)
    start_time = Column(Float)
    end_time = Column(Float)
    
    session = relationship("ExecutionSession", back_populates="timeline_events")

class GitTracking(Base):
    __tablename__ = 'git_tracking'
    
    session_id = Column(String, ForeignKey('execution_sessions.session_id', ondelete='CASCADE'), primary_key=True)
    git_commit = Column(String)
    timestamp = Column(Float)
    
    session = relationship("ExecutionSession", back_populates="git_tracking")

# Database configuration
def get_sync_engine(db_path):
    return create_engine(f"sqlite:///{db_path}")

def get_async_engine(db_path):
    return create_async_engine(f"sqlite+aiosqlite:///{db_path}")

def init_db(db_path):
    engine = get_sync_engine(db_path)
    Base.metadata.create_all(engine)