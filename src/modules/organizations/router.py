import email
import logging
from os import stat
from fastapi import APIRouter, Depends, HTTPException, logger, status
from datetime import datetime, timedelta
from sqlalchemy.orm import selectinload
from src.modules.auth.router import register
from src.modules.auth.schema import RegisterSchema
from src.modules.organizations.enums import AccessLevel
from src.modules.organizations.models import OrganizationRole, OrganizationMemberRole
from typing import Awaitable, List, Optional
from fastapi.logger import logger
import base64
import secrets
from src.common.context import UserContext, TenantContext


from typing import Optional
from fastapi.encoders import jsonable_encoder
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import selectinload
from src.models import Country, Timezone, User
from .service import lookup_country_by_phone_code, map_workspace_fields, validate_and_fetch_new_owner, update_owner_info
from src.common.dependencies import (
    get_bearer_token,
    get_current_user,
    update_user_cache,
    validate_role_data,
)
from src.common.models import BaseModel, Permission
from src.common.utils import random_unique_key
from src.utils.get_templates import get_templates
from src.config.settings import settings
from src.enums import InvitationStatus
from src.models import (
    Organization,
    OrganizationInvitation,
    OrganizationMember,
    OrganizationMemberRole,
    OrganizationRole,
    User,
    OrganizationInvitationRole,
    OrganizationMemberShift,
    OrganizationMemberAccessLevel,
    PhoneCode,

)

from src.models.countries import Country
from src.models.timezones import Timezone
from src.tasks import send_invitation_email
from src.utils.response import CustomResponse as cr
from src.common.invitations import get_pending_invitation 
from src.modules.staff_management.models import RolePermission
from .schema import (
    OrganizationSchema,
    OrganizationInviteSchema,
    OrganizationRoleSchema,
    OrganizationSchema,
    CreateRoleOutSchema,
    RoleDetailOutSchema,
    UpdateRoleInfoSchema,
    CreateRoleSchema,
    UpdateRoleInfoSchema,
    InvitationOut,
    GetMembersOutSchema,
    UpdateMemberSchema,
    AssignRoleSchema,
    WorkSpaceDelSchema,
    ChangeOwnerSchema,
    WorkspaceUpdateSchema,
)
import json
from pathlib import Path

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("")
async def get_organizations(user=Depends(get_current_user)):
    """
    Get the list of organizations the user belongs to.
    """
    print("The user is", user.id)
    records = await Organization.get_orgs_by_user_id(user_id=user.id)
    data = [item.to_json() for item in records]
    return cr.success(data=data)


@router.get("/current")
async def get_current_organization():
    organization_id=TenantContext.get()

    if not organization_id:
        return cr.error(message="Organization not found for the user")
    
    user_id=UserContext.get()
    organization=await Organization.get(organization_id)
    response =organization.to_json()
    
    #fetch owner
    user=await User.get(organization.owner_id)
    if not user:
        return cr.error(message="User not found")
    response['owner'] = user.to_json()
    
    return cr.success(data=response)

@router.post("")
async def create_organization(
    body: OrganizationSchema,
    user=Depends(get_current_user),
    token: str = Depends(get_bearer_token),
):
    """
    Create a new organization.
    """
    errors = []
    record = await Organization.find_one(
        where={"name": {"mode": "insensitive", "value": body.name}, "owner_id": user.id}
    )

    if record:
        errors.append({"name": "this organization with this name already exists"})

    record = await Organization.find_one(
        where={
            "domain": {"mode": "insensitive", "value": body.domain},
        }
    )

    if record:
        errors.append({"domain": "This domain already exists"})

    if errors:
        return cr.error(data=errors)

    email_alias = ""
    while True:
        # generating the random email
        token_bytes = secrets.token_bytes(9)

        # Encode to Base64 URL-safe string
        email_alias_name = (
            base64.urlsafe_b64encode(token_bytes).rstrip(b"=").decode("ascii")
        )

        email_alias = f"{email_alias_name}@{settings.EMAIL_DOMAIN}"

        # checking it the email alias exists before
        record = await Organization.find_one(
            where={"email_alias": {"mode": "insensitive", "value": email_alias}}
        )
        if record:
            continue
        break

    slug = body.name.lower().replace(" ", "-")

    organization = await Organization.create(
        name=body.name,
        description=body.description,
        slug=slug,
        logo=body.logo,
        domain=body.domain,
        purpose=body.purpose,
        identifier=f"{slug}-{random_unique_key()}",
        owner_id=user.id,
        email_alias=email_alias,
    )

    await OrganizationMember.create(
        organization_id=organization.id, user_id=user.id, is_owner=True
    )

    user_attributes = user.attributes

    if not user_attributes:
        user_attributes = {}

    if "organization_id" not in user_attributes:
        user = await User.update(
            user.id, attributes={"organization_id": organization.id}
        )

        if not user:
            raise HTTPException(404, "Not found User")

        update_user_cache(token, user)

    return cr.success(data=organization.to_json())


@router.get("/members", response_model=List[GetMembersOutSchema])
async def get_members(user=Depends(get_current_user)):
    """
    Returns all members of the current tenant organization
    """
    try:
        members = await OrganizationMember.filter(
            related_items=[
                selectinload(OrganizationMember.user),
                selectinload(OrganizationMember.shifts),
                selectinload(OrganizationMember.member_roles).selectinload(
                    OrganizationMemberRole.role
                ),
            ]
        )

        member_data = []

        for member in members:
            shift = member.shifts[0] if member.shifts else None

            shift_data = {}
            if shift:
                shift_data = {
                    "shift": shift.shift,
                    "operating_hour": f"{shift.start_time}-{shift.end_time}",
                    "client_handled": shift.client_handled,
                    "start_time": shift.start_time,
                    "end_time": shift.end_time,
                    "total_hours": shift.total_hours,
                }

            member_data.append(
                {
                    **member.to_json(schema=GetMembersOutSchema),
                    "user_name": member.user.name,
                    "email": member.user.email,
                    "image":member.user.image,
                    "user_id":member.user.id,
                    "role_ids": (
                        [mr.role.id for mr in member.member_roles]
                        if member.member_roles
                        else []
                    ),
                    "roles": (
                        [
                            {"role_id": mr.role.id, "role_name": mr.role.name}
                            for mr in member.member_roles
                        ]
                        if member.member_roles
                        else []
                    ),
                    **shift_data,
                }
            )

        return cr.success(data=member_data)

    except Exception as e:
        logger.exception(e)
        return cr.error(
            status_code=getattr(
                e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            message=f"{e.detail if hasattr(e, 'detail') else str(e)}",
            data=str(e),
        )


# @router.delete("/member/{member_id}")
# async def delete_member(member_id: int, user=Depends(get_current_user)):
#     """
#     Soft delete a member from the organization
#     """
#     try:

#         await OrganizationMember.soft_delete(where={"id": member_id})

#     except Exception as e:
#         logger.exception(e)
#         return cr.error(
#             status_code=getattr(
#                 e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR
#             ),
#             message=f"{e.detail if hasattr(e, 'detail') else str(e)}",
#             data=str(e),
#         )
#     else:
#         return cr.success(data={"message": "Member deletion successful"})


@router.delete("/member/{member_id}")
async def delete_member(member_id: int, user=Depends(get_current_user)):
    """
    Soft delete a member from the organization
    """
    try:
        where = {"id": member_id}

        member = await OrganizationMember.find_one(where=where)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        await OrganizationMember.soft_delete(where=where)

    except Exception as e:
        logger.exception(e)
        return cr.error(
            status_code=getattr(
                e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            message=f"{e.detail if hasattr(e, 'detail') else str(e)}",
            data=str(e),
        )
    else:
        return cr.success(data={"message": "Member deletion successful"})


@router.put("/member/{member_id}")
async def update_member(
    member_id: int, body: UpdateMemberSchema, user=Depends(get_current_user)
):
    """
    Update a member's details and set default access level in the team
    """
    try:

        member = await OrganizationMember.find_one(
            where={"id": member_id},
            related_items=[
                selectinload(OrganizationMember.member_roles),
                selectinload(OrganizationMember.shifts),
            ],
        )

        if not member:
            return cr.error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Member with id {member_id} not found",
            )

        if not body.start_time or not body.end_time:
            return cr.error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Start time and end time are required",
            )

        start_time = datetime.strptime(body.start_time, "%H:%M").time()
        end_time = datetime.strptime(body.end_time, "%H:%M").time()

        if start_time >= end_time:
            return cr.error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Start time must be before end time",
            )

        await OrganizationMember.update(
            member.id,
            team_id=body.team_id,
            shifts_data={"days": body.day},
        )

        for role in member.member_roles:
            await OrganizationMemberRole.delete(where={"id": role.id})

        for role_id in body.role_ids:
            await OrganizationMemberRole.create(member_id=member.id, role_id=role_id)

        for shift in member.shifts:
            await OrganizationMemberShift.delete(where={"id": shift.id})

        for day in body.day:
            await OrganizationMemberShift.create(
                **body.model_dump(exclude={"day"}),
                member_id=member.id,
                day=day,
            )

        existing_access = await OrganizationMemberAccessLevel.find_one(
            where={"member_id": member.id, "team_id": body.team_id}
        )

        if existing_access:
            await OrganizationMemberAccessLevel.update(
                existing_access.id,
                access_level=AccessLevel.MEMBER,
            )
        else:
            await OrganizationMemberAccessLevel.create(
                **body.model_dump(exclude={"team_id", "access_level"}),
                member_id=member.id,
                team_id=body.team_id,
                access_level=AccessLevel.MEMBER,
            )

        return cr.success(
            data=None,
            message="Member updated successfully",
        )

    except Exception as e:
        return cr.error(
            status_code=getattr(
                e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            message=f"{getattr(e, 'detail', str(e))}",
            data=str(e),
        )

    return cr.success(data=jsonable_encoder(result))


@router.post("/roles")
async def create_role(body: CreateRoleSchema, user=Depends(get_current_user)):
    """
    Create a New Role for an organization.
    """
    try:
        await validate_role_data(
            name=body.name,
            permissions=body.permissions,
            permission_group_id=body.permission_group,
        )

        # Create on Organzation Role
        role = await OrganizationRole.create(
            **body.model_dump(
                exclude={"permissions", "updated_at", "created_at"}, exclude_none=True
            ),
            identifier=body.name.lower().replace(" ", "-"),
        )

        # Create on role Permission Table
        role_permission_ids = []
        for perm in body.permissions:
            role_perm = await RolePermission.create(
                role_id=role.id,
                **perm.model_dump(),
            )
            role_permission_ids.append(role_perm.id)

        # update the attributes Column of Org_role
        await OrganizationRole.update(
            id=role.id,
            attributes={"no_of_agents": 0, "permissions": role_permission_ids},
        )

        return cr.success(data=None, message="Role created successfully")

    except Exception as e:
        logger.exception(e)
        return cr.error(
            status_code=getattr(
                e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            message=f"{e.detail if hasattr(e, 'detail') else str(e)}",
            data=str(e),
        )


@router.put("/roles/{role_id}")
async def update_role(
    role_id: int, body: UpdateRoleInfoSchema, user=Depends(get_current_user)
):
    try:
        role = await OrganizationRole.find_one(where={"id": role_id})
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
            )

        await validate_role_data(
            name=body.name,
            permissions=body.permissions,
            role_id=role_id,
            permission_group_id=body.permission_group,
        )

        await OrganizationRole.update(
            role_id,
            **body.model_dump(exclude={"permissions", "permission_group"}),
            identifier=body.name.lower().replace(" ", "-"),
        )

        role_permission_ids = []

        for perm in body.permissions:
            role_perm = await RolePermission.find_one(
                where={"role_id": role.id, "permission_id": perm.permission_id}
            )

            if role_perm:
                data = perm.model_dump(exclude={"permission_id"})
                await RolePermission.update(role_perm.id, **data)
                role_permission_ids.append(role_perm.id)
            else:
                data = perm.model_dump()
                new_role_perm = await RolePermission.create(
                    role_id=role.id,
                    **data,
                )
                role_permission_ids.append(new_role_perm.id)

        no_of_agents = (role.attributes or {}).get("no_of_agents")
        await OrganizationRole.update(
            id=role.id,
            attributes={
                "no_of_agents": no_of_agents,
                "permissions": role_permission_ids,
            },
        )

        return cr.success(data=None, message="Role Updated Successfully")

    except Exception as e:
        logger.exception(e)
        return cr.error(
            status_code=getattr(
                e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            message=f"{e.detail if hasattr(e, 'detail') else str(e)}",
            data=str(e),
        )


@router.get("/roles")
async def get_roles(user=Depends(get_current_user)):
    """
    List all roles with no. of agents, permission summary,
    and total members assigned in each role.
    """
    try:
        roles = await OrganizationRole.get_all(
            related_items=[
                selectinload(OrganizationRole.role_permissions).selectinload(
                    RolePermission.permission
                ),
                selectinload(OrganizationRole.member_roles),
            ]
        )

        results = []
        for role in roles:
            no_of_agents = len(role.member_roles) if role.member_roles else 0

            role_data = role.to_json(CreateRoleOutSchema)
            role_data["role_id"] = role.id
            role_data["role_name"] = role.name
            role_data["no_of_agents"] = no_of_agents

            permission_summary = []
            permission_ids = (
                role.attributes.get("permissions", []) if role.attributes else []
            )

            for rp in role.role_permissions:
                if rp.id in permission_ids:
                    if rp.is_changeable or rp.is_deletable or rp.is_viewable:
                        permission_summary.append(
                            {
                                "permission_name": (
                                    rp.permission.name if rp.permission else None
                                ),
                                "is_changeable": rp.is_changeable,
                                "is_deletable": rp.is_deletable,
                                "is_viewable": rp.is_viewable,
                            }
                        )

            role_data["permission_summary"] = permission_summary
            results.append(role_data)

        return cr.success(data=results, message="get roles successful")

    except Exception as e:
        logger.exception(e)
        return cr.error(
            status_code=getattr(
                e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            message=f"{e.detail if hasattr(e, 'detail') else str(e)}",
            data=str(e),
        )


@router.delete("/roles/{role_id}")
async def delete_role(role_id: int, user=Depends(get_current_user)):
    """
    Soft delete a role from the organization (tenant-aware).
    """
    try:
        await OrganizationRole.soft_delete(where={"id": role_id})

        return cr.success(data={"message": "Role deletion successful"})
    except Exception as e:
        logger.exception(e)
        return cr.error(
            status_code=getattr(
                e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            message=f"{e.detail if hasattr(e, 'detail') else str(e)}",
            data=str(e),
        )


# @router.post("/invitation")
# async def invite_user(body: OrganizationInviteSchema, user=Depends(get_current_user)):

#     try:
#         record = await OrganizationInvitation.find_one(
#             where={"email": body.email, "status": "pending"}
#         )

#         if record:
#             raise HTTPException(
#                 status_code=status.HTTP_409_CONFLICT,
#                 detail="An invitation already exists for this email.",
#             )

#         if user.email == body.email:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="You can't invite yourself.",
#             )

#         for role_id in body.role_ids:
#             role = await OrganizationRole.find_one(where={"id": role_id})
#             if not role:
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail=f"Invalid role",
#                 )

#         expires_at = datetime.utcnow() + timedelta(days=7)

#         invitations = await OrganizationInvitation.create(
#             **body.model_dump(),
#             invited_by_id=user.id,
#             status="pending",
#             token="",
#             expires_at=expires_at,
#         )

#         for role_id in body.role_ids:
#             await OrganizationInvitationRole.create(
#                 invitation_id=invitations.id, role_id=role_id
#             )

#         send_invitation_email.delay(email=body.email)

#         return cr.success(data=None, message="Invitation sent successfully")

#     except Exception as e:
#         logger.exception(e)
#         return cr.error(
#             status_code=getattr(
#                 e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR
#             ),
#             message=f"{e.detail if hasattr(e, 'detail') else str(e)}",
#             data=str(e),
#         )


@router.post("/invitation")
async def invite_user(body: OrganizationInviteSchema, user=Depends(get_current_user)):
    """
    Invite a user to the organization.
    """
    try:

        record = await OrganizationInvitation.find_one(
            where={"email": body.email, "status": "pending"}
        )
        if record:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An invitation already exists for this email.",
            )

        if user.email == body.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can't invite yourself.",
            )

        for role_id in body.role_ids:
            role = await OrganizationRole.find_one(where={"id": role_id})
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role ID: {role_id}",
                )

        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=7)

        invitation = await OrganizationInvitation.create(
            **body.model_dump(),
            invited_by_id=user.id,
            status="pending",
            token=token,
            expires_at=expires_at,
        )

        for role_id in body.role_ids:
            await OrganizationInvitationRole.create(
                invitation_id=invitation.id, role_id=role_id
            )

        accept_link = f"{settings.FRONTEND_URL}/settings/workspace-settings/invite-agents/accept-invitation/{invitation.id}/{token}"

        reject_link = f"{settings.FRONTEND_URL}/settings/workspace-settings/invite-agents/reject-invitation/{invitation.id}/{token}"

        html_content = await get_templates(
            "invite_email.html",
            {
                "name": body.name,
                "accept_link": accept_link,
                "reject_link": reject_link,
                "expires_at": expires_at.strftime("%Y-%m-%d %H:%M UTC"),
            },
        )

        send_invitation_email.delay(email=body.email, html_context=html_content)

        return cr.success(data=None, message="Invitation send successfully")

    except Exception as e:
        logger.exception(e)
        return cr.error(
            status_code=getattr(
                e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            message=f"{e.detail if hasattr(e, 'detail') else str(e)}",
            data=str(e),
        )


@router.get("/invitation", response_model=List[InvitationOut])
async def get_invitations(user=Depends(get_current_user)):
    """
    Get all pending invitations for the current user.
    """
    invitations = await OrganizationInvitation.filter_without_tenant(
        where={"status": "pending"},
        related_items=[
            selectinload(OrganizationInvitation.invitation_roles).selectinload(
                OrganizationInvitationRole.role
            )
        ],
    )

    data = [
        {
            **inv.to_json(schema=InvitationOut),
            "role_names": [
                RoleDetailOutSchema(
                    role_id=invrole.role.id, role_name=invrole.role.name
                ).model_dump()
                for invrole in inv.invitation_roles
                if invrole.role
            ],
        }
        for inv in invitations
    ]

    return cr.success(data=data)

@router.post("/invitation/{invitation_id}/accept/{token}")
async def accept_invitation(invitation_id: int, token:str):

    invitation = await get_pending_invitation(invitation_id)

    TenantContext.set(invitation.organization_id)

    if token != invitation.token:
        record = await OrganizationInvitation.update(
            invitation.id, status=InvitationStatus.REJECTED
        )
    return cr.success(data=record)

@router.get("/countries")
async def get_countries():
    """Get all countries for selection"""
    try:

        countries = await Country.filter()

        countries_data = [
            {
                "id": country.id,
                "name": country.name,
                "code": country.iso_code_2,
                "iso_code_2": country.iso_code_2,  # US
                "iso_code_3": country.iso_code_3,  # USA
                "phone_code": country.phone_code,  # +977
            }
            for country in countries
        ]

        return cr.success(
            data={"countries": countries_data},
            message="Countries retrieved successfully",
        )
    except Exception as e:
        return cr.error(message=f"Failed to retrieve countries: {str(e)}")


@router.get("/timezones")
async def get_timezones(country_id: Optional[int] = None):
    """Get all timezones, optionally filtered by country_id"""
    try:
        where_clause = {}
        if country_id:
            where_clause["country_id"] = country_id

        timezones = await Timezone.filter(
            where=where_clause,
            related_items=[
                selectinload(Timezone.country)
            ],  # for loading countries relationship
        )

        timezones_data = [
            {
                "id": tz.id,
                "name": tz.name,
                "display_name": tz.display_name,
                "country_id": tz.country_id,
                "country_code":tz.country.iso_code_2,
                "country_name": tz.country.name if tz.country else None,
            }
            for tz in timezones
        ]

        return cr.success(
            data={"timezones": timezones_data},
            message="Timezones retrieved successfully",
        )

    except Exception as e:
        return cr.error(message=f"Failed to retrieve timezones: {str(e)}")

@router.get("/phone-codes")
async def get_phone_codes():
    """Get all phone codes"""
    phone_codes= await PhoneCode.get_all()
    if not phone_codes:
        return cr.error(message="Failed to retreive phone codes")
    
    return cr.success(data=jsonable_encoder(phone_codes), message="Phone code retreived successfully")


@router.post("/invitation/{invitation_id}/accept")
async def accept_invitation(invitation_id: int, user=Depends(get_current_user)):
    invitation = await OrganizationInvitation.find_one(where={"id": invitation_id})

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if user.email != invitation.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to accept this invitation"
        )

    user = await User.find_one(where={"email": invitation.email})
    if not user:
        register_user = RegisterSchema(
            name=invitation.name,
            email=invitation.email,
            password="test12345"
        )
        register_request = await register(register_user)

        user = await User.find_one(where={"email": invitation.email})

    await OrganizationMember.create(user_id=user.id,organization_id=invitation.organization_id)

    invitation.status="Accepted"
    await invitation.update(invitation.id, status="Accepted")

    return cr.success(data=None, message="Account accepted and created  succesffully please check your mail once")
         



@router.post("/invitation/{invitation_id}/reject/{token}")
async def reject_invitation(invitation_id: int, token: str):
    
    invitation = await get_pending_invitation(invitation_id)
    
    """
    invitation = await OrganizationInvitation.find_one_without_tenant(
        where={"id": invitation_id}
    )

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found"
        )

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitation is already processed.",
        )
     """

    TenantContext.set(invitation.organization_id)

    if token != invitation.token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to reject this invitation",
        )

    await OrganizationInvitation.update(invitation.id, status=InvitationStatus.REJECTED)

    return cr.success(data=None, message="Invitation has been rejected")


@router.delete("/invitations/{invitation_id}")
async def delete_invitation(invitation_id: int, user=Depends(get_current_user)):
    """
    Soft delete an invitation from the organization (tenant-aware).
    """
    await OrganizationInvitation.soft_delete(where={"id": invitation_id})

    return cr.success(data={"message": "Invitation successfully deleted"})


@router.post("/roles-assign")
async def assign_role(body: AssignRoleSchema, user=Depends(get_current_user)):
    organization_id = user.attributes.get("organization_id")
    member = await OrganizationMember.find_one(
        where={"organization_id": organization_id, "user_id": body.user_id}
    )

    if not member:
        raise HTTPException(400, "Organization Member not found")

    member_role = await OrganizationMemberRole.find_one(
        where={"member_id": member.id, "role_id": body.role_id}
    )

    if not member_role:
        await OrganizationMemberRole.create(role_id=body.role_id, member_id=member.id)

    return cr.success(data={"message": "Successfully assign"})


@router.post("/remove-assign-role")
async def remove_assign_role(body: AssignRoleSchema, user=Depends(get_current_user)):
    organization_id = user.attributes.get("organization_id")

    member = await OrganizationMember.find_one(
        where={"organization_id": organization_id, "user_id": body.user_id}
    )

    if not member:
        raise HTTPException(400, "Organization Member not found")

    member_role = await OrganizationMemberRole.find_one(
        {"member_id": member.id, "role_id": body.role_id}
    )

    if not member_role:
        raise HTTPException(400, "Role not found")

    await OrganizationMemberRole.soft_delete(member_role.id)
    return cr.success(data={"message": "Successfully remove role"})


@router.get("/permissions")
async def get_permissions(user=Depends(get_current_user)):
    permissions = await Permission.filter()
    return cr.suc



@router.get("/{organization_id}")
async def get_organization_by_id(organization_id : int, user=Depends(get_current_user)):
    """
    Get the organization details by id
    """
    organization=await Organization.find_one(where={'id': organization_id})

    if not organization:
        return cr.error(data={"success": False}, message="Unable to find organization with the id")

    return cr.success(data=jsonable_encoder(organization))


@router.patch("/update-workspace")
async def update_workspace(body: WorkspaceUpdateSchema, user=Depends(get_current_user)):
    try:
        organization_id = TenantContext.get()
        user_id = UserContext.get()
        current_owner=user=await User.get(user_id)

        body_data = body.model_dump(exclude_unset=True)

        country = await lookup_country_by_phone_code(body.phone_code) if body.phone_code else None
        country_id = country.id if country else None

        workspace_updates = map_workspace_fields(body_data, country_id, body.phone_code)
        updated_owner=None
        if "owner_id" in body_data and body.owner_id:
            org_member, new_owner_user = await validate_and_fetch_new_owner(
                organization_id, body.owner_id
            )
            if not org_member:
                return cr.error(
                    data={'success': False},
                    message='Sorry, the new owner is not an organization member'
                )
            workspace_updates["owner_id"] =new_owner_user.id
        
        # Update workspace
        updated_workspace = await Organization.update(organization_id, **workspace_updates)

        if not updated_workspace:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        workspace=updated_workspace.to_json()
        updated_owner= await update_owner_info(updated_workspace.owner_id,body_data)
        if updated_owner:
            workspace["owner"]=updated_owner.to_json()
        workspace["owner"]=current_owner.to_json()

        return cr.success(
            data=workspace,
            message="Workspace updated successfully"
        )
        
    except Exception:
        logger.exception("Unexpected error while updating workspace")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating the workspace"
        )

@router.post("/delete-workspace")
async def delete_workspace(body: WorkSpaceDelSchema, token: str = Depends(get_bearer_token)):
    try:
        userId = UserContext.get()
        user = await User.get(userId)
        organization_id=TenantContext.get()
        print(f"org_owner_id {user.id}")
        # Check if the organization exists for the given and user
        organization = await Organization.get(
            organization_id
        )
        print(f"organization_id found {organization.id}")
        
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found for the given user"
            )

        # Soft delete the organization
        await Organization.soft_delete(where={"id": organization.id})
        

        if user.attributes.get("organization_id") == organization.id:
            user = await User.update(userId,attributes={**user.attributes,"organization_id":None})
            update_user_cache(token, user)
        

        return cr.success(
            data={"message": f"Successfully deleted the workspace owned by {user.name}"}
        )

    except Exception as e:
        logger.exception("Unexpected error while deleting workspace")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the workspace"
        )


@router.put("/{organization_id}")
async def update_organization(
    organization_id: int, body: OrganizationSchema, user=Depends(get_current_user)
):
    """
    Update an existing organization.
    """

    organization = await Organization.get(organization_id)

    organization_member = await OrganizationMember.find_one(
        {"organization_id": organization_id, "user_id": user.id}
    )

    if not organization_member:
        return cr.error(
            data={"success": False},
            message="You do not have permission to update this organization",
        )

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    if organization.name != body.name:
        existing_org = await Organization.find_one(
            {"name": {"value": body.name, "mode": "insensitive"}}
        )
        if existing_org:
            return cr.error(
                data={"success": False},
                message="Organization with this name already exists",
            )
    record = await Organization.find_one(
        where={
            "domain": {"mode": "insensitive", "value": body.domain},
        }
    )

    if record and record.domain != body.domain:
        return cr.error(
            data={"success": False}, message="This domain is already exists"
        )

    record = await Organization.update(
        organization_id,
        name=body.name,
        description=body.description,
        logo=body.logo,
        domain=body.domain,
    )

    return cr.success(data=record)


@router.put("/{organization_id}/set")
async def set_organization(
    organization_id: int,
    user=Depends(get_current_user),
    token: str = Depends(get_bearer_token),
):
    """
    Set an existing organization.
    """

    organization = await Organization.get(organization_id)

    user = await User.update(user.id, attributes={"organization_id": organization_id})

    if not user:
        raise HTTPException(404, "Not found User")

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    update_user_cache(token, user)

    return cr.success(data={"message": "Organization set successfully"})
