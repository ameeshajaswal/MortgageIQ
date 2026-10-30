# mortgage_crew.py

import json
from typing import Any, Dict

from crewai import Crew

from agents import (
    main_orchestrator,
    eligibility_agent,
    product_search_agent,
    paperwork_agent,
    feedback_agent,
    customer_intel_agent,
)
from tasks import (
    plan_task,
    eligibility_task,
    product_task,
    paperwork_task,
    customer_intel_task,
    feedback_task,
    final_answer_task,
)


def _crew_result_to_str(result: Any) -> str:
    """Helper to safely convert a Crew result to string."""
    if hasattr(result, "raw"):
        return str(result.raw)
    return str(result)


def _parse_json_or_default(raw: str, default: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return json.loads(raw)
    except Exception:
        return default


def _log_introspection(
    plan: Dict[str, Any],
    agent_outputs: Dict[str, str],
    feedback_report: Dict[str, Any],
    previous_context: Dict[str, Any],
) -> None:
    """Append a JSON line with introspection metrics to a local log file."""
    entry = {
        "plan": plan,
        "agent_outputs": agent_outputs,
        "feedback_report": feedback_report,
        "previous_context": previous_context,
    }
    try:
        with open("introspection_logs.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"[mortgage_crew] Failed to write introspection log: {e}")


class MortgageAdvisorSystem:
    """
    Single access point for the AI Mortgage Broker system.

    - Only the main orchestrator talks to the user.
    - Feedback agent is introspective and internal only.
    - System keeps track of the previous turn to learn from user feedback.
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.previous_context: Dict[str, Any] = {
            "user_message": None,
            "answer": None,
            "feedback_report": None,
        }

    # -------- Planning --------

    def _make_plan(self, user_message: str) -> Dict[str, Any]:
        plan_crew = Crew(
            agents=[main_orchestrator],
            tasks=[plan_task],
            verbose=self.verbose,
        )
        raw_plan = _crew_result_to_str(
            plan_crew.kickoff(inputs={"user_message": user_message})
        )
        default_plan = {
            "steps": [
                {"agent": "eligibility", "purpose": "check eligibility"},
                {"agent": "products", "purpose": "suggest products"},
                {"agent": "paperwork", "purpose": "explain documents"},
                {"agent": "feedback", "purpose": "evaluate quality"},
            ]
        }
        plan = _parse_json_or_default(raw_plan, default_plan)
        return plan

    # -------- Worker agents --------

    def _run_workers(self, user_message: str, plan: Dict[str, Any]) -> Dict[str, str]:
        """Run specialist agents according to the plan; return their raw outputs."""
        agent_outputs: Dict[str, str] = {}
        steps = plan.get("steps", [])

        for step in steps:
            agent_name = step.get("agent")

            if agent_name == "eligibility":
                crew = Crew(
                    agents=[eligibility_agent],
                    tasks=[eligibility_task],
                    verbose=self.verbose,
                )
                result = crew.kickoff(inputs={"user_message": user_message, "plan": plan})
                agent_outputs["eligibility"] = _crew_result_to_str(result)

            elif agent_name == "products":
                crew = Crew(
                    agents=[product_search_agent],
                    tasks=[product_task],
                    verbose=self.verbose,
                )
                result = crew.kickoff(inputs={"user_message": user_message, "plan": plan})
                agent_outputs["products"] = _crew_result_to_str(result)

            elif agent_name == "paperwork":
                crew = Crew(
                    agents=[paperwork_agent],
                    tasks=[paperwork_task],
                    verbose=self.verbose,
                )
                result = crew.kickoff(inputs={"user_message": user_message, "plan": plan})
                agent_outputs["paperwork"] = _crew_result_to_str(result)

            elif agent_name == "customer_intel":
                crew = Crew(
                    agents=[customer_intel_agent],
                    tasks=[customer_intel_task],
                    verbose=self.verbose,
                )
                result = crew.kickoff(inputs={"user_message": user_message, "plan": plan})
                agent_outputs["customer_intel"] = _crew_result_to_str(result)

            # 'feedback' is run separately

        return agent_outputs

    # -------- Feedback / introspection --------

    def _run_feedback(
        self,
        user_message: str,
        plan: Dict[str, Any],
        agent_outputs: Dict[str, str],
    ) -> Dict[str, Any]:
        prev = self.previous_context or {}
        previous_user_message = prev.get("user_message")
        previous_answer = prev.get("answer")
        previous_feedback_report = prev.get("feedback_report")

        feedback_crew = Crew(
            agents=[feedback_agent],
            tasks=[feedback_task],
            verbose=self.verbose,
        )
        raw_feedback = _crew_result_to_str(
            feedback_crew.kickoff(
                inputs={
                    "user_message": user_message,
                    "plan": plan,
                    "agent_outputs": agent_outputs,
                    "previous_user_message": previous_user_message,
                    "previous_answer": previous_answer,
                    "previous_feedback_report": json.dumps(previous_feedback_report)
                    if isinstance(previous_feedback_report, dict)
                    else str(previous_feedback_report),
                }
            )
        )
        default_feedback = {
            "overall_quality": "unknown",
            "alignment_with_user": "unknown",
            "risk_flags": [],
            "policy_flags": [],
            "user_feedback_signal": "",
            "notes_for_orchestrator": "",
            "log_entry": "feedback agent did not return valid JSON",
        }
        feedback_report = _parse_json_or_default(raw_feedback, default_feedback)

        _log_introspection(plan, agent_outputs, feedback_report, self.previous_context)
        return feedback_report

    # -------- Final answer --------

    def _run_final_answer(
        self,
        user_message: str,
        plan: Dict[str, Any],
        agent_outputs: Dict[str, str],
        feedback_report: Dict[str, Any],
    ) -> str:
        prev = self.previous_context or {}
        previous_user_message = prev.get("user_message")
        previous_answer = prev.get("answer")

        final_crew = Crew(
            agents=[main_orchestrator],
            tasks=[final_answer_task],
            verbose=self.verbose,
        )
        result = final_crew.kickoff(
            inputs={
                "user_message": user_message,
                "plan": plan,
                "agent_outputs": agent_outputs,
                "feedback_report": feedback_report,
                "previous_user_message": previous_user_message,
                "previous_answer": previous_answer,
            }
        )
        return _crew_result_to_str(result)

    # -------- Public API --------

    def run(self, user_message: str) -> str:
        """
        End-to-end flow for a single user message:
        1) Orchestrator plans which agents to call.
        2) Worker agents run internally.
        3) Feedback agent introspects and generates metrics.
        4) Orchestrator composes the final answer.
        5) Previous context is updated for the next call.
        """
        plan = self._make_plan(user_message)
        agent_outputs = self._run_workers(user_message, plan)
        feedback_report = self._run_feedback(user_message, plan, agent_outputs)
        final_answer = self._run_final_answer(
            user_message, plan, agent_outputs, feedback_report
        )

        self.previous_context = {
            "user_message": user_message,
            "answer": final_answer,
            "feedback_report": feedback_report,
            "plan": plan,
            "agent_outputs": agent_outputs,
        }

        return final_answer


# Convenience function used by Streamlit
def run_mortgage_advisor(user_message: str) -> str:
    system = MortgageAdvisorSystem(verbose=True)
    return system.run(user_message)
