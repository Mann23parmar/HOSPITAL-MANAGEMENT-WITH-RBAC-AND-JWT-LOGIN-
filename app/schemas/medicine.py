from pydantic import BaseModel, Field, StrictInt, StrictFloat


class MedicineCreate(BaseModel):

    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Paracetamol"]
    )

    manufacturer: str = Field(
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

    expiry_date: str = Field(
        ...,
        examples=["2027-12-31"]
    )


class MedicineUpdate(BaseModel):

    name: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    manufacturer: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    quantity: StrictInt = Field(
        ...,
        ge=0
    )

    price: StrictFloat = Field(
        ...,
        gt=0
    )

    expiry_date: str