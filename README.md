# MortgageIQ

A multi-agent mortgage advisory prototype built with [CrewAI](https://www.crewai.com/).
One orchestrator agent plans each conversation turn, specialist agents do the
analysis with their own tools, a feedback agent reviews the work, and the
orchestrator writes a short final answer for the client.

> **Status: working prototype.** The affordability math and document tools are
> real. Rates, appointment booking, CRM data and the document scanner are
> **simulated** (hardcoded sample data). See [What is real vs simulated](#what-is-real-vs-simulated).
> This is not financial advice.

## What it does

For a client message such as *"I make $90k, have $500/month in debts and want
to buy a $600k home with $120k down"*, the system can:

- estimate affordability (GDS/TDS ratios under a stress-test rate) and run
  payment scenarios
- compare mortgage product types (fixed vs variable) using sample rate ranges
- answer policy and FAQ questions from a small local knowledge base
- check which application documents are uploaded and read details from PDFs
- show available appointment slots and "book" one (simulated)
- analyse client engagement from CRM data (simulated) and review its own
  answer quality after each turn

## How it works

| Agent | Responsibility | Tools |
|-------|----------------|-------|
| **AI Mortgage Broker** (orchestrator) | Only agent that talks to the client. Plans which specialists to call, then writes the final 3-5 sentence answer from their outputs. | none |
| **Eligibility Agent** | Assesses how much the client can borrow and flags concerns (high ratios, small down payment). | `credit_scoring_tool`, `mortgage_software_tool` |
| **Product & Rate Search Specialist** | Compares fixed/variable options and explains trade-offs. Instructed never to invent rates. | `rate_finder_tool`, `rag_knowledge_tool` |
| **Paperwork & Application Specialist** | Lists uploaded vs missing documents and verifies details inside PDFs. | `document_loader_tool`, `document_reader_tool`, `digital_scanner_tool` |
| **Customer Intelligence Agent** | Internal only. Scores engagement and churn risk and recommends next actions as JSON. | `crm_tool` |
| **Feedback & Introspection Agent** | Internal only. Reviews the plan, agent outputs and the user's reaction, and returns a quality-metrics JSON report. | none |

`calendar_tool` (appointments) is defined in `tools.py` as well.

### Flow for each user message

`mortgage_crew.py` wires it together in four steps:

1. **Plan:** the orchestrator returns a JSON plan of which specialists to run
   (a default plan is used if the JSON is invalid).
2. **Work:** the planned specialist agents run one after another, each as its
   own single-agent Crew.
3. **Review:** the feedback agent evaluates the outputs, using the previous
   turn as context, and the report is appended to `introspection_logs.jsonl`.
4. **Answer:** the orchestrator combines everything into a short reply. The
   turn is stored so the next message can build on it.

**Why several agents instead of one?** Each specialist has one narrow job and
only the tools it needs, which keeps prompts short and makes mistakes easier to
trace to a single agent. The orchestrator never calls tools itself, so numbers
in the final answer come from tool outputs.

## What is real vs simulated

| Component | Status |
|-----------|--------|
| GDS/TDS and max-mortgage estimate (`credit_scoring_tool`) | **Real calculation.** Uses a 5.25% stress rate, 25-year amortization, 32% GDS / 44% TDS limits, and assumed property tax ($333/mo) and heating ($150/mo). |
| Payment and stress-test scenario (`mortgage_software_tool`) | **Real calculation.** Standard payment formula, stress rate of contract rate + 2% (minimum 5.25%), and a CMHC insurance note when the down payment is under 20%. |
| Knowledge lookup (`rag_knowledge_tool`) | **Real but simple.** Keyword search over the markdown files in `data/`. No embeddings or vector search yet. |
| Document list and reader | **Real.** Lists files in `uploaded_docs/` and reads the first two pages of PDFs. |
| Rates (`rate_finder_tool`) | **Simulated.** Returns fixed sample ranges. No live lender data and no per-bank comparison. |
| Appointments (`calendar_tool`) | **Simulated.** Fixed available slots; "booking" returns a confirmation message but does not create a booking or send email. |
| CRM (`crm_tool`) | **Simulated.** Returns a hardcoded history and profile. |
| Document scanner | **Simulated.** Returns scanning tips only. |

## Run it

```bash
git clone https://github.com/ameeshajaswal/MortgageIQ.git
cd MortgageIQ
python -m venv venv
venv\Scripts\activate          # Windows (use: source venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
```

Create a `.env` file in the project root (it is git-ignored):

```
MISTRAL_API_KEY=your_key_here
MISTRAL_MODEL=mistral-small-latest
```

Start the web interface:

```bash
streamlit run streamlit_app.py
```

The LLM is Mistral, accessed through CrewAI (`config.py`, temperature 0.2).

## Project files

- `agents.py` – the six agents, their goals, and which tools each can use
- `tasks.py` – the task each agent performs (plan, eligibility, products, paperwork, customer intel, feedback, final answer)
- `tools.py` – all tools, including the mortgage calculations
- `mortgage_crew.py` – orchestration: plan, work, review, answer
- `config.py` – LLM configuration (reads the key from `.env`)
- `streamlit_app.py` – chat interface
- `data/` – markdown knowledge base used by `rag_knowledge_tool`

## Known limitations

- Rates, appointments and CRM data are sample data, not live integrations.
- The knowledge lookup is keyword matching, so paraphrased questions can miss.
- The stress test uses a flat 5.25% in the eligibility tool, and property tax
  and heating are fixed assumptions.
- There are no automated tests or evaluation set yet.
- Agent outputs have not been benchmarked for correctness.

## Next steps

- Add tests that check the payment, GDS/TDS and max-mortgage calculations
  against known figures
- Build a small evaluation set of client questions with expected outcomes to
  measure whether the agents' answers are correct
- Replace keyword search with embedding-based retrieval
- Connect real rate data and a real calendar
