from pydantic import BaseModel, Field, StrictStr
from app.schemas.update_payload import UpdatePayload


class DepartmentCreate(BaseModel):

    name: StrictStr = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Cardiology"]
    )

    location: StrictStr = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["2nd Floor"]
    )

    description: StrictStr = Field(
        ...,
        min_length=5,
        max_length=300,
        examples=["Department for heart-related treatments"]
    )


class DepartmentUpdate(UpdatePayload):

    name: StrictStr | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        examples=["Cardiology"]
    )

    location: StrictStr | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        examples=["2nd Floor"]
    )

    description: StrictStr | None = Field(
        default=None,
        min_length=5,
        max_length=300,
        examples=["Department for heart-related treatments"]
    )
