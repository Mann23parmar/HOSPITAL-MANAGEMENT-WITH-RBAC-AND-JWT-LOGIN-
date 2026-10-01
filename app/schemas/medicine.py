from datetime import date

from pydantic import BaseModel, Field, StrictFloat, StrictInt, StrictStr, field_validator


class MedicineCreate(BaseModel):

    name: StrictStr = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Paracetamol"]
    )

    manufacturer: StrictStr = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["ABC Pharmaceuticals"]
    )

    quantity: StrictInt = Field(
        ...,
        ge=0,
        examples=[100]
    )

    price: StrictFloat = Field(
        ...,
        gt=0,
        examples=[25.50]
    )

    expiry_date: date = Field(
        ...,
        examples=["2027-12-31"]
    )

    @field_validator("expiry_date")
    @classmethod
    def validate_expiry_date(cls, value: date):
        if value <= date.today():
            raise ValueError("Expiry date must be in the future")
        return value


class MedicineUpdate(BaseModel):

    name: StrictStr | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    manufacturer: StrictStr | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    quantity: StrictInt | None = Field(
        default=None,
        ge=0
    )

    price: StrictFloat | None = Field(
        default=None,
        gt=0
    )

    expiry_date: date | None = Field(
        default=None,
        examples=["2027-12-31"]
    )

    @field_validator("expiry_date")
    @classmethod
    def validate_expiry_date(cls, value: date | None):
        if value is not None and value <= date.today():
            raise ValueError("Expiry date must be in the future")
        return value