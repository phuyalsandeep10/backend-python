import asyncio

from src.seed.organization import organization_seed_dummy, organization_user_seed_dummy
from src.seed.team import department_team_seed_dummy
from src.seed.ticket import priority_seed, sla_seed_dummy, ticket_status_seed
from src.seed.user import user_seed_dummy
from src.seed.customer import create_customer_seed
from src.seed.permissions import (
    permission_seed_dummy_group1,
    permission_seed_dummy_group2,
)
from src.seed.permission_group import permission_group_seed_dummy
from src.seed.organization_members import organization_members_seed_dummy
from src.seed.team import team_members_seed_dummy
from src.seed.timezone_country import seed_countries, seed_timezones
from src.seed.phone_code import seed_phone_codes

async def seed_func():
    await user_seed_dummy()
    await organization_seed_dummy()
    await organization_user_seed_dummy()
    await organization_members_seed_dummy()
    await department_team_seed_dummy()
    await team_members_seed_dummy()
    await permission_group_seed_dummy()

    await priority_seed()
    await ticket_status_seed()
    await sla_seed_dummy()
    await create_customer_seed()
    await seed_phone_codes()
    await permission_seed_dummy_group1()
    await permission_seed_dummy_group2()
    await seed_countries()
    await seed_timezones()


print(f"__name__ {__name__}")
if __name__ == "__main__":
    print("Running seed main script")
    asyncio.run(seed_func())
