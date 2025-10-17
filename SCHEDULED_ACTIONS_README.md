# Scheduled Actions Feature - Phase 1 Implementation

## 🎉 Overview

This document describes the implementation of **Phase 1: Basic Scheduled Actions** for Open WebUI. This feature allows users to create automated, scheduled tasks without requiring technical knowledge or writing code.

## ✅ What's Been Implemented

### Backend Components

#### 1. Database Layer
**File:** `backend/open_webui/internal/migrations/019_add_scheduled_actions.py`
- Migration script to create the `scheduled_action` table
- Fields: id, user_id, name, description, action_type, action_config, schedule_type, schedule_config, enabled, last_run_at, next_run_at, created_at, updated_at

**File:** `backend/open_webui/models/scheduled_actions.py`
- `ScheduledAction` database model
- `ScheduledActionModel` Pydantic model for validation
- Complete CRUD operations via `ScheduledActionsTable` class
- JSON serialization/deserialization for action_config and schedule_config

#### 2. API Layer
**File:** `backend/open_webui/routers/scheduled_actions.py`
- RESTful API endpoints:
  - `GET /api/v1/scheduled-actions/` - Get user's scheduled actions
  - `GET /api/v1/scheduled-actions/all` - Get all actions (admin only)
  - `GET /api/v1/scheduled-actions/{id}` - Get specific action
  - `POST /api/v1/scheduled-actions/create` - Create new action
  - `POST /api/v1/scheduled-actions/{id}/update` - Update action
  - `POST /api/v1/scheduled-actions/{id}/toggle` - Enable/disable action
  - `DELETE /api/v1/scheduled-actions/{id}` - Delete action
  - `POST /api/v1/scheduled-actions/{id}/test` - Test run immediately

#### 3. Scheduler Service
**File:** `backend/open_webui/services/scheduler.py`
- Uses APScheduler for reliable job scheduling
- Supports three schedule types:
  - **Cron**: Unix cron expressions (e.g., `0 9 * * *` for 9 AM daily)
  - **Interval**: Recurring intervals (e.g., every 60 minutes)
  - **Once**: One-time execution at specific datetime
- Automatic job reloading when actions are modified
- Graceful error handling and logging
- Integration with main.py lifespan for startup/shutdown

#### 4. Action Executors
**File:** `backend/open_webui/services/action_executors.py`
- **WebSearchExecutor**: Perform web searches on schedule
  - Supports multiple search engines
  - Optional: Save results to user memory
  - Optional: Send notification on completion
- **ChatCompletionExecutor**: Run automated LLM queries
  - Execute prompts with any model
  - Optional: Save responses to memory
- **NotificationExecutor**: Send notifications to users
  - Different notification types (info, success, warning, error)

### Frontend Components

#### API Client
**File:** `src/lib/apis/scheduled-actions/index.ts`
- Complete TypeScript API client
- Functions for all CRUD operations
- Error handling and type safety

### Infrastructure

#### Dependencies
**File:** `backend/requirements.txt`
- Added `croniter==3.0.3` for cron expression validation
- APScheduler already present

#### Integration
**File:** `backend/open_webui/main.py`
- Router registration for scheduled_actions
- Scheduler service initialization in lifespan
- Proper cleanup on shutdown

## 📋 Data Models

### Scheduled Action

```json
{
  "id": "uuid",
  "user_id": "user_id",
  "name": "Daily AI News Search",
  "description": "Search for latest AI and LLM news every day at 9 AM",
  "action_type": "web_search",
  "action_config": {
    "query": "latest AI and LLM news",
    "engine": "searxng",
    "max_results": 10,
    "save_to_memory": true,
    "notify": true
  },
  "schedule_type": "cron",
  "schedule_config": {
    "expression": "0 9 * * *"
  },
  "enabled": true,
  "last_run_at": 1697098800,
  "next_run_at": 1697185200,
  "created_at": 1697098800,
  "updated_at": 1697098800
}
```

### Supported Action Types

#### 1. Web Search (`web_search`)
```json
{
  "action_type": "web_search",
  "action_config": {
    "query": "search query",
    "engine": "ollama_cloud|searxng|google|brave|duckduckgo|tavily|...",
    "max_results": 10,
    "save_to_memory": true,
    "notify": true
  }
}
```

#### 2. Chat Completion (`chat_completion`)
```json
{
  "action_type": "chat_completion",
  "action_config": {
    "model": "model_id",
    "prompt": "Your automated prompt",
    "system_prompt": "Optional system prompt",
    "save_to_memory": true,
    "notify": true
  }
}
```

#### 3. Notification (`notification`)
```json
{
  "action_type": "notification",
  "action_config": {
    "title": "Notification title",
    "message": "Your message",
    "type": "info|success|warning|error"
  }
}
```

### Schedule Types

#### 1. Cron Schedule
```json
{
  "schedule_type": "cron",
  "schedule_config": {
    "expression": "0 9 * * *"  // 9 AM UTC every day
  }
}
```

Common cron expressions:
- `0 9 * * *` - Every day at 9:00 AM
- `0 */6 * * *` - Every 6 hours
- `0 9 * * 1` - Every Monday at 9:00 AM
- `0 0 1 * *` - First day of every month at midnight

#### 2. Interval Schedule
```json
{
  "schedule_type": "interval",
  "schedule_config": {
    "value": 60,
    "unit": "minutes"  // seconds|minutes|hours|days|weeks
  }
}
```

#### 3. One-Time Schedule
```json
{
  "schedule_type": "once",
  "schedule_config": {
    "datetime": "2025-10-13T09:00:00"
  }
}
```

## 🚀 How to Use (API Examples)

### Creating Your Daily AI News Search

```bash
curl -X POST "http://localhost:8080/api/v1/scheduled-actions/create" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily AI News",
    "description": "Search for latest AI and LLM news every morning",
    "action_type": "web_search",
    "action_config": {
      "query": "latest AI and LLM news",
      "engine": "searxng",
      "max_results": 10,
      "save_to_memory": true,
      "notify": true
    },
    "schedule_type": "cron",
    "schedule_config": {
      "expression": "0 9 * * *"
    },
    "enabled": true
  }'
```

### List Your Scheduled Actions

```bash
curl -X GET "http://localhost:8080/api/v1/scheduled-actions/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test an Action Immediately

```bash
curl -X POST "http://localhost:8080/api/v1/scheduled-actions/{action_id}/test" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Toggle Enable/Disable

```bash
curl -X POST "http://localhost:8080/api/v1/scheduled-actions/{action_id}/toggle" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

## 🔄 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface                          │
│                  (To be implemented)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              API Layer (FastAPI Router)                     │
│         /api/v1/scheduled-actions/*                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│           Database Layer (SQLAlchemy/Peewee)                │
│              scheduled_action table                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│         Scheduler Service (APScheduler)                     │
│   - Monitors database for enabled actions                  │
│   - Creates cron/interval/one-time jobs                    │
│   - Executes actions at scheduled times                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│           Action Executors                                  │
│   - WebSearchExecutor                                       │
│   - ChatCompletionExecutor                                  │
│   - NotificationExecutor                                    │
└─────────────────────────────────────────────────────────────┘
```

## 📝 Next Steps (Remaining Tasks)

### Frontend UI Components
Create user-friendly Svelte components:
1. **ScheduledActions.svelte** - Main management page
2. **ScheduledActionForm.svelte** - Create/edit form
3. **ActionTypeSelector.svelte** - Action type picker
4. **ScheduleTypeSelector.svelte** - Schedule configuration UI

### Settings Integration
1. Add "Automations" tab to admin settings
2. Update navigation routes
3. Add icons and styling

### Testing & Documentation
1. Test scheduled action execution
2. Verify cron parsing
3. Test memory integration
4. Write user documentation
5. Create example use cases

## 🎯 Example Use Cases

### 1. Daily News Digest
- **Action**: Web Search
- **Query**: "AI machine learning news"
- **Schedule**: Every day at 9 AM
- **Config**: Save to memory, send notification

### 2. Weekly Summary
- **Action**: Chat Completion
- **Prompt**: "Summarize the key AI developments from my memory this week"
- **Schedule**: Every Monday at 10 AM
- **Config**: Save response to memory

### 3. Hourly Status Check
- **Action**: Web Search
- **Query**: "site:github.com open-webui issues"
- **Schedule**: Every hour
- **Config**: Notify on new results

### 4. Reminder Notification
- **Action**: Notification
- **Message**: "Don't forget your daily standup!"
- **Schedule**: Every weekday at 9:45 AM

## ⚙️ Configuration

### Environment Variables (Optional)
Currently uses existing Open WebUI configuration. Future enhancements could add:
- `ENABLE_SCHEDULED_ACTIONS` - Enable/disable feature
- `MAX_SCHEDULED_ACTIONS_PER_USER` - Rate limiting
- `SCHEDULER_TIMEZONE` - Default timezone for cron jobs

## 🐛 Error Handling

The system includes comprehensive error handling:
- Invalid cron expressions are rejected
- Failed action executions are logged
- Scheduler continues running if individual actions fail
- Database transactions are properly managed
- API returns meaningful error messages

## 🔒 Security

- User ownership validation on all operations
- Admin-only access to view all actions
- API authentication required
- No code execution (restricted to predefined action types)
- Input validation and sanitization

## 📊 Monitoring

Logs include:
- Action execution start/completion
- Scheduler service lifecycle
- Individual job scheduling
- Error conditions with stack traces

Check logs for patterns like:
```
INFO: Executing scheduled action: Daily AI News (type: web_search, user: user_id)
INFO: Action action_id execution result: success
INFO: Scheduled action 'Daily AI News' (ID: action_id) - Next run: 2025-10-13 09:00:00
```

## 🎨 Future Enhancements (Phase 2 & 3)

### Phase 2: Advanced Features
- **Workflow Builder**: Chain multiple actions
- **Conditional Logic**: If/then rules
- **Variables**: Pass data between actions
- **Templates**: Pre-built automation templates
- **Action History**: View execution logs

### Phase 3: AI-Assisted Creation
- Natural language schedule parsing
- Chat-based automation creation
- Smart recommendations
- Auto-optimization of schedules

## 📚 Resources

- APScheduler Documentation: https://apscheduler.readthedocs.io/
- Cron Expression Guide: https://crontab.guru/
- Open WebUI Documentation: https://docs.openwebui.com/

## 🤝 Contributing

To extend this feature:
1. Add new action executors in `action_executors.py`
2. Register them in `EXECUTOR_REGISTRY`
3. Update API validation for new action types
4. Create corresponding UI components

## 📄 License

This feature follows the Open WebUI project license.

---

**Status**: Backend implementation complete ✅  
**Next**: Frontend UI implementation  
**Timeline**: Phase 1 core functionality ready for testing
