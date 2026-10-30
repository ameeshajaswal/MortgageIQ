# tasks.py

from crewai import Task
from agents import (
    main_orchestrator,
    eligibility_agent,
    product_search_agent,
    paperwork_agent,
    feedback_agent,
    customer_intel_agent,
)

# ─────────────────────────────────────────────────────────────
# 1. PLANNING TASK  (main orchestrator decides which agents to call)
# ─────────────────────────────────────────────────────────────

plan_task = Task(
    description=(
        "You are the AI Mortgage Broker orchestrator.\n\n"
        "Read the user's current message and decide which specialist agents should "
        "be involved THIS TURN:\n"
        "- 'eligibility' for questions about qualifying, how much they can borrow, "
        "  or affordability.\n"
        "- 'products' for questions about mortgage options, fixed vs variable, terms, "
        "  or comparisons.\n"
        "- 'paperwork' when the user asks about documents or wants to apply / move "
        "  the application forward.\n"
        "- 'customer_intel' if the message gives useful info about preferences, "
        "  risk tolerance, or engagement.\n"
        "- 'feedback' is always run internally at the end for introspection.\n\n"
        "Return ONLY a JSON object with a 'steps' list. Each step has:\n"
        "  - 'agent': one of ['eligibility','products','paperwork','customer_intel',"
        "'feedback']\n"
        "  - 'purpose': a short sentence of why you are calling that agent.\n\n"
        "User message: {user_message}"
    ),
    agent=main_orchestrator,
    expected_output=(
        "A valid JSON object, e.g.\n"
        '{ "steps": ['
        '{"agent":"eligibility","purpose":"check affordability"},'
        '{"agent":"products","purpose":"suggest product options"},'
        '{"agent":"paperwork","purpose":"explain docs"},'
        '{"agent":"feedback","purpose":"evaluate quality"} ] }'
    ),
)

# ─────────────────────────────────────────────────────────────
# 2. WORKER TASKS (specialist agents)
# ─────────────────────────────────────────────────────────────

eligibility_task = Task(
    description=(
        "Act as the eligibility & affordability specialist.\n\n"
        "Using the user's message and any context, estimate how a typical lender "
        "might view their affordability and basic mortgage eligibility. Use your "
        "tools (credit/affordability calculators, internal guidelines) when needed. "
        "Be realistic, not overly optimistic, and do not guarantee approval.\n\n"
        "User message: {user_message}"
    ),
    agent=eligibility_agent,
    expected_output=(
        "A broker-style summary including:\n"
        "- Rough maximum recommended borrowing amount or range (if possible)\n"
        "- Main factors that help or hurt eligibility\n"
        "- Any important warnings or assumptions"
    ),
)

product_task = Task(
    description=(
        "Act as the product & rate search specialist.\n\n"
        "Based on the situation described and any plan context, suggest suitable "
        "mortgage product options. Use your tools to get typical rate ranges and "
        "policy knowledge (do NOT invent precise live quotes). Focus on 2–4 options "
        "and explain them like a 10-year broker.\n\n"
        "User message: {user_message}\n"
        "Plan: {plan}"
    ),
    agent=product_search_agent,
    expected_output=(
        "A short list of 2–4 product options. For each, include:\n"
        "- Type (e.g., 5-year fixed, 3-year variable)\n"
        "- Approximate rate range (described qualitatively, not exact live quotes)\n"
        "- Pros and cons for this user\n"
        "- When it would or would not make sense"
    ),
)

paperwork_task = Task(
    description=(
        "Act as the paperwork & application specialist.\n\n"
        "Use a TWO-STEP approach:\n\n"
        "STEP 1 - Quick Assessment (ALWAYS do this first):\n"
        "  • Call document_loader_tool once with 'all uploaded documents'\n"
        "  • Review the list and identify what's present vs missing\n\n"
        "STEP 2 - Deep Verification (ONLY if user wants to apply/verify details):\n"
        "  • If the user asks to process application or verify details:\n"
        "    - Use document_reader_tool to read specific files\n"
        "    - Extract key info: salary, employer name, account balances, etc.\n"
        "    - Report findings and any issues\n\n"
        "If user just uploaded docs and wants to know status: do STEP 1 only.\n"
        "If user says 'I want to apply' or 'process my application': do BOTH steps.\n\n"
        "User message: {user_message}"
    ),
    agent=paperwork_agent,
    expected_output=(
        "A broker-style explanation that:\n"
        "- Lists what documents are uploaded (from quick assessment)\n"
        "- Identifies missing documents\n"
        "- If verification was done: reports key details found (salary, employer, etc.)\n"
        "- States next steps (what's needed or if ready for underwriting)"
    ),
)

customer_intel_task = Task(
    description=(
        "You are the Customer Intelligence Agent. You NEVER speak directly to the user.\n\n"
        "From the user's current message and the plan context, infer behavior and "
        "engagement patterns and return a structured intelligence report.\n\n"
        "Your JSON report MUST contain:\n"
        "- 'engagement_score': integer 0–100\n"
        "- 'churn_risk': 'low' | 'medium' | 'high'\n"
        "- 'conversion_likelihood': 'low' | 'medium' | 'high'\n"
        "- 'behavioral_signals': list of short strings\n"
        "- 'recommended_actions': list of objects like "
        '{"action": "...", "reason": "..."}\n\n'
        "User message: {user_message}\n"
        "Plan: {plan}"
    ),
    agent=customer_intel_agent,
    expected_output=(
        "A valid JSON object with keys: engagement_score, churn_risk, "
        "conversion_likelihood, behavioral_signals, recommended_actions."
    ),
)

# ─────────────────────────────────────────────────────────────
# 3. FEEDBACK / INTROSPECTION TASK
# ─────────────────────────────────────────────────────────────

feedback_task = Task(
    description=(
        "You are the Feedback & Introspection Agent. You NEVER talk to the user.\n\n"
        "DO NOT USE ANY TOOLS. Just analyze the provided inputs directly.\n\n"
        "Inputs:\n"
        "- user_message: current turn message.\n"
        "- plan: current plan from the orchestrator.\n"
        "- agent_outputs: dict-like text of what each specialist agent produced.\n"
        "- previous_user_message: last user message (if any).\n"
        "- previous_answer: last final answer the user saw (if any).\n"
        "- previous_feedback_report: previous introspection report as JSON string "
        "  (may be null).\n\n"
        "Analyze these inputs and return ONLY a JSON object. Do not call any tools.\n\n"
        "Return ONLY a JSON object with:\n"
        "- 'overall_quality': 'low' | 'medium' | 'high'\n"
        "- 'alignment_with_user': 'low' | 'medium' | 'high'\n"
        "- 'risk_flags': list of short strings\n"
        "- 'policy_flags': list of short strings\n"
        "- 'user_feedback_signal': short description of how the user reacted\n"
        "- 'notes_for_orchestrator': short guidance for improving the next answer\n"
        "- 'log_entry': one-line summary for logging.\n\n"
        "User message: {user_message}\n"
        "Plan: {plan}\n"
        "Agent outputs: {agent_outputs}\n"
        "Previous user message: {previous_user_message}\n"
        "Previous answer: {previous_answer}\n"
        "Previous feedback report: {previous_feedback_report}"
    ),
    agent=feedback_agent,
    expected_output=(
        "A valid JSON object with keys: overall_quality, alignment_with_user, "
        "risk_flags, policy_flags, user_feedback_signal, notes_for_orchestrator, "
        "log_entry."
    ),
)

# ─────────────────────────────────────────────────────────────
# 4. FINAL ANSWER TASK (main orchestrator talks to user)
# ─────────────────────────────────────────────────────────────

final_answer_task = Task(
    description=(
        "You are the AI Mortgage Broker and the ONLY agent that speaks to the user.\n\n"
        "CRITICAL: DO NOT USE ANY TOOLS. You already have ALL information from specialist agents.\n"
        "Your ONLY job is to synthesize their outputs into a concise, conversational answer.\n\n"
        "You receive:\n"
        "- user_message\n"
        "- plan (which agents were called)\n"
        "- agent_outputs (eligibility, products, paperwork, customer_intel)\n"
        "- feedback_report (introspection JSON)\n"
        "- previous_user_message (if any)\n"
        "- previous_answer (if any)\n\n"
        "If agent_outputs contains 'customer_intel', it is a JSON report with fields "
        "like engagement_score, churn_risk, conversion_likelihood, behavioral_signals, "
        "and recommended_actions. Treat this as INTERNAL guidance about engagement and "
        "follow-up style; do NOT show the raw JSON to the user.\n\n"
        "Use all of this to:\n"
        "- Correct any mistakes or confusion flagged in feedback_report.\n"
        "- Adjust tone and urgency based on engagement/churn risk.\n"
        "- Provide a clear, realistic broker-style answer including eligibility "
        "  context, product options (if relevant), and document / next-step guidance.\n\n"
        "Keep responses SHORT and CONVERSATIONAL (3-5 sentences max).\n\n"
        "Write directly to the user in the first person as their mortgage advisor. "
        "Do NOT output JSON or mention internal agent names.\n\n"
        "User message: {user_message}\n"
        "Plan: {plan}\n"
        "Agent outputs: {agent_outputs}\n"
        "Feedback report: {feedback_report}\n"
        "Previous user message: {previous_user_message}\n"
        "Previous answer: {previous_answer}"
    ),
    agent=main_orchestrator,
    expected_output=(
        "A single coherent answer that:\n"
        "- Explains how a lender might view their situation.\n"
        "- Gives approximate eligibility or scenarios where possible.\n"
        "- Summarises any relevant product options.\n"
        "- Clearly states what documents and steps come next.\n"
        "- Acknowledges and corrects previous mistakes if the user pointed them out.\n"
        "- Implicitly reflects engagement / churn risk in tone and follow-up suggestions."
    ),
)
