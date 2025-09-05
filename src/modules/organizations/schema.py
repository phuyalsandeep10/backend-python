from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from src.common.schemas import BaseModel
from datetime import datetime
from src.modules.organizations.enums import WeekDay, ShiftType


class OrganizationSchema(BaseModel):
    name: str = Field(..., max_length=255, description="Name of the organization")
    description: str | None = Field(
        None, max_length=500, description="Description of the organization"
    )
    domain: str = Field(..., max_length=255, description="Domain of the organization")

    logo: str | None = Field(
        None, max_length=255, description="Logo URL for the organization"
    )
    purpose: str | None = Field(
        None, max_length=255, description="Purpose of organization creation"
    )



class OrganizationRoleSchema(BaseModel):
    name: str = Field(..., max_length=255, description="Name of the role")
    description: str | None = Field(
        None, max_length=500, description="Description of the role"
    )


class PermissionSchema(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = Field(None, max_length=250)


class OrganizationInviteSchema(BaseModel):
    email: EmailStr
    role_ids: List[int]
    name: str


class OrganizationInviteOutSchema(BaseModel):
    email: EmailStr
    created_at: datetime
    status: str
    role_ids: List[int]
    role_name: str | None


class OrganizationInvitationApproveSchema(BaseModel):
    email: EmailStr
    token: str


class AssignRoleSchema(BaseModel):
    user_id: int
    role_id: int


class AssignPermissionSchema(BaseModel):
    permission_ids: List[int]


class RolePermissionInSchema(BaseModel):
    role_id: int
    permission_id: int
    value: bool = False


class CreateRoleOutSchema(BaseModel):
    role_id: int
    role_name: str
    description: str
    org_name: str


class UpdateRoleInSchema(BaseModel):
    permission_id: int
    is_changeable: bool = False
    is_deletable: bool = False
    is_viewable: bool = False


class UpdateRoleInfoSchema(BaseModel):
    name: str = Field(..., max_length=100, description="Name of the role")
    permission_group: int

    description: str | None = Field(
        None, max_length=500, description="Description of the role"
    )
    permissions: List[UpdateRoleInSchema] = []


class CreateRoleSchema(BaseModel):
    name: str = Field(..., max_length=100)
    description: str = Field(..., max_length=500)
    permission_group: int
    permissions: List[UpdateRoleInSchema] = []


class CreateRoleOutSchema(BaseModel):
    role_id: int
    role_name: str
    description: str | None
    org_name: str
    created_at: str
    no_of_agents: int
    permission_summary: str = ""


class RoleDetailOutSchema(BaseModel):
    role_id: int
    role_name: str


class InvitationOut(BaseModel):
    id: int
    name: str
    email: str
    status: str
    invited_by_id: int
    role_ids: List[int] = []
    created_at: datetime
    role_names: List[RoleDetailOutSchema] = []


class GetMembersOutSchema(BaseModel):
    id: int
    user_name: str
    role_name: str
    created_at: datetime
    shift: str | None
    operating_hour: str | None
    client_handled: str | None
    start_time: str | None
    end_time: str | None
    total_hours: float | None
    email: EmailStr
    image:str | None
    user_id : int


class UpdateMemberSchema(BaseModel):
    role_ids: List[int] = []
    client_handled: Optional[str] = None
    day: List[WeekDay]
    shift: ShiftType
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    # team_id: Optional[int] = None
    team_id: int
    total_hours: int

class WorkSpaceDelSchema(BaseModel):
    identifier : str

class ChangeOwnerSchema(BaseModel):
    organization_id:int
    owner_id: int


class WorkspaceUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, max_length=255, description="Name of the workspace")
    domain: Optional[str] = Field(None, description="Domain associated with the workspace")
    owner_name: Optional[str] = Field(None, description="UUID or ID of the workspace owner")
    owner_id : Optional[int] = Field(None, description="user id of the workspace owner")
    phone: Optional[str] = Field(None, description="Contact phone of the organization")
    timezone_id : Optional[int] = Field(None, description="Timezoneid")
    owner_image: Optional[str] = Field(
        None, description="Profile picture URL of the workspace"
    )
    email: Optional[EmailStr] = Field(
        None, description="Contact email of the workspace"
    )
    phone_code: Optional[str] = Field(
        None, max_length=20, description="Contact phone number of the workspace"
    )
    telegram: Optional[str] = Field(
        None, description="Telegram handle or link"
    )
    twitter: Optional[str] = Field(
        None, description="Twitter/X handle or profile link"
    )
    whatsapp : Optional[str]= Field(
        None, description=" Whatsapp number"
    )
    facebook : Optional[str]= Field(
        None, description=" Facebook handle"
    )
