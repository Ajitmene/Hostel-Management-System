from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PlainSerializer, StringConstraints

Phone = Annotated[str, StringConstraints(pattern=r"^\+?[0-9]{7,15}$")]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
Money = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]


# Money leaves the API as a fixed two-decimal string ("500.00") whatever the database returns.
MoneyOut = Annotated[Decimal, PlainSerializer(lambda v: format(Decimal(v).quantize(Decimal("0.01")), "f"), return_type=str, when_used="json")]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    message: str


__all__ = ["date", "datetime", "Decimal", "EmailStr", "Field", "Phone", "Name", "Money", "MoneyOut", "ORMModel", "Message", "ConfigDict"]
