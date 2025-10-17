"""
Scheduler service for executing scheduled actions.

Uses APScheduler to run scheduled tasks based on user-defined schedules.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from croniter import croniter

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.scheduled_actions import (
    ScheduledActions,
    ScheduledActionModel,
)
from open_webui.services.action_executors import get_executor

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


class SchedulerService:
    """Service for managing and executing scheduled actions."""
    
    def __init__(self, app_state):
        """Initialize the scheduler service."""
        self.app_state = app_state
        self.scheduler = AsyncIOScheduler()
        self.job_map = {}
        self._running = False
    
    async def start(self):
        """Start the scheduler service."""
        if self._running:
            log.warning("Scheduler service is already running")
            return
        
        log.info("Starting scheduler service...")
        
        await self.reload_jobs()
        
        self.scheduler.start()
        self._running = True
        
        log.info("Scheduler service started successfully")
    
    async def stop(self):
        """Stop the scheduler service."""
        if not self._running:
            return
        
        log.info("Stopping scheduler service...")
        
        self.scheduler.shutdown(wait=True)
        self._running = False
        self.job_map.clear()
        
        log.info("Scheduler service stopped")
    
    async def reload_jobs(self):
        """Reload all scheduled jobs from the database."""
        log.info("Reloading scheduled jobs...")
        
        self.scheduler.remove_all_jobs()
        self.job_map.clear()
        
        try:
            actions = ScheduledActions.get_enabled_scheduled_actions()
            log.info(f"Found {len(actions)} enabled scheduled actions")
            
            for action in actions:
                await self._schedule_action(action)
        except Exception as e:
            log.exception(f"Error reloading jobs: {e}")
    
    async def _schedule_action(self, action: ScheduledActionModel):
        """Schedule a single action."""
        try:
            trigger = self._create_trigger(action)
            if not trigger:
                log.warning(f"Could not create trigger for action {action.id}")
                return
            
            job = self.scheduler.add_job(
                self._execute_action_wrapper,
                trigger=trigger,
                args=[action.id],
                id=f"action_{action.id}",
                name=action.name,
                replace_existing=True,
                misfire_grace_time=60,
            )
            
            self.job_map[action.id] = job.id
            
            if hasattr(job, 'next_run_time') and job.next_run_time:
                next_run_timestamp = int(job.next_run_time.timestamp())
                ScheduledActions.update_scheduled_action_run_times(
                    action.id,
                    last_run_at=action.last_run_at or 0,
                    next_run_at=next_run_timestamp
                )
                log.info(
                    f"Scheduled action '{action.name}' (ID: {action.id}) "
                    f"- Next run: {job.next_run_time}"
                )
            else:
                log.info(
                    f"Scheduled action '{action.name}' (ID: {action.id}) - scheduled successfully"
                )
        except Exception as e:
            log.exception(f"Error scheduling action {action.id}: {e}")
    
    def _create_trigger(self, action: ScheduledActionModel):
        """Create an APScheduler trigger from schedule config."""
        schedule_type = action.schedule_type
        config = action.schedule_config
        
        try:
            if schedule_type == "cron":

                cron_expr = config.get("expression", "0 9 * * *")
                
                if not croniter.is_valid(cron_expr):
                    log.error(f"Invalid cron expression: {cron_expr}")
                    return None
                
                parts = cron_expr.split()
                if len(parts) == 5:
                    minute, hour, day, month, day_of_week = parts
                    return CronTrigger(
                        minute=minute,
                        hour=hour,
                        day=day,
                        month=month,
                        day_of_week=day_of_week
                    )
                else:
                    log.error(f"Invalid cron format: {cron_expr}")
                    return None
            
            elif schedule_type == "interval":

                value = config.get("value", 60)
                unit = config.get("unit", "minutes")
                
                kwargs = {unit: value}
                return IntervalTrigger(**kwargs)
            
            elif schedule_type == "once":

                dt_str = config.get("datetime") or config.get("run_at")
                if not dt_str:
                    log.error("No datetime specified for 'once' schedule")
                    return None
                
                try:
                    run_date = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                    return DateTrigger(run_date=run_date)
                except ValueError as e:
                    log.error(f"Invalid datetime format: {dt_str} - {e}")
                    return None
            
            else:
                log.error(f"Unknown schedule type: {schedule_type}")
                return None
        except Exception as e:
            log.exception(f"Error creating trigger: {e}")
            return None
    
    async def _execute_action_wrapper(self, action_id: str):
        """Wrapper function to execute an action and handle errors."""
        try:

            action = ScheduledActions.get_scheduled_action_by_id(action_id)
            if not action:
                log.warning(f"Action {action_id} not found, removing from schedule")
                self.scheduler.remove_job(f"action_{action_id}")
                return
            
            if not action.enabled:
                log.info(f"Action {action_id} is disabled, skipping execution")
                return
            
            await self.execute_action(action)
            
            current_time = int(datetime.now().timestamp())
            job = self.scheduler.get_job(f"action_{action_id}")
            next_run_at = None
            if job and hasattr(job, 'next_run_time') and job.next_run_time:
                next_run_at = int(job.next_run_time.timestamp())
            
            ScheduledActions.update_scheduled_action_run_times(
                action_id,
                last_run_at=current_time,
                next_run_at=next_run_at
            )
            
            if action.schedule_type == "once":
                from open_webui.models.scheduled_actions import ScheduledActionUpdateForm
                ScheduledActions.update_scheduled_action_by_id(
                    action_id,
                    ScheduledActionUpdateForm(enabled=False)
                )
                log.info(f"One-time action {action_id} completed and disabled")
        except Exception as e:
            log.exception(f"Error in action wrapper for {action_id}: {e}")
    
    async def execute_action(self, action: ScheduledActionModel) -> dict:
        """Execute a scheduled action."""
        log.info(
            f"Executing scheduled action: {action.name} "
            f"(type: {action.action_type}, user: {action.user_id})"
        )
        
        try:

            executor = get_executor(action.action_type, self.app_state)
            if not executor:
                error_msg = f"No executor found for action type: {action.action_type}"
                log.error(error_msg)
                return {"status": "error", "message": error_msg}
            
            result = await executor.execute(action.user_id, action.action_config)
            
            log.info(f"Action {action.id} execution result: {result.get('status')}")
            
            if result.get("chat_id"):
                chat_id = result.get("chat_id")

                updated_config = {**action.action_config, "chat_id": chat_id}
                
                from open_webui.models.scheduled_actions import ScheduledActionUpdateForm
                ScheduledActions.update_scheduled_action_by_id(
                    action.id,
                    ScheduledActionUpdateForm(action_config=updated_config)
                )
                log.info(f"Persisted chat_id {chat_id} to action {action.id}")
            
            if action.action_config.get("notify", False):
                await self._send_completion_notification(action, result)
            
            return result
        except Exception as e:
            log.exception(f"Error executing action {action.id}: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _send_completion_notification(
        self, action: ScheduledActionModel, result: dict
    ):
        """Send a notification when an action completes."""
        try:
            from open_webui.services.action_executors import NotificationExecutor
            
            status = result.get("status", "unknown")
            executor = NotificationExecutor(self.app_state)
            
            notification_config = {
                "title": f"Scheduled Action Complete: {action.name}",
                "message": f"Status: {status}",
                "type": "success" if status == "success" else "warning"
            }
            
            await executor.execute(action.user_id, notification_config)
        except Exception as e:
            log.exception(f"Error sending completion notification: {e}")
    
    def get_job_status(self, action_id: str) -> Optional[dict]:
        """Get the status of a scheduled job."""
        job_id = self.job_map.get(action_id)
        if not job_id:
            return None
        
        job = self.scheduler.get_job(job_id)
        if not job:
            return None
        
        next_run = None
        if hasattr(job, 'next_run_time') and job.next_run_time:
            next_run = job.next_run_time.isoformat()
        
        return {
            "id": job.id,
            "name": job.name,
            "next_run_time": next_run,
            "trigger": str(job.trigger),
        }


scheduler_service: Optional[SchedulerService] = None


async def get_scheduler_service(app_state) -> SchedulerService:
    """Get or create the scheduler service instance."""
    global scheduler_service
    if scheduler_service is None:
        scheduler_service = SchedulerService(app_state)
        await scheduler_service.start()
    return scheduler_service
