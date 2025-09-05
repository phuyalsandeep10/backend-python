"""add user activity

Revision ID: 20250831_051737
Revises: 20250824_043505
Create Date: 2025-08-31 11:02:38.681173

"""

from migrations.base import BaseMigration
from typing import Sequence, Union
from datetime import datetime

revision: str = '20250831_051737'
down_revision: Union[str, Sequence[str], None] = '20250829_055655'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

class UseractivityModelMigration(BaseMigration):

    table_name = "org_customer_activity"
    def __init__(self):
        super().__init__(revision='20250831_051737',down_revision='20250829_055655')
        self.create_whole_table = True
        # schemas
        self.common_columns()
        self.foreign("customer_id", "org_customers", nullable=True)
        self.string("action_type", nullable=False)
        self.string("details", nullable=False)
        self.date_time(name="activity_at", default=datetime.utcnow())


def upgrade() -> None:
  """
  Function to create a table
  """
  UseractivityModelMigration().upgrade()
  

def downgrade() -> None:
  """
  Function to drop a table
  """
  UseractivityModelMigration().downgrade()
