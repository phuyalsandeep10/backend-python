"""org phone code table added

Revision ID: 20250831_074107
Revises: 20250831_051737
Create Date: 2025-08-31 13:26:08.697699

"""

from migrations.base import BaseMigration
from typing import Sequence, Union
from pathlib import Path
import json
import os


revision: str = '20250831_074107'
down_revision: Union[str, Sequence[str], None] = '20250831_051737'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT_ROOT = os.path.dirname(BASE_DIR)

class AddPhoneCodeTableMigration(BaseMigration):

    table_name = "sys_phone_codes"
    def __init__(self):
        super().__init__(revision='20250831_074107',down_revision='20250831_051737')
        self.create_whole_table=True
        # schemas
        self.base_columns()
        self.string("name", nullable=True)
        self.string("dial_code", nullable=True)
        self.string("code", nullable=True)
    

def upgrade() -> None:
  """
  Function to create a table
  """
  AddPhoneCodeTableMigration().upgrade()
  

def downgrade() -> None:
  """
  Function to drop a table
  """
  AddPhoneCodeTableMigration().downgrade()
