from pydantic import BaseModel, Field, StrictInt


# This Pydantic model is for creating pharmacy item
class PharmacyCreate(BaseModel):

    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Apollo Pharmacy"]
    )

    medicine: str = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Paracetamol 500mg"]
    )

    quantity: StrictInt = Field(
        ...,
        ge=0,
        description="Medicine quantity must be an integer",
        examples=[100]
    )

    price: float = Field(
        ...,
        ge=0,
        description="Medicine price cannot be negative",
        examples=[25.50]
    )

    manufacturer: str = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["ABC Pharma"]
    )

    expiry_date: str = Field(
        ...,
        description="Expiry date in YYYY-MM-DD format",
        examples=["2027-12-31"]
    )


# This Pydantic model is for updating pharmacy item
class PharmacyUpdate(BaseModel):

    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Apollo Pharmacy"]
    )

    medicine: str = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Paracetamol 500mg"]
    )

    quantity: StrictInt = Field(
        ...,
        ge=0,
        examples=[100]
    )

    price: float = Field(
        ...,
        ge=0,
        examples=[25.50]
    )

    manufacturer: str = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["ABC Pharma"]
    )

    expiry_date: str = Field(
        ...,
        examples=["2027-12-31"]
    )