from fastapi import HTTPException, status
from src.modules.organizations.models import OrganizationInvitation
from src.enums.organization import InvitationStatus

async def get_pending_invitation(invitation_id: int) -> OrganizationInvitation:
    invitation = await OrganizationInvitation.find_one_without_tenant(
        where={"id": invitation_id}
    )

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitation is already processed."
        )

    return invitation
