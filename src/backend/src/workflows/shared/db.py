import os
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def build_db_url_from_env() -> str:
    host = os.environ.get("POSTGRES_HOST")
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    db = os.environ.get("POSTGRES_DB")
    port = os.environ.get("POSTGRES_PORT", "5432")
    if not all([host, user, password, db]):
        raise RuntimeError("Missing Postgres env vars: POSTGRES_HOST/USER/PASSWORD/DB")

    schema = os.environ.get("POSTGRES_DB_SCHEMA")
    query = f"?options=-csearch_path%3D{schema}" if schema else ""
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}{query}"


def create_engine_from_env() -> Engine:
    url = build_db_url_from_env()
    return create_engine(url, pool_pre_ping=True)


