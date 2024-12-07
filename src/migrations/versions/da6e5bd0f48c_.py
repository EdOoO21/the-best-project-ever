"""empty message

Revision ID: da6e5bd0f48c
Revises: 266e31b54cc8
Create Date: 2024-12-15 02:46:10.395674

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da6e5bd0f48c'
down_revision: Union[str, None] = '266e31b54cc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
