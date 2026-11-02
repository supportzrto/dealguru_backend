
"""add payment refund reference"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "84059913b133"
down_revision: Union[str, Sequence[str], None] = "89cd4e2046b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("refund_reference", sa.String(length=100), nullable=True),
    )

    op.create_unique_constraint(
        "uq_payments_refund_reference",
        "payments",
        ["refund_reference"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_payments_refund_reference",
        "payments",
        type_="unique",
    )

    op.drop_column("payments", "refund_reference")
