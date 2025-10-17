import time
import uuid
import json
from typing import Optional

from open_webui.internal.db import Base, get_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text


class ScheduledAction(Base):
    __tablename__ = "scheduled_action"

    id = Column(String, primary_key=True)
    user_id = Column(String)
    
    name = Column(Text)
    description = Column(Text, nullable=True)
    
    action_type = Column(String)
    action_config = Column(Text)
    
    schedule_type = Column(String)
    schedule_config = Column(Text)
    
    enabled = Column(Boolean, default=True)
    last_run_at = Column(BigInteger, nullable=True)
    next_run_at = Column(BigInteger, nullable=True)
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class ScheduledActionModel(BaseModel):
    id: str
    user_id: str
    
    name: str
    description: Optional[str] = None
    
    action_type: str
    action_config: dict
    
    schedule_type: str
    schedule_config: dict
    
    enabled: bool = True
    last_run_at: Optional[int] = None
    next_run_at: Optional[int] = None
    
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class ScheduledActionForm(BaseModel):
    name: str
    description: Optional[str] = None
    action_type: str
    action_config: dict
    schedule_type: str
    schedule_config: dict
    enabled: bool = True


class ScheduledActionUpdateForm(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    action_config: Optional[dict] = None
    schedule_type: Optional[str] = None
    schedule_config: Optional[dict] = None
    enabled: Optional[bool] = None


class ScheduledActionsTable:
    def insert_new_scheduled_action(
        self, user_id: str, form_data: ScheduledActionForm
    ) -> Optional[ScheduledActionModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            timestamp = int(time.time())
            
            scheduled_action = ScheduledAction(
                **{
                    "id": id,
                    "user_id": user_id,
                    "name": form_data.name,
                    "description": form_data.description,
                    "action_type": form_data.action_type,
                    "action_config": json.dumps(form_data.action_config),
                    "schedule_type": form_data.schedule_type,
                    "schedule_config": json.dumps(form_data.schedule_config),
                    "enabled": form_data.enabled,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            )
            
            db.add(scheduled_action)
            db.commit()
            db.refresh(scheduled_action)
            
            return ScheduledActionModel(
                **{
                    **scheduled_action.__dict__,
                    "action_config": json.loads(scheduled_action.action_config),
                    "schedule_config": json.loads(scheduled_action.schedule_config),
                }
            )

    def get_scheduled_actions(self) -> list[ScheduledActionModel]:
        with get_db() as db:
            actions = db.query(ScheduledAction).all()
            return [
                ScheduledActionModel(
                    **{
                        **action.__dict__,
                        "action_config": json.loads(action.action_config),
                        "schedule_config": json.loads(action.schedule_config),
                    }
                )
                for action in actions
            ]

    def get_scheduled_actions_by_user_id(
        self, user_id: str
    ) -> list[ScheduledActionModel]:
        with get_db() as db:
            actions = db.query(ScheduledAction).filter_by(user_id=user_id).all()
            return [
                ScheduledActionModel(
                    **{
                        **action.__dict__,
                        "action_config": json.loads(action.action_config),
                        "schedule_config": json.loads(action.schedule_config),
                    }
                )
                for action in actions
            ]

    def get_enabled_scheduled_actions(self) -> list[ScheduledActionModel]:
        """Get all enabled scheduled actions across all users."""
        with get_db() as db:
            actions = db.query(ScheduledAction).filter_by(enabled=True).all()
            return [
                ScheduledActionModel(
                    **{
                        **action.__dict__,
                        "action_config": json.loads(action.action_config),
                        "schedule_config": json.loads(action.schedule_config),
                    }
                )
                for action in actions
            ]

    def get_scheduled_action_by_id(self, id: str) -> Optional[ScheduledActionModel]:
        try:
            with get_db() as db:
                action = db.query(ScheduledAction).filter_by(id=id).first()
                if action:
                    return ScheduledActionModel(
                        **{
                            **action.__dict__,
                            "action_config": json.loads(action.action_config),
                            "schedule_config": json.loads(action.schedule_config),
                        }
                    )
                return None
        except Exception:
            return None

    def update_scheduled_action_by_id(
        self, id: str, form_data: ScheduledActionUpdateForm
    ) -> Optional[ScheduledActionModel]:
        with get_db() as db:
            action = db.query(ScheduledAction).filter_by(id=id).first()
            if not action:
                return None
            
            update_data = form_data.model_dump(exclude_unset=True)
            
            if "action_config" in update_data:
                update_data["action_config"] = json.dumps(update_data["action_config"])
            if "schedule_config" in update_data:
                update_data["schedule_config"] = json.dumps(update_data["schedule_config"])
            
            update_data["updated_at"] = int(time.time())
            
            for key, value in update_data.items():
                setattr(action, key, value)
            
            db.commit()
            db.refresh(action)
            
            return ScheduledActionModel(
                **{
                    **action.__dict__,
                    "action_config": json.loads(action.action_config),
                    "schedule_config": json.loads(action.schedule_config),
                }
            )

    def update_scheduled_action_run_times(
        self, id: str, last_run_at: int, next_run_at: Optional[int] = None
    ) -> bool:
        """Update the last run and next run times for a scheduled action."""
        with get_db() as db:
            action = db.query(ScheduledAction).filter_by(id=id).first()
            if not action:
                return False
            
            action.last_run_at = last_run_at
            if next_run_at is not None:
                action.next_run_at = next_run_at
            action.updated_at = int(time.time())
            
            db.commit()
            return True

    def delete_scheduled_action_by_id(self, id: str) -> bool:
        with get_db() as db:
            action = db.query(ScheduledAction).filter_by(id=id).first()
            if not action:
                return False
            
            db.delete(action)
            db.commit()
            return True

    def delete_scheduled_actions_by_user_id(self, user_id: str) -> bool:
        with get_db() as db:
            db.query(ScheduledAction).filter_by(user_id=user_id).delete()
            db.commit()
            return True


ScheduledActions = ScheduledActionsTable()
