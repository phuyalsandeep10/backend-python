from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr


from src.modules.auth.schema import UserOutSchema

from src.common.models import TenantModel
from src.modules.organizations.schema import RoleDetailOutSchema


class TeamSchema(BaseModel):
    name: str = Field(..., max_length=250)
    description: str | None = Field(None, max_length=300)


class TeamMemberSchema(BaseModel):
    user_ids: list[int] = Field([])


class TeamResponseOutSchema(BaseModel):
    id: int
    name: str
    description: str | None
    status: str


class TeamMemberOutSchema(BaseModel):
    team_id: int
    user: UserOutSchema


class TeamMembersOutSchema(BaseModel):
    member_id: int
    username: str
    access_levels: str = ""
    email: EmailStr
    is_active: bool
    mobile: Optional[str]


class MemberAccessUpdate(BaseModel):
    access_level: str
    member_id: int

class UpdateTeamAccessSchema(BaseModel):
    members: List[MemberAccessUpdate]
