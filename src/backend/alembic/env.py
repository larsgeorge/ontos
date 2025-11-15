from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# --- Import application-specific components ---
import os
import sys
from src.common.database import Base, get_db_url # Import Base and helper
from src.common.config import get_settings, Settings, init_config # Import settings loader, model, AND initializer
# Add the project root to the Python path to allow imports from src.*
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
# ---------------------------------------------

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Alembic configuration for the application --- 
# Import the Base from your application
# from src.common.database import Base # Already imported above
# Import all model modules to ensure they are registered with Base.metadata
# import src.db_models.data_products
# import src.db_models.notification
# import src.db_models.audit_log
# import src.db_models.settings
# import src.db_models.data_asset_reviews
# Instead of individual imports, import the package to run __init__.py
import src.db_models
# Ensure all models defined in src.db_models.__all__ are now known to Base.metadata

# Set the target metadata for autogenerate
target_metadata = Base.metadata

# --- Load settings and DB URL --- 
# Use a function to handle potential errors during settings loading
def load_app_settings() -> Settings:
    try:
        # Ensure settings are initialized before getting them
        init_config() 
        return get_settings()
    except Exception as e:
        print(f"ERROR: Failed to load application settings for Alembic: {e}")
        # Optionally re-raise or exit if settings are critical
        # sys.exit(1)
        raise # Re-raise for now

settings = load_app_settings()
DB_URL = get_db_url(settings) # Use your helper to construct the URL
# --------------------------------

# --- Include Object Hook (To ignore indexes for Databricks SQL) ---
def include_object(object, name, type_, reflected, compare_to):
    """Exclude indexes from Alembic's consideration."""
    if type_ == "index":
        # print(f"Ignoring index: {name}") # Optional: for debugging
        return False
    else:
        return True
# -----------------------------------------------------------------

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # url = config.get_main_option("sqlalchemy.url") # <-- Don't get from config
    context.configure(
        url=DB_URL, # <--- Use the URL from settings
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object # Add hook here too if generating offline
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Check if a connection was provided via config.attributes
    # This allows database.py to pass an existing connection to avoid connection issues
    connectable = config.attributes.get('connection', None)
    
    if connectable is not None:
        # Use the provided connection directly
        context.configure(
            connection=connectable,
            target_metadata=target_metadata,
            include_object=include_object
        )
        
        with context.begin_transaction():
            context.run_migrations()
    else:
        # Create our own engine and connection (normal standalone mode)
        # Use a dictionary to pass the URL directly
        configuration = config.get_section(config.config_ini_section, {})
        configuration["sqlalchemy.url"] = DB_URL # <--- Set the URL here

        connectable = engine_from_config(
            configuration, # Pass the modified configuration
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            context.configure(
                connection=connection, 
                target_metadata=target_metadata,
                include_object=include_object # Pass the hook function
            )

            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
