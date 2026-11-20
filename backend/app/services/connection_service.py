import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.security import decrypt_secret, encrypt_secret
from app.models.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class ConnectionService:
    @staticmethod
    def get_connection_url(conn: DatabaseConnection, readonly: bool = True) -> str:
        """Constructs a secure SQLAlchemy database URL from connection details."""
        raw_password = decrypt_secret(conn.encrypted_credentials)
        safe_user = quote_plus(conn.username)
        safe_password = quote_plus(raw_password)
        if conn.database_type.lower() == "postgresql":
            # Using psycopg3 driver
            return f"postgresql+psycopg://{safe_user}:{safe_password}@{conn.host}:{conn.port}/{conn.database_name}"
        elif conn.database_type.lower() == "mysql":
            return f"mysql+pymysql://{safe_user}:{safe_password}@{conn.host}:{conn.port}/{conn.database_name}"
        elif conn.database_type.lower() == "sqlite":
            return f"sqlite:///{conn.database_name}"
        else:
            raise ValueError(f"Unsupported database type: {conn.database_type}")

    @classmethod
    def test_connection_params(
        cls,
        database_type: str,
        host: str,
        port: int,
        database_name: str,
        username: str,
        password: str,
        ssl_mode: Optional[str] = None,
        timeout_seconds: int = 5,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Tests external database connectivity with real handshake."""
        db_type = database_type.lower()
        if db_type not in ("postgresql", "mysql"):
            return False, f"Database type '{database_type}' not yet configured.", {}

        safe_user = quote_plus(username)
        safe_password = quote_plus(password)
        if db_type == "postgresql":
            url = f"postgresql+psycopg://{safe_user}:{safe_password}@{host}:{port}/{database_name}"
            test_query = text("SELECT version(), current_database(), current_user;")
        else:
            url = f"mysql+pymysql://{safe_user}:{safe_password}@{host}:{port}/{database_name}"
            test_query = text("SELECT VERSION(), DATABASE(), CURRENT_USER();")

        connect_args = {"connect_timeout": timeout_seconds}
        engine = None
        try:
            engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
            with engine.connect() as connection:
                result = connection.execute(test_query)
                row = result.fetchone()
                server_info = {
                    "version": row[0] if row else "Unknown",
                    "database": row[1] if row else database_name,
                    "user": row[2] if row else username,
                }
                return True, "Connection successful!", server_info
        except Exception as e:
            logger.warning(f"Connection test failed for {host}:{port}/{database_name}: {str(e)}")
            return False, f"Connection failed: {str(e)}", {}
        finally:
            if engine:
                engine.dispose()

    @classmethod
    def create_connection(
        cls,
        db: Session,
        workspace_id: Any,
        name: str,
        database_type: str,
        host: str,
        port: int,
        database_name: str,
        username: str,
        password: str,
        ssl_configuration: Optional[Dict[str, Any]] = None,
    ) -> DatabaseConnection:
        """Persists a new database connection with encrypted credentials."""
        encrypted_pass = encrypt_secret(password)
        conn = DatabaseConnection(
            workspace_id=workspace_id,
            name=name,
            database_type=database_type.lower(),
            host=host,
            port=port,
            database_name=database_name,
            username=username,
            encrypted_credentials=encrypted_pass,
            ssl_configuration=ssl_configuration or {},
            status="connected",
        )
        db.add(conn)
        db.commit()
        db.refresh(conn)
        return conn

    @classmethod
    def test_existing_connection(cls, conn: DatabaseConnection) -> Tuple[bool, str, Dict[str, Any]]:
        """Tests an existing persisted connection."""
        raw_password = decrypt_secret(conn.encrypted_credentials)
        return cls.test_connection_params(
            database_type=conn.database_type,
            host=conn.host,
            port=conn.port,
            database_name=conn.database_name,
            username=conn.username,
            password=raw_password,
        )

