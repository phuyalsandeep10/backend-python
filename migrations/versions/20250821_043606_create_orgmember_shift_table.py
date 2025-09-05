"""create_orgmember_shift_table

Revision ID: 20250821_043606
Revises: 20250819_072251
Create Date: 2025-08-21 10:21:06.846974
"""

from migrations.base import BaseMigration
from typing import Sequence, Union

revision: str = "20250821_043606"
down_revision: Union[str, Sequence[str], None] = "20250819_072251"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class OrganizationMemberShiftMigration(BaseMigration):
    table_name = "org_member_shifts"

    def __init__(self):
        super().__init__(revision="20250821_043606", down_revision="20250819_072251")

        self.tenant_columns()

        # self.integer(name="team_id", nullable=True)
        self.string(name="day", length=10, nullable=False)
        self.string(name="shift", length=10, nullable=False)
        self.string(name="start_time", nullable=True)
        self.string(name="end_time", nullable=True)
        self.float(name="total_hours", nullable=True)
        self.string(name="client_handled", default=False, nullable=False)

        # foreign keys
        self.foreign("member_id", "org_members", ondelete="CASCADE")
        self.foreign("team_id", "org_teams", ondelete="SET NULL")


def upgrade() -> None:
    """
    Function to create the table
    """
    OrganizationMemberShiftMigration().upgrade()


def downgrade() -> None:
    """
    Function to drop the table
    """
    OrganizationMemberShiftMigration().downgrade()
