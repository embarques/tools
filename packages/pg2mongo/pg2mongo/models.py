from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class IdRefInt(BaseModel):
    model_config = ConfigDict(extra="ignore")
    _id: int


class BranchRef(IdRefInt): ...
class UserRef(IdRefInt): ...
class DriverRef(IdRefInt): ...


class ContainerRef(BaseModel):
    model_config = ConfigDict(extra="ignore")
    _id: int


class Address(BaseModel):
    model_config = ConfigDict(extra="ignore")
    address1: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None


class Party(BaseModel):
    model_config = ConfigDict(extra="ignore")
    _id: Optional[str] = None
    oldID: Optional[int] = None
    name: Optional[str] = None
    customerType: Optional[int] = None
    phone1: Optional[str] = None
    createdAt: Optional[datetime] = None
    branch: Optional[BranchRef] = None
    createdByID: Optional[int] = None
    address: Optional[Address] = None


class InvoiceDetailRef(BaseModel):
    model_config = ConfigDict(extra="ignore")
    _id: Optional[str] = None


class InvoiceDocument(BaseModel):
    model_config = ConfigDict(extra="ignore")

    oldID: int = Field(..., description="Legacy Postgres PK")
    number: str
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    date: Optional[datetime] = None

    paidRegion: Optional[str] = None
    paidStatus: Optional[str] = None

    branch: Optional[BranchRef] = None
    user: Optional[UserRef] = None
    driver: Optional[DriverRef] = None
    container: Optional[ContainerRef] = None

    cost: Optional[float] = 0.0
    discount: Optional[float] = 0.0
    payment: Optional[float] = 0.0
    balance: Optional[float] = 0.0
    recharge: Optional[float] = 0.0

    sender: Optional[Party] = None
    receiver: Optional[Party] = None

    invoice_details: Optional[List[InvoiceDetailRef]] = None


class CustomerDocument(BaseModel):
    model_config = ConfigDict(extra="ignore")

    oldID: int = Field(..., description="Legacy Postgres PK (vwcustomer_api.id)")
    customerType: Optional[int] = None
    name: str
    phone1: Optional[str] = None
    phone2: Optional[str] = None
    idNumber: Optional[str] = None
    active: Optional[bool] = None

    createdAt: Optional[datetime] = None
    createdByID: Optional[int] = None

    branch: Optional[BranchRef] = None
    address: Optional[Address] = None
