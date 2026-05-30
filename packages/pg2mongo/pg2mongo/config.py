from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
import tomllib
from pydantic import BaseModel

from pg2mongo.mongo_uri import build_mongo_uri

# pg2mongo project root (contains db.toml when installed editable)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_NAME = "db.toml"


def _find_db_toml() -> Path | None:
    for candidate in (Path.cwd() / DEFAULT_CONFIG_NAME, _PROJECT_ROOT / DEFAULT_CONFIG_NAME):
        if candidate.is_file():
            return candidate
    return None


def resolve_config_path(config_path: Optional[str]) -> Path:
    """Return the TOML config file path (explicit ``-c`` or auto-discovered ``db.toml``)."""
    if config_path:
        path = Path(config_path)
        if not path.is_file():
            raise click.ClickException(f"Config file not found: {path}")
        return path

    found = _find_db_toml()
    if found is not None:
        return found

    raise click.ClickException(
        "No configuration found.\n"
        f"  • Copy db.example.toml to {DEFAULT_CONFIG_NAME} and edit it, or\n"
        f"  • Pass an explicit path: pg2mongo -c /path/to/{DEFAULT_CONFIG_NAME}\n"
        f"  Searched: {Path.cwd()}, {_PROJECT_ROOT}"
    )


class PostgresConfig(BaseModel):
    server: str
    port: int = 5432
    db: str
    username: str
    password: str
    schema_name: str = "public"


class MongoConfig(BaseModel):
    uri: str
    db: str
    username: str = ""
    password: str = ""

    def build_uri(self) -> str:
        """Return connection URI, injecting creds only when absent from *uri*."""
        return build_mongo_uri(self.uri, self.username, self.password)


class TransferConfig(BaseModel):
    upsert_key: str = "oldID"


class Settings(BaseModel):
    postgres: PostgresConfig
    mongo: MongoConfig
    transfer: TransferConfig = TransferConfig()


def load_settings(config_path: Optional[str]) -> Settings:
    """
    Load settings from ``db.toml``.

    Uses ``config_path`` when provided (``-c`` flag), otherwise auto-discovers
    ``db.toml`` in the current directory or the pg2mongo project root.
    """
    path = resolve_config_path(config_path)

    with open(path, "rb") as f:
        data = tomllib.load(f)

    pg_data = data.get("postgres", {})
    mongo_data = data.get("mongo", {})
    transfer_data = data.get("transfer", {})

    pg = PostgresConfig(**pg_data)
    mongo = MongoConfig(**mongo_data)
    transfer = TransferConfig(**transfer_data)

    return Settings(postgres=pg, mongo=mongo, transfer=transfer)
