from pydantic import BaseModel, Field, StrictInt


class PatientCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    age: StrictInt = Field(
        ...,
        ge=0,
        le=120,
        description="Age must be an integer between 0 and 120",
        examples=[25]
    )
    phone: str = Field(..., min_length=10, max_length=10)
    address: str = Field(..., min_length=5, max_length=200)

class PatientUpdate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    age: int = Field(..., ge=0, le=120)
    phone: str = Field(..., min_length=10, max_length=10)
    address: str = Field(..., min_length=5, max_length=200)