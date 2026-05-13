from pydantic import BaseModel


class PersonUpdate(BaseModel):
    name: str
    employee_id: str = ""
    role: str = ""
    department: str = ""


class LinkUnknownBody(BaseModel):
    unknown_id: str = ""
    snapshot: str
    person_id: str


class CreatePersonFromUnknownBody(BaseModel):
    snapshot: str
    name: str
    employee_id: str = ""
    role: str = ""
    department: str = ""


class IgnoreUnknownBody(BaseModel):
    snapshot: str
