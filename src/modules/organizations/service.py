from .models import OrganizationMember
from src.modules.auth.models import User
from src.models import Country, User

async def lookup_country_by_phone_code(phone_code: str):
    if not phone_code:
        return None
    return await Country.find_one(where={"phone_code": phone_code})


def map_workspace_fields(body_data: dict, country_id: int | None = None, phone_code: str | None = None):
    field_map = {
        "name": "name",
        "email": "contact_email",
        "domain": "domain",
        "twitter": "twitter_username",
        "facebook": "facebook_username",
        "telegram": "telegram_username",
        "whatsapp": "whatsapp_number",
        "phone": "contact_phone",
        "timezone_id": "timezone_id",
    }

    updates = {mapped: body_data[src] for src, mapped in field_map.items() if src in body_data}

    if phone_code:
        updates["contact_dial_code"] = phone_code
    if country_id:
        updates["country_id"] = country_id

    return updates


async def validate_and_fetch_new_owner(organization_id: int, new_owner_id: int):
    org_member = await OrganizationMember.find_one(
        where={'organization_id': organization_id, 'user_id': new_owner_id}
    )
    if not org_member:
        return None, None
    new_owner_user = await User.find_one(where={'id': new_owner_id})
    return org_member, new_owner_user


async def update_owner_info(owner_id: int, body_data: dict):
    """
    Update the owner's image and/or name if provided in body_data
    and also update the workspace JSON with the new values.
    """
    owner_update_data = {}

    if "owner_image" in body_data:
        owner_update_data["image"] = body_data["owner_image"]
    if "owner_name" in body_data:
        owner_update_data["name"] = body_data["owner_name"]
    if owner_update_data:
        updated_user=await User.update(owner_id, **owner_update_data)
        if not updated_user:
            return cr.error(message="Failed to update the owner data")
        return updated_user
