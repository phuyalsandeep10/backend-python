"""TicketNote added

Revision ID: 20250829_055655
Revises: 20250824_043505
Create Date: 2025-08-29 11:41:56.048053

"""

from typing import Sequence, Union

from migrations.base import BaseMigration

revision: str = "20250829_055655"
down_revision: Union[str, Sequence[str], None] = "20250825_060447"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class TicketNoteMigration(BaseMigration):

    table_name = "ticket_notes"

    def __init__(self):
        super().__init__(revision="20250829_055655", down_revision="20250825_060447")
        self.create_whole_table = True
        # describe your schemas here
        self.base_columns()
        self.foreign(name="created_by_id", table="sys_users", ondelete="CASCADE")
        self.foreign(name="ticket_id", table="org_tickets", ondelete="CASCADE")
        self.string(name="content")


def upgrade() -> None:
    """
    Function to create a table
    """
    TicketNoteMigration().upgrade()


def downgrade() -> None:
    """
    Function to drop a table
    """
    TicketNoteMigration().downgrade()
