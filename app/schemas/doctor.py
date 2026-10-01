from pydantic import BaseModel, Field, StrictStr


class DoctorCreate(BaseModel):

    user_id: StrictStr = Field(
        ...,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$",
        examples=["66f123456789abcdef123456"]
    )

    department_id: StrictStr = Field(
        ...,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$",
        examples=["66f987654321abcdef654321"]
    )

    name: StrictStr = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Rahul Sharma"]
    )

    specialization: StrictStr = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Cardiology"]
    )

    phone: StrictStr = Field(
        ...,
        min_length=10,
        max_length=15,
        pattern=r"^\d{10,15}$",
        examples=["9876543210"]
    )


class DoctorUpdate(BaseModel):

    user_id: StrictStr | None = Field(
        default=None,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$"
    )

    department_id: StrictStr | None = Field(
        default=None,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$"
    )

    name: StrictStr | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    specialization: StrictStr | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    phone: StrictStr | None = Field(
        default=None,
        min_length=10,
        max_length=15,
        pattern=r"^\d{10,15}$"
    )