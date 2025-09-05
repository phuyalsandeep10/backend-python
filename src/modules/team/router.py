from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import selectinload
import logging

from fastapi import APIRouter, Depends, HTTPException, logger, status
from src.common.context import TenantContext
from src.common.permissions import get_current_user
from src.modules.organizations.models import (
    OrganizationMember,
    OrganizationMemberRole,
    OrganizationMemberAccessLevel,
)
from src.modules.auth.schema import UserOutSchema
from src.utils.response import CustomResponse as cr

from .models import Team, TeamMember
from .schema import (
    TeamMemberSchema,
    TeamSchema,
    TeamResponseOutSchema,
    TeamMemberOutSchema,
    TeamMembersOutSchema,
    RoleDetailOutSchema,
    UpdateTeamAccessSchema,
)
from typing import List

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("")
async def create_team(body: TeamSchema, user=Depends(get_current_user)):
    if not TenantContext:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    record = await Team.find_one(
        where={"name": {"mode": "insensitive", "value": body.name}}
    )

    if record:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Team Name Already Exists"
        )

    team = await Team.create(**body.model_dump())

    return cr.success(data=None, message="Team Created Successfully")


@router.get("", response_model=List[TeamResponseOutSchema])
async def get_teams(user=Depends(get_current_user)):
    if not TenantContext.get():
        raise HTTPException(403, detail="Not authorized")

    # Fetch all teams with related access levels -> members -> users
    teams = await Team.filter(
        related_items=[
            selectinload(Team.access_levels)
            .selectinload(OrganizationMemberAccessLevel.member)
            .selectinload(OrganizationMember.user)
        ]
    )

    result = []
    for team in teams:
        team_data = team.to_json(schema=TeamResponseOutSchema)

        lead = next(
            (al for al in team.access_levels if al.access_level.upper() == "LEAD"),
            None,
        )

        team_data["lead_name"] = (
            getattr(lead.member.user, "name", None) if lead else None
        )

        team_data["status"] = "Online"
        
        result.append(team_data)

    return cr.success(data=result)


# @router.put("/{team_id}")
# async def update_data(team_id: int, body: TeamSchema, user=Depends(get_current_user)):
#     # user update data
#     organizationId = user.attributes.get("organization_id")

#     if not organizationId:
#         raise HTTPException(403, "Not authorized")

#     team = await Team.get(team_id)

#     if not team:
#         raise HTTPException(404, "Not found")

#     record = await Team.find_one(
#         where={
#             "name": {"mode": "insensitive", "value": body.name},
#             "organization_id": organizationId,
#         }
#     )

#     if record and record.id != team.id:
#         raise HTTPException(400, "Duplicate record")

#     team = await Team.update(
#         team_id,
#         name=body.name,
#         description=body.description,
#         organization_id=organizationId,
#     )

#     return cr.success(data=team.to_json())


@router.delete("/{team_id}")
async def delete_team(team_id: int, user=Depends(get_current_user)):
    """
    Soft delete a team by ID.
    """
    try:
        team = await Team.find_one_without_tenant(where={"id": team_id})

        await Team.soft_delete(
            where={"id": team_id, "organization_id": team.organization_id}
        )

        return cr.success(data=None, message="Team deleted successfully")

    except Exception as e:
        logger.exception(e)
        return cr.error(
            status_code=getattr(
                e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            message=f"{e.detail if hasattr(e, 'detail') else str(e)}",
            data=str(e),
        )


# @router.put("/{team_id}/assign-member")
# async def assign_team_member(
#     team_id: int, body: TeamMemberSchema, user=Depends(get_current_user)
# ):
#     team = await Team.get(team_id)
#     if not team:
#         raise HTTPException(404, "Team not found")

#     current_members = await TeamMember.filter(where={"team_id": team_id})
#     current_user_ids = {member.user_id for member in current_members}

#     new_user_ids = set(body.user_ids)

#     to_add = new_user_ids - current_user_ids
#     to_remove = current_user_ids - new_user_ids

#     for user_id in to_add:
#         await TeamMember.create(team_id=team_id, user_id=user_id)

#     for user_id in to_remove:
#         member = await TeamMember.find_one(
#             where={"team_id": team_id, "user_id": user_id}
#         )

#         if not member:
#             raise HTTPException(404, "Not found")
#         if member:
#             await TeamMember.soft_delete(member.id)

#     return cr.success(data={"message": "Team members updated successfully"})


# @router.get("/{team_id}/team-members")
# async def get_team_members(team_id: int):

#     members = await TeamMember.filter(
#         where={"team_id": team_id}, related_items=[selectinload(TeamMember.user)]
#     )

#     return cr.success(
#         data=[
#             member.to_json(
#                 schema=TeamMemberOutSchema,
#                 include_relationships=True,
#                 related_schemas={"user": UserOutSchema},
#             )
#             for member in members
#         ]
#     )


@router.get("/{team_id}")
async def get_members_by_team(team_id: int, user=Depends(get_current_user)):
    """
    Returns all active (not soft-deleted) members in a specific team.
    """
    try:
        members: List[OrganizationMember] = await OrganizationMember.filter(
            where={"team_id": team_id},
            related_items=[
                selectinload(OrganizationMember.user),
                selectinload(OrganizationMember.access_levels),
            ],
        )

        if not members:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No members found for team_id={team_id}",
            )

        result = []

        for member in members:
            active_levels = [
                act_lvl
                for act_lvl in member.access_levels
                if act_lvl.team_id == team_id and act_lvl.deleted_at is None
            ]
            if not active_levels:
                continue

            access_level = active_levels[0].access_level

            result.append(
                TeamMembersOutSchema(
                    member_id=member.id,
                    username=member.user.name,
                    email=member.user.email,
                    mobile=member.user.mobile,
                    is_active=member.user.is_active,
                    access_levels=access_level,
                )
            )

        return cr.success(
            data=[member.dict() for member in result],
            message="Members fetched successfully",
        )

    except Exception as e:
        return cr.error(
            status_code=getattr(e, "status_code", 500),
            message=f"{getattr(e, 'detail', str(e))}",
            data=str(e),
        )


@router.delete("/team/{team_id}/member/{member_id}/access-level")
async def remove_member_access_level(
    team_id: int, member_id: int, user=Depends(get_current_user)
):
    """
    Remove the access level of a member in a team (does not delete the member itself).
    """
    try:
        member = await OrganizationMember.find_one(
            where={"id": member_id, "team_id": team_id}
        )

        if not member:
            raise HTTPException(status_code=404, detail="Member not found in this team")

        await OrganizationMemberAccessLevel.soft_delete(where={"member_id": member.id})

        return cr.success(data={"message": "Member access level removed successfully"})

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/{team_id}/members/access-level")
async def update_team_members_access_level(
    team_id: int,
    payload: UpdateTeamAccessSchema,
    user=Depends(get_current_user),
):
    """
    Update access level for multiple members in a team.
    """
    for member_data in payload.members:
        member_id = member_data.member_id
        access_level = member_data.access_level.upper()

        member = await OrganizationMember.find_one({"id": member_id})
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member with id={member_id} not found",
            )

        if access_level == "LEAD":
            existing_lead = await OrganizationMemberAccessLevel.find_one(
                {"team_id": team_id, "access_level": "LEAD"}
            )
            if existing_lead and existing_lead.member_id != member_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A LEAD already exists in this team",
                )

        access_obj = await OrganizationMemberAccessLevel.find_one(
            {"member_id": member_id, "team_id": team_id}
        )
        if access_obj:
            await OrganizationMemberAccessLevel.update(
                access_obj.id, access_level=access_level
            )
        else:
            await OrganizationMemberAccessLevel.create(
                member_id=member_id,
                team_id=team_id,
                access_level=access_level,
            )

    return cr.success(data=None, message="Access levels updated successfully")
