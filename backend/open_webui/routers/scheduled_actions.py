from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
import logging
from typing import Optional

from open_webui.models.scheduled_actions import (
    ScheduledActions,
    ScheduledActionModel,
    ScheduledActionForm,
    ScheduledActionUpdateForm,
)
from open_webui.utils.auth import get_verified_user, get_admin_user
from open_webui.env import SRC_LOG_LEVELS


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


@router.get("/", response_model=list[ScheduledActionModel])
async def get_scheduled_actions(user=Depends(get_verified_user)):
    """Get all scheduled actions for the current user."""
    return ScheduledActions.get_scheduled_actions_by_user_id(user.id)


@router.get("/all", response_model=list[ScheduledActionModel])
async def get_all_scheduled_actions(user=Depends(get_admin_user)):
    """Get all scheduled actions across all users (admin only)."""
    return ScheduledActions.get_scheduled_actions()


@router.get("/{action_id}", response_model=Optional[ScheduledActionModel])
async def get_scheduled_action_by_id(action_id: str, user=Depends(get_verified_user)):
    """Get a specific scheduled action by ID."""
    action = ScheduledActions.get_scheduled_action_by_id(action_id)
    
    if not action:
        raise HTTPException(status_code=404, detail="Scheduled action not found")
    
    if action.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    return action


@router.post("/create", response_model=Optional[ScheduledActionModel])
async def create_scheduled_action(
    request: Request,
    form_data: ScheduledActionForm,
    user=Depends(get_verified_user),
):
    """Create a new scheduled action."""
    try:

        valid_action_types = ["web_search", "chat_completion", "notification"]
        if form_data.action_type not in valid_action_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action_type. Must be one of: {', '.join(valid_action_types)}"
            )
        
        valid_schedule_types = ["cron", "interval", "once"]
        if form_data.schedule_type not in valid_schedule_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid schedule_type. Must be one of: {', '.join(valid_schedule_types)}"
            )
        
        action = ScheduledActions.insert_new_scheduled_action(user.id, form_data)
        
        if hasattr(request.app.state, "scheduler_service"):
            await request.app.state.scheduler_service.reload_jobs()
        
        return action
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error creating scheduled action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{action_id}/update", response_model=Optional[ScheduledActionModel])
async def update_scheduled_action(
    action_id: str,
    request: Request,
    form_data: ScheduledActionUpdateForm,
    user=Depends(get_verified_user),
):
    """Update an existing scheduled action."""
    try:

        action = ScheduledActions.get_scheduled_action_by_id(action_id)
        if not action:
            raise HTTPException(status_code=404, detail="Scheduled action not found")
        
        if action.user_id != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        updated_action = ScheduledActions.update_scheduled_action_by_id(
            action_id, form_data
        )
        
        if hasattr(request.app.state, "scheduler_service"):
            await request.app.state.scheduler_service.reload_jobs()
        
        return updated_action
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating scheduled action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ToggleForm(BaseModel):
    enabled: bool


@router.post("/{action_id}/toggle", response_model=Optional[ScheduledActionModel])
async def toggle_scheduled_action(
    action_id: str,
    request: Request,
    form_data: ToggleForm,
    user=Depends(get_verified_user),
):
    """Enable or disable a scheduled action."""
    try:

        action = ScheduledActions.get_scheduled_action_by_id(action_id)
        if not action:
            raise HTTPException(status_code=404, detail="Scheduled action not found")
        
        if action.user_id != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        updated_action = ScheduledActions.update_scheduled_action_by_id(
            action_id, ScheduledActionUpdateForm(enabled=form_data.enabled)
        )
        
        if hasattr(request.app.state, "scheduler_service"):
            await request.app.state.scheduler_service.reload_jobs()
        
        return updated_action
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error toggling scheduled action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{action_id}", response_model=bool)
async def delete_scheduled_action(
    action_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    """Delete a scheduled action."""
    try:

        action = ScheduledActions.get_scheduled_action_by_id(action_id)
        if not action:
            raise HTTPException(status_code=404, detail="Scheduled action not found")
        
        if action.user_id != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        result = ScheduledActions.delete_scheduled_action_by_id(action_id)
        
        if hasattr(request.app.state, "scheduler_service"):
            await request.app.state.scheduler_service.reload_jobs()
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error deleting scheduled action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{action_id}/test", response_model=dict)
async def test_scheduled_action(
    action_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    """Test execute a scheduled action immediately."""
    try:

        action = ScheduledActions.get_scheduled_action_by_id(action_id)
        if not action:
            raise HTTPException(status_code=404, detail="Scheduled action not found")
        
        if action.user_id != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        if hasattr(request.app.state, "scheduler_service"):
            result = await request.app.state.scheduler_service.execute_action(action)
            return {"status": "success", "result": result}
        else:
            raise HTTPException(
                status_code=503,
                detail="Scheduler service not available"
            )
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error testing scheduled action: {e}")
        raise HTTPException(status_code=500, detail=str(e))
