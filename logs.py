# logs.py
"""
Centralized logging service for the AI Mortgage Advisor.
Architecture: Knowledge Base Services Layer → Logs
"""

import os
import json
from datetime import datetime
from typing import Any, Dict, Optional

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)


class LogService:
    """Centralized logging for all system components."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.log_file = os.path.join(LOG_DIR, "system.jsonl")
        self._initialized = True
    
    def _write(self, entry: Dict[str, Any]):
        """Write a log entry to file."""
        entry["timestamp"] = datetime.now().isoformat()
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"[LogService] Failed to write log: {e}")
    
    def log_user_message(self, session_id: str, message: str):
        """Log incoming user message."""
        self._write({
            "type": "user_message",
            "session_id": session_id,
            "message": message[:500]  # Truncate long messages
        })
    
    def log_agent_response(self, session_id: str, agent: str, response: str):
        """Log agent response."""
        self._write({
            "type": "agent_response",
            "session_id": session_id,
            "agent": agent,
            "response": response[:1000]
        })
    
    def log_tool_call(self, agent: str, tool: str, input: str, output: str):
        """Log tool invocation."""
        self._write({
            "type": "tool_call",
            "agent": agent,
            "tool": tool,
            "input": input[:300],
            "output": output[:500]
        })
    
    def log_plan(self, session_id: str, plan: Dict[str, Any]):
        """Log orchestrator plan."""
        self._write({
            "type": "plan",
            "session_id": session_id,
            "plan": plan
        })
    
    def log_feedback(self, session_id: str, feedback_report: Dict[str, Any]):
        """Log feedback/introspection report."""
        self._write({
            "type": "feedback",
            "session_id": session_id,
            "report": feedback_report
        })
    
    def log_error(self, context: str, error: str):
        """Log errors."""
        self._write({
            "type": "error",
            "context": context,
            "error": str(error)
        })
    
    def log_event(self, event_type: str, details: Dict[str, Any]):
        """Log generic events."""
        self._write({
            "type": event_type,
            **details
        })
    
    def get_recent_logs(self, n: int = 50, log_type: Optional[str] = None) -> list:
        """Retrieve recent log entries."""
        entries = []
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if log_type is None or entry.get("type") == log_type:
                            entries.append(entry)
                    except:
                        pass
        except FileNotFoundError:
            return []
        
        return entries[-n:]
    
    def get_session_logs(self, session_id: str) -> list:
        """Get all logs for a specific session."""
        entries = []
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get("session_id") == session_id:
                            entries.append(entry)
                    except:
                        pass
        except FileNotFoundError:
            return []
        
        return entries


# Singleton instance
logger = LogService()