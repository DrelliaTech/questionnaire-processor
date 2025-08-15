import os
from contextlib import contextmanager
from typing import Optional, Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool


class PostgreSQLClient:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.host = host or os.environ.get("POSTGRES_HOST")
        self.port = port or int(os.environ.get("POSTGRES_PORT", 5432))
        self.database = database or os.environ.get("POSTGRES_DB")
        self.username = username or os.environ.get("POSTGRES_USER")
        self.password = password or os.environ.get("POSTGRES_PASSWORD")
        
        if not all([self.host, self.database, self.username, self.password]):
            raise ValueError("Missing required PostgreSQL connection parameters")
        
        self.connection_string = (
            f"postgresql://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )
        
        # Use NullPool for serverless environments (Lambda/Fargate)
        self.engine = create_engine(
            self.connection_string,
            poolclass=NullPool,
            echo=False
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_tables(self, base):
        base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self, base):
        base.metadata.drop_all(bind=self.engine)