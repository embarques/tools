from __future__ import annotations

from typing import Optional

import tomllib
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from pg2mongo.mongo_uri import build_mongo_uri


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


class EnvSettings(BaseSettings):
    """Raw environment loader. We then map to Settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str
    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_SCHEMA: str = "public"

    MONGO_URI: str
    MONGO_DB: str
    MONGO_USERNAME: str = ""
    MONGO_PASSWORD: str = ""


def load_settings(config_path: Optional[str]) -> Settings:
    """
    Load settings from db.toml if provided, else from environment.
    If config_path is provided, .env / env vars are ignored.
    """
    if config_path:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        pg_data = data.get("postgres", {})
        mongo_data = data.get("mongo", {})
        transfer_data = data.get("transfer", {})

        pg = PostgresConfig(**pg_data)
        mongo = MongoConfig(**mongo_data)
        transfer = TransferConfig(**transfer_data)

        return Settings(postgres=pg, mongo=mongo, transfer=transfer)

    # Environment-based
    env = EnvSettings()

    pg = PostgresConfig(
        server=env.POSTGRES_SERVER,
        port=env.POSTGRES_PORT,
        db=env.POSTGRES_DB,
        username=env.POSTGRES_USERNAME,
        password=env.POSTGRES_PASSWORD,
        schema_name=env.POSTGRES_SCHEMA,
    )

    mongo = MongoConfig(
        uri=env.MONGO_URI,
        db=env.MONGO_DB,
        username=env.MONGO_USERNAME,
        password=env.MONGO_PASSWORD,
    )

    transfer = TransferConfig()

    return Settings(postgres=pg, mongo=mongo, transfer=transfer)
