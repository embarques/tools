from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Dict, Any

from pg2mongo.mongo_uri import build_mongo_uri
from urllib.parse import quote_plus


class AppSettings(BaseSettings):
    # ==== PostgreSQL ====
    pg_server: str = Field(alias="POSTGRES_SERVER")
    pg_port: int = Field(default=5432, alias="POSTGRES_PORT")
    pg_db: str = Field(alias="POSTGRES_DB")
    pg_username: str = Field(default="", alias="POSTGRES_USERNAME")
    pg_password: str = Field(default="", alias="POSTGRES_PASSWORD")
    pg_schema: str = Field(default="public", alias="PG_SCHEMA")
    pg_table: str = Field(default="invoices", alias="PG_TABLE")

    # ==== MongoDB (base URI + injected creds) ====
    mongo_uri_base: str = Field(alias="MONGO_URI")   # base (no creds)
    mongo_db: str = Field(alias="MONGO_DB")          # ← Mongo DB
    mongo_collection: str = Field(alias="MONGO_COLLECTION")
    mongo_username: str = Field(default="", alias="MONGO_USERNAME")
    mongo_password: str = Field(default="", alias="MONGO_PASSWORD")

    # ==== Transfer ====
    upsert_key: str = Field(default="oldID", alias="UPsert_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def pg_dsn(self) -> str:
        auth = ""
        if self.pg_username:
            auth = quote_plus(self.pg_username)
            if self.pg_password:
                auth = f"{auth}:{quote_plus(self.pg_password)}"
            auth += "@"
        return f"postgresql://{auth}{self.pg_server}:{self.pg_port}/{self.pg_db}"

    @property
    def mongo_uri(self) -> str:
        """Final MongoDB URI; inject creds only when absent from the base URI."""
        return build_mongo_uri(
            self.mongo_uri_base,
            self.mongo_username,
            self.mongo_password,
        )


def load_settings() -> AppSettings:
    return AppSettings()


def load_settings_from_dict(d: Dict[str, Any]) -> AppSettings:
    # model_validate() expects field names (not env aliases),
    # which is why dbconfig_to_settings_dict uses AppSettings attribute names.
    return AppSettings.model_validate(d)
