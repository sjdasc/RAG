# db/models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from .db import Base

# PostgresDB 
class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String(1024), unique=True, index=True, nullable=False)
    title = Column(String(512), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    session_id = Column(String, index=True, default="default")

# 이건 chorma?
class SearchLog(Base):
    __tablename__ = "search_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True, default="default")
    query = Column(Text, nullable=False)
    top_k = Column(Integer, nullable=False)
    results_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
