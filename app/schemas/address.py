
from pydantic import BaseModel, Field, ConfigDict, field_validator


class AddressCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=10, max_length=20)
    pincode: str = Field(pattern=r"^\d{6}$")
    line1: str = Field(min_length=1, max_length=120)
    line2: str = Field(default="", max_length=120)
    landmark: str = Field(default="", max_length=80)
    city: str = Field(min_length=1, max_length=60)
    state: str = Field(min_length=1, max_length=60)
    address_type: str = Field(default="Home", max_length=20)
    is_default: bool = False


class AddressUpdate(AddressCreate):
    pass


class AddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    phone: str
    pincode: str
    line1: str
    line2: str
    landmark: str
    city: str
    state: str
    address_type: str
    is_default: bool

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_string(cls, value):
        return str(value)
