from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Cardiology"]
    )

    location: str = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["2nd Floor"]
    )

    description: str = Field(
        ...,
        min_length=5,
        max_length=300,
        examples=["Department for heart-related treatments"]
    )


class DepartmentUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        examples=["Cardiology"]
    )

    location: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        examples=["2nd Floor"]
    )

    description: str | None = Field(
        default=None,
        min_length=5,
        max_length=300,
        examples=["Department for heart-related treatments"]
    )