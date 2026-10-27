from logging.config import fileConfig
import os
import sys

from alembic import context

# Ensure app path is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None

def run_migrations_offline() -> None:
    url = os.getenv("DATABASE_URL", "sqlite:///./sentinelflow.db")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    pass

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
