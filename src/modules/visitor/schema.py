from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List



class CustomerEmailSchema(BaseModel):
    email: EmailStr
    
class CustomerSchema(BaseModel):
    id: int
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

class LocationSchema(BaseModel):
    longitude: float
    latitude: float
    count: int

class VisitorLogsSchema(BaseModel):
    id : int
    customer_id : int
    visitor_name:Optional[str]
    status : Optional[str]
    last_active : Optional[str] 
    active_duration : Optional[str]
    num_of_visits : int
    engagged : Optional[str]
    ip_address : Optional[str]

class VisitorsResponseSchema(BaseModel):
    visitors: List[VisitorLogsSchema]
    visitors_by_location: List[LocationSchema]

class ActivitySchema(BaseModel):
    action_type: Optional[Optional[str]]
    details: Optional[Optional[str]]
    activity_at: Optional[datetime]

class VisitorSchema(BaseModel):
    customer_id : int
    email: Optional[str]
    picture: Optional[str]
    engagged: Optional[str]
    ip_address: Optional[str]
    location : Optional[str]
    browser : Optional[str]
    login_time : Optional[datetime]
    activities: Optional[List] = []
