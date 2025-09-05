from typing import Optional, List
from src.common.models import BaseModel
from sqlmodel import Field, Relationship


class PhoneCode(BaseModel, table=True):
    __tablename__ = "sys_phone_codes"

    name: str = Field(nullable=False)
    dial_code: str = Field(max_length=2, nullable=False) 
    code: str = Field(max_length=3, nullable=False)  
    
    
