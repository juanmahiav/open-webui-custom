"""Peewee migrations -- 019_add_scheduled_actions.py.

This migration adds the scheduled_actions table for user-friendly automation.

Some examples (model - class or model name)::

    > Model = migrator.orm['table_name']            # Return model in current state by name
    > Model = migrator.ModelClass                   # Return model in current state by name

    > migrator.sql(sql)                             # Run custom SQL
    > migrator.run(func, *args, **kwargs)           # Run python function with the given args
    > migrator.create_model(Model)                  # Create a model (could be used as decorator)
    > migrator.remove_model(model, cascade=True)    # Remove a model
    > migrator.add_fields(model, **fields)          # Add fields to a model
    > migrator.change_fields(model, **fields)       # Change fields
    > migrator.remove_fields(model, *field_names, cascade=True)
    > migrator.rename_field(model, old_field_name, new_field_name)
    > migrator.rename_table(model, new_table_name)
    > migrator.add_index(model, *col_names, unique=False)
    > migrator.add_not_null(model, *field_names)
    > migrator.add_default(model, field_name, default)
    > migrator.add_constraint(model, name, sql)
    > migrator.drop_index(model, *col_names)
    > migrator.drop_not_null(model, *field_names)
    > migrator.drop_constraints(model, *constraints)

"""

from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator


with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""

    @migrator.create_model
    class ScheduledAction(pw.Model):
        id = pw.TextField(unique=True)
        user_id = pw.TextField()
        
        name = pw.TextField()
        description = pw.TextField(null=True)
        
        action_type = pw.TextField()  # 'web_search', 'chat_completion', 'notification'
        action_config = pw.TextField()  # JSON string with action-specific config
        
        schedule_type = pw.TextField()  # 'cron', 'interval', 'once'
        schedule_config = pw.TextField()  # JSON string with schedule config
        
        enabled = pw.BooleanField(default=True)
        last_run_at = pw.BigIntegerField(null=True)
        next_run_at = pw.BigIntegerField(null=True)
        
        created_at = pw.BigIntegerField(null=False)
        updated_at = pw.BigIntegerField(null=False)

        class Meta:
            table_name = "scheduled_action"


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    migrator.remove_model("scheduled_action")
