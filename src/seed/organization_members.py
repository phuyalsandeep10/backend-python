from src.modules.organizations.models import OrganizationMember, Organization


organization_members = [
    {"user_id": 3, "organization_id": 1},
    {"user_id": 4, "organization_id": 1},
    {"user_id": 5, "organization_id": 2},
    {"user_id": 6, "organization_id": 2},
]


async def organization_members_seed_dummy():
    # Add predefined members
    for user in organization_members:
        user_exist = await OrganizationMember.find_one(
            where={
                "user_id": user["user_id"],
                "organization_id": user["organization_id"],
            }
        )
        if not user_exist:
            await OrganizationMember.create(**user)
            print(f"Organization member created: {user}")

    # Now also ensure each organization owner is a member
    organizations = await Organization.get_all()  # get all orgs
    for org in organizations:
        if org.owner_id:  # check owner exists
            owner_exist = await OrganizationMember.find_one(
                where={
                    "user_id": org.owner_id,
                    "organization_id": org.id,
                }
            )
            if not owner_exist:
                await OrganizationMember.create(
                    user_id=org.owner_id,
                    organization_id=org.id,
                )
                print(
                    f"Owner {org.owner_id} added as member to organization {org.id}"
                )
