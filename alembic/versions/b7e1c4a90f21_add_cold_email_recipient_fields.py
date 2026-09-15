"""add recipient_email, subject, role_specialization to cold_email_drafts

Revision ID: b7e1c4a90f21
Revises: 143d8fa3e362
Create Date: 2026-09-15

"""
from alembic import op
import sqlalchemy as sa

revision = 'b7e1c4a90f21'
down_revision = '143d8fa3e362'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('cold_email_drafts', sa.Column('recipient_email', sa.String(length=320), nullable=True))
    op.add_column('cold_email_drafts', sa.Column('subject', sa.Text(), nullable=True))
    op.add_column('cold_email_drafts', sa.Column('role_specialization', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_cold_email_drafts_recipient_email'), 'cold_email_drafts', ['recipient_email'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_cold_email_drafts_recipient_email'), table_name='cold_email_drafts')
    op.drop_column('cold_email_drafts', 'role_specialization')
    op.drop_column('cold_email_drafts', 'subject')
    op.drop_column('cold_email_drafts', 'recipient_email')
