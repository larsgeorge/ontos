import os
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from .secrets import get_secret_value


def build_db_url_from_env() -> str:
    host = os.environ.get("POSTGRES_HOST")
    user = os.environ.get("POSTGRES_USER")
    db = os.environ.get("POSTGRES_DB")
    port = os.environ.get("POSTGRES_PORT", "5432")

    # Resolve password either directly or via Databricks secret reference
    password = os.environ.get("POSTGRES_PASSWORD")
    if not password:
        secret_ref = os.environ.get("POSTGRES_PASSWORD_SECRET")
        if secret_ref:
            password = get_secret_value(secret_ref)

    if not all([host, user, password, db]):
        raise RuntimeError(
            "Missing Postgres env vars: POSTGRES_HOST/USER/(PASSWORD or POSTGRES_PASSWORD_SECRET)/DB"
        )

    schema = os.environ.get("POSTGRES_DB_SCHEMA")
    query = f"?options=-csearch_path%3D{schema}" if schema else ""
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}{query}"


def create_engine_from_env() -> Engine:
    url = build_db_url_from_env()
    return create_engine(url, pool_pre_ping=True)


