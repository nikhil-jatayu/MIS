"""drop project member role and track assigned tester

Revision ID: b7c1d9e4f2a3
Revises: 249e8a5f64b3
Create Date: 2026-11-13 10:45:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c1d9e4f2a3'
down_revision: Union[str, None] = '249e8a5f64b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('assigned_tester_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        None,
        'projects',
        'users',
        ['assigned_tester_id'],
        ['id'],
        ondelete='SET NULL',
    )
    # Preserve the tester assignment before the member role is removed.
    op.execute(
        """
        UPDATE projects AS p
        SET assigned_tester_id = pm.user_id
        FROM project_members AS pm
        WHERE pm.project_id = p.id
          AND pm.role_in_project = 'TESTER'
        """
    )
    op.drop_column('project_members', 'role_in_project')


def downgrade() -> None:
    op.add_column(
        'project_members',
        sa.Column(
            'role_in_project',
            sa.Enum(
                'DEVELOPER',
                'PRODUCER',
                'TESTER',
                name='project_member_role',
                native_enum=False,
                length=20,
            ),
            nullable=True,
        ),
    )
    op.execute(
        """
        UPDATE project_members AS pm
        SET role_in_project = 'TESTER'
        FROM projects AS p
        WHERE p.id = pm.project_id
          AND p.assigned_tester_id = pm.user_id
        """
    )
    op.drop_constraint(
        'projects_assigned_tester_id_fkey',
        'projects',
        type_='foreignkey',
    )
    op.drop_column('projects', 'assigned_tester_id')
