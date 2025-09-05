"""create_organzation_member_accesslevel

Revision ID: 20250825_060447
Revises: 20250821_043606
Create Date: 2025-08-25 11:49:48.423391

"""

from migrations.base import BaseMigration
from typing import Sequence, Union

revision: str = "20250825_060447"
down_revision: Union[str, Sequence[str], None] = "20250824_043505"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class Migration(BaseMigration):

    table_name = "org_member_accesslevel"

    def __init__(self):
        super().__init__(revision="20250825_060447", down_revision="20250824_043505")
        self.create_whole_table = True
        self.tenant_columns()
        self.string(name="access_level", length=20, default="Member", nullable=False)

        # self.foreign("team_id", "org_teams", ondelete="CASCADE")
        self.foreign("member_id", "org_members", ondelete="CASCADE")
        self.foreign("team_id", "org_teams", ondelete="CASCADE")
        # describe your schemas here


def upgrade() -> None:
    """
    Function to create a table
    """
    Migration().upgrade()


def downgrade() -> None:
    """
    Function to drop a table
    """
    Migration().downgrade()
