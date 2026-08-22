"""add new meeting status enums

Revision ID: b9e1f8c2a3d4
Revises: 6d3e3f410c59
Create Date: 2026-08-22 16:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'b9e1f8c2a3d4'
down_revision: Union[str, None] = '6d3e3f410c59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No-op: The status columns are Strings, not PostgreSQL enums.
    pass

def downgrade() -> None:
    pass
