from pydantic import BaseModel, Field, StrictFloat, StrictInt, StrictStr


class PatientVitalsCreate(BaseModel):

    patient_id: StrictStr = Field(
        ...,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$",
        examples=["66f123456789abcdef123456"]
    )

    nurse_id: StrictStr = Field(
        ...,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$",
        examples=["66f987654321abcdef654321"]
    )

    blood_pressure: StrictStr = Field(
        ...,
        min_length=3,
        max_length=20,
        examples=["120/80"]
    )

    temperature: StrictFloat = Field(
        ...,
        gt=0,
        examples=[98.6]
    )

    pulse_rate: StrictInt = Field(
        ...,
        gt=0,
        examples=[72]
    )

    weight: StrictFloat = Field(
        ...,
        gt=0,
        examples=[65.5]
    )


class PatientVitalsUpdate(BaseModel):

    patient_id: StrictStr | None = Field(
        default=None,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$"
    )

    nurse_id: StrictStr | None = Field(
        default=None,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$"
    )

    blood_pressure: StrictStr | None = Field(
        default=None,
        min_length=3,
        max_length=20
    )

    temperature: StrictFloat | None = Field(
        default=None,
        gt=0
    )

    pulse_rate: StrictInt | None = Field(
        default=None,
        gt=0
    )

    weight: StrictFloat | None = Field(
        default=None,
        gt=0
    )