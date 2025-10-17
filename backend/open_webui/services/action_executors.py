"""
Action executors for scheduled actions.

Each executor implements a specific action type that can be scheduled.
"""

import logging
import time
import uuid
from typing import Any, Dict, Optional
from fastapi import Request

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.users import Users

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


class ActionExecutor:
    """Base class for action executors."""
    
    def __init__(self, app_state):
        self.app_state = app_state
    
    async def execute(
        self, user_id: str, action_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the action. Must be implemented by subclasses."""
        raise NotImplementedError


class WebSearchExecutor(ActionExecutor):
    """Execute a web search and return results."""
    
    async def execute(
        self, user_id: str, action_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a web search.
        
        action_config format:
        {
            "query": "search query",
            "engine": "ollama_cloud|searxng|google|brave|serpstack|serper|serply|duckduckgo|tavily|jina",
            "max_results": 10,
            "save_to_memory": true,  # Optional: save results to user memory
            "notify": true  # Optional: send notification when complete
        }
        """
        try:

            from open_webui.retrieval.web.ollama import search_ollama_cloud
            from open_webui.retrieval.web.searxng import search_searxng
            from open_webui.retrieval.web.brave import search_brave
            from open_webui.retrieval.web.google_pse import search_google_pse
            from open_webui.retrieval.web.duckduckgo import search_duckduckgo
            from open_webui.retrieval.web.tavily import search_tavily
            
            query = action_config.get("query", "")
            engine = action_config.get("engine", "ollama_cloud")
            max_results = action_config.get("max_results", 10)
            
            if not query:
                return {"status": "error", "message": "No query provided"}
            
            log.info(f"Executing web search for user {user_id}: {query} (engine: {engine})")
            
            config = self.app_state.config
            
            results = []
            if engine == "ollama_cloud":
                if not config.OLLAMA_CLOUD_WEB_SEARCH_API_KEY:
                    return {"status": "error", "message": "Ollama Cloud API key not configured"}
                results = search_ollama_cloud(
                    "https://ollama.com",
                    config.OLLAMA_CLOUD_WEB_SEARCH_API_KEY,
                    query,
                    max_results,
                    config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                )
            elif engine == "searxng":
                if not config.SEARXNG_QUERY_URL:
                    return {"status": "error", "message": "SearXNG query URL not configured"}
                results = search_searxng(
                    config.SEARXNG_QUERY_URL,
                    query,
                    max_results,
                    config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                )
            elif engine == "brave":
                if not config.BRAVE_SEARCH_API_KEY:
                    return {"status": "error", "message": "Brave Search API key not configured"}
                results = search_brave(
                    config.BRAVE_SEARCH_API_KEY,
                    query,
                    max_results,
                    config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                )
            elif engine == "google_pse":
                if not config.GOOGLE_PSE_API_KEY or not config.GOOGLE_PSE_ENGINE_ID:
                    return {"status": "error", "message": "Google PSE API key or engine ID not configured"}
                results = search_google_pse(
                    config.GOOGLE_PSE_API_KEY,
                    config.GOOGLE_PSE_ENGINE_ID,
                    query,
                    max_results,
                    config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                )
            elif engine == "duckduckgo":
                results = search_duckduckgo(
                    query,
                    max_results,
                    config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                )
            elif engine == "tavily":
                if not config.TAVILY_API_KEY:
                    return {"status": "error", "message": "Tavily API key not configured"}
                results = search_tavily(
                    config.TAVILY_API_KEY,
                    query,
                    max_results,
                    config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                )
            else:
                return {"status": "error", "message": f"Unsupported search engine: {engine}"}
            
            chat_id = None
            if action_config.get("save_to_chat", True):  # Changed from save_to_memory to save_to_chat
                chat_id = await self._save_to_chat(user_id, query, results, action_config)
            
            return {
                "status": "success",
                "query": query,
                "engine": engine,
                "results_count": len(results) if results else 0,
                "results": results,
                "chat_id": chat_id
            }
        except Exception as e:
            log.exception(f"Error executing web search: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _save_to_chat(
        self, user_id: str, query: str, results: list, action_config: Dict[str, Any]
    ) -> Optional[str]:
        """
        Save search results to a chat. Creates a new chat or updates existing one.
        Returns the chat ID.
        """
        try:
            from open_webui.models.chats import Chats, ChatForm
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            message_content = f"🔍 **Search Results for:** {query}\n"
            message_content += f"📅 **Date:** {timestamp}\n"
            message_content += f"🔎 **Engine:** {action_config.get('engine', 'unknown')}\n"
            message_content += f"📊 **Results Found:** {len(results)}\n\n"
            message_content += "---\n\n"
            
            for i, result in enumerate(results, 1):

                if hasattr(result, 'title'):
                    title = result.title or "No title"
                    link = result.link or ""
                    snippet = result.snippet or ""
                else:
                    title = result.get("title", "No title")
                    link = result.get("link", "")
                    snippet = result.get("snippet", "")
                
                message_content += f"### {i}. {title}\n"
                message_content += f"🔗 [{link}]({link})\n\n"
                if snippet:
                    message_content += f"{snippet}\n\n"
                message_content += "---\n\n"
            
            chat_id = action_config.get("chat_id")
            
            if chat_id:

                existing_chat = Chats.get_chat_by_id_and_user_id(chat_id, user_id)
                if existing_chat:

                    chat_data = existing_chat.chat
                    
                    if "history" not in chat_data:
                        chat_data["history"] = {"messages": {}}
                    if "messages" not in chat_data["history"]:
                        chat_data["history"]["messages"] = {}
                    
                    if "messages" not in chat_data:
                        chat_data["messages"] = []
                    
                    if "models" not in chat_data or not chat_data["models"]:
                        chat_data["models"] = ["scheduled-search"]
                    
                    if "tags" not in chat_data:
                        chat_data["tags"] = []
                    if "files" not in chat_data:
                        chat_data["files"] = []
                    
                    user_msg_id = str(uuid.uuid4())
                    assistant_msg_id = str(uuid.uuid4())
                    
                    messages = chat_data["history"]["messages"]
                    last_msg_id = None
                    if messages:

                        for msg_id, msg in messages.items():
                            if not msg.get("childrenIds"):
                                last_msg_id = msg_id
                                break
                    
                    user_message = {
                        "id": user_msg_id,
                        "parentId": last_msg_id,
                        "childrenIds": [assistant_msg_id],
                        "role": "user",
                        "content": f"[Scheduled Search] {query}",
                        "timestamp": int(time.time()),
                        "models": ["scheduled-search"]
                    }
                    
                    assistant_message = {
                        "id": assistant_msg_id,
                        "parentId": user_msg_id,
                        "childrenIds": [],
                        "role": "assistant",
                        "content": message_content,
                        "timestamp": int(time.time()),
                        "model": "scheduled-search",
                        "done": True
                    }
                    
                    chat_data["history"]["messages"][user_msg_id] = user_message
                    chat_data["history"]["messages"][assistant_msg_id] = assistant_message
                    
                    chat_data["history"]["currentId"] = assistant_msg_id
                    
                    chat_data["messages"].append(user_message)
                    chat_data["messages"].append(assistant_message)
                    
                    if last_msg_id and last_msg_id in messages:
                        if "childrenIds" not in messages[last_msg_id]:
                            messages[last_msg_id]["childrenIds"] = []
                        messages[last_msg_id]["childrenIds"].append(user_msg_id)
                    
                    Chats.update_chat_by_id(chat_id, chat_data)
                    log.info(f"Updated existing chat {chat_id} with new search results")
                    return chat_id
            
            chat_title = f"📰 {query}"
            user_msg_id = str(uuid.uuid4())
            assistant_msg_id = str(uuid.uuid4())
            
            user_message = {
                "id": user_msg_id,
                "parentId": None,
                "childrenIds": [assistant_msg_id],
                "role": "user",
                "content": f"[Scheduled Search] {query}",
                "timestamp": int(time.time()),
                "models": ["scheduled-search"]
            }
            
            assistant_message = {
                "id": assistant_msg_id,
                "parentId": user_msg_id,
                "childrenIds": [],
                "role": "assistant",
                "content": message_content,
                "timestamp": int(time.time()),
                "model": "scheduled-search",
                "done": True
            }
            
            chat_data = {
                "id": "",
                "title": chat_title,
                "models": ["scheduled-search"],
                "params": {},
                "history": {
                    "messages": {
                        user_msg_id: user_message,
                        assistant_msg_id: assistant_message
                    },
                    "currentId": assistant_msg_id
                },
                "messages": [user_message, assistant_message],  # Also add as array for frontend
                "tags": [],
                "files": [],
                "timestamp": int(time.time())
            }
            
            chat_form = ChatForm(chat=chat_data, folder_id=None)
            new_chat = Chats.insert_new_chat(user_id, chat_form)
            
            if new_chat:
                log.info(f"Created new chat {new_chat.id} with search results")
                return new_chat.id
            
            return None
        except Exception as e:
            log.exception(f"Error saving to chat: {e}")
            return None


class ChatCompletionExecutor(ActionExecutor):
    """Execute a chat completion and save the response."""
    
    async def execute(
        self, user_id: str, action_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a chat completion.
        
        action_config format:
        {
            "model": "model_id",
            "prompt": "Your prompt here",
            "system_prompt": "Optional system prompt",
            "save_to_memory": true,  # Optional: save response to user memory
            "notify": true  # Optional: send notification when complete
        }
        """
        try:
            from open_webui.utils.chat import generate_chat_completion
            from fastapi import Request
            
            model = action_config.get("model", "")
            prompt = action_config.get("prompt", "")
            system_prompt = action_config.get("system_prompt", "")
            
            if not prompt:
                return {"status": "error", "message": "No prompt provided"}
            
            if not model:
                return {"status": "error", "message": "No model specified"}
            
            log.info(f"Executing chat completion for user {user_id} with model {model}")
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            form_data = {
                "model": model,
                "messages": messages,
                "stream": False
            }
            
            response_content = "Chat completion executed (implementation pending)"
            
            if action_config.get("save_to_memory", False):
                await self._save_to_memory(user_id, prompt, response_content)
            
            return {
                "status": "success",
                "model": model,
                "prompt": prompt,
                "response": response_content
            }
        except Exception as e:
            log.exception(f"Error executing chat completion: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _save_to_memory(
        self, user_id: str, prompt: str, response: str
    ) -> None:
        """Save chat completion to user memory."""
        try:
            from open_webui.models.memories import Memories
            from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT
            
            summary = f"Automated chat:\nQ: {prompt}\nA: {response}"
            
            memory = Memories.insert_new_memory(user_id, summary)
            
            if memory and hasattr(self.app_state, "EMBEDDING_FUNCTION"):
                VECTOR_DB_CLIENT.upsert(
                    collection_name=f"user-memory-{user_id}",
                    items=[{
                        "id": memory.id,
                        "text": memory.content,
                        "vector": self.app_state.EMBEDDING_FUNCTION(
                            memory.content, user=Users.get_user_by_id(user_id)
                        ),
                        "metadata": {"created_at": memory.created_at},
                    }],
                )
            
            log.info(f"Saved chat completion to memory for user {user_id}")
        except Exception as e:
            log.exception(f"Error saving to memory: {e}")


class NotificationExecutor(ActionExecutor):
    """Send a notification to the user."""
    
    async def execute(
        self, user_id: str, action_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send a notification.
        
        action_config format:
        {
            "title": "Notification title",
            "message": "Notification message",
            "type": "info|success|warning|error"
        }
        """
        try:
            title = action_config.get("title", "Scheduled Action")
            message = action_config.get("message", "Your scheduled action has completed")
            notification_type = action_config.get("type", "info")
            
            log.info(f"Sending notification to user {user_id}: {title}")
            
            log.info(f"Notification for {user_id}: [{notification_type}] {title} - {message}")
            
            return {
                "status": "success",
                "title": title,
                "message": message,
                "type": notification_type
            }
        except Exception as e:
            log.exception(f"Error sending notification: {e}")
            return {"status": "error", "message": str(e)}

EXECUTOR_REGISTRY = {
    "web_search": WebSearchExecutor,
    "chat_completion": ChatCompletionExecutor,
    "notification": NotificationExecutor,
}


def get_executor(action_type: str, app_state) -> Optional[ActionExecutor]:
    """Get an executor instance for the given action type."""
    executor_class = EXECUTOR_REGISTRY.get(action_type)
    if executor_class:
        return executor_class(app_state)
    return None
