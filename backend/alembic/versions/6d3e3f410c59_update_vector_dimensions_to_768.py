"""update vector dimensions to 768

Revision ID: 6d3e3f410c59
Revises: d58279f9b3a1
Create Date: 2026-08-22 15:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector

# revision identifiers
revision: str = '6d3e3f410c59'
down_revision: Union[str, None] = 'd58279f9b3a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # We must drop the column or truncate and alter because pgvector restricts casting between dimensions.
    # The safest approach for local dev that preserves the table is to clear the rows, then alter the column type.
    op.execute("TRUNCATE TABLE transcript_chunks RESTART IDENTITY CASCADE;")
    
    op.alter_column(
        'transcript_chunks', 'embedding',
        existing_type=pgvector.sqlalchemy.vector.VECTOR(dim=1536),
        type_=pgvector.sqlalchemy.vector.VECTOR(dim=768),
        existing_nullable=True
    )

def downgrade() -> None:
    op.execute("TRUNCATE TABLE transcript_chunks RESTART IDENTITY CASCADE;")
    
    op.alter_column(
        'transcript_chunks', 'embedding',
        existing_type=pgvector.sqlalchemy.vector.VECTOR(dim=768),
        type_=pgvector.sqlalchemy.vector.VECTOR(dim=1536),
        existing_nullable=True
    )
