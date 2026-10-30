# tools.py

import os
import glob
import json
import re

from crewai.tools import tool

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

# RAG KNOWLEDGE TOOL (simple keyword search for prototype)

_KB_CACHE = None

def _load_knowledge_base() -> str:
    global _KB_CACHE
    if _KB_CACHE is not None:
        return _KB_CACHE
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    texts = []
    
    if os.path.isdir(data_dir):
        for path in glob.glob(os.path.join(data_dir, "*.md")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    texts.append(f.read())
            except Exception:
                pass
    
    _KB_CACHE = "\n\n".join(texts)
    return _KB_CACHE


@tool("RAG knowledge lookup for policies and FAQs")
def rag_knowledge_tool(query: str) -> str:
    """Search internal knowledge base for mortgage policies and FAQs."""
    kb = _load_knowledge_base()
    if not kb:
        return "Knowledge base is empty."
    
    query_words = [w.lower() for w in query.split() if w.strip()]
    matches = [line for line in kb.splitlines() if any(w in line.lower() for w in query_words)]
    
    if not matches:
        return "No relevant entries found."
    
    return "Relevant entries:\n" + "\n".join(matches[:20])


# CREDIT SCORING TOOL (with actual GDS/TDS calculations)

def _monthly_payment(principal: float, annual_rate: float, years: int) -> float:
    """Standard mortgage payment formula."""
    if annual_rate <= 0:
        return principal / (years * 12)
    r = annual_rate / 12.0
    n = years * 12
    return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)


def _parse_financial_data(text: str) -> dict:
    """Parse financial data from various input formats."""
    data = {}
    
    # Try JSON
    try:
        return json.loads(text)
    except:
        pass
    
    # Try key=value
    for part in text.replace(';', ',').split(','):
        if '=' in part:
            k, v = part.split('=', 1)
            try:
                data[k.strip().lower()] = float(v.strip().replace(',', ''))
            except:
                data[k.strip().lower()] = v.strip()
    
    # Try natural language extraction
    if not data:
        patterns = [
            (r'income[:\s]*\$?([\d,]+)', 'income'),
            (r'debt[s]?[:\s]*\$?([\d,]+)', 'debts'),
            (r'down[:\s]*\$?([\d,]+)', 'down'),
            (r'price[:\s]*\$?([\d,]+)', 'price'),
        ]
        for pattern, key in patterns:
            match = re.search(pattern, text.lower())
            if match:
                data[key] = float(match.group(1).replace(',', ''))
    
    return data


@tool("Check credit and affordability profile")
def credit_scoring_tool(customer_context: str) -> str:
    """
    Analyze affordability using GDS/TDS ratios.
    
    Input formats:
      - "income=90000, debts=500, price=600000, down=120000"
      - {"income": 90000, "debts": 500}
      - "income $90,000, debts $500"
    
    Returns GDS/TDS ratios and max mortgage estimate.
    """
    data = _parse_financial_data(customer_context)
    
    if not data:
        return "Could not parse data. Use: income=90000, debts=500, price=600000, down=120000"
    
    income = data.get('income', 0)
    monthly_debts = data.get('debts', 0)
    price = data.get('price', 0)
    down = data.get('down', 0)
    
    if income <= 0:
        return "Income required for affordability analysis."
    
    monthly_income = income / 12
    results = [f"Annual Income: ${income:,.0f}"]
    
    # Calculate mortgage payment if price provided
    mortgage_payment = 0
    if price > 0:
        principal = price - down
        stress_rate = 0.0525  # Stress test rate
        mortgage_payment = _monthly_payment(principal, stress_rate, 25)
        results.append(f"Mortgage: ${principal:,.0f} → ${mortgage_payment:,.0f}/month (at 5.25% stress test)")
    
    # GDS/TDS calculations
    property_tax = 333  # ~$4000/year estimate
    heating = 150
    housing_costs = mortgage_payment + property_tax + heating
    
    gds = (housing_costs / monthly_income) * 100
    tds = ((housing_costs + monthly_debts) / monthly_income) * 100
    
    results.append(f"GDS: {gds:.1f}% (limit: 32%) {'✓' if gds <= 32 else '⚠️ HIGH'}")
    results.append(f"TDS: {tds:.1f}% (limit: 44%) {'✓' if tds <= 44 else '⚠️ HIGH'}")
    
    # Max mortgage estimate
    max_payment = (monthly_income * 0.32) - property_tax - heating
    if max_payment > 0:
        max_mortgage = max_payment * ((1.0525/12 + 1) ** 300 - 1) / ((0.0525/12) * (1.0525/12 + 1) ** 300)
        results.append(f"Max mortgage (est.): ${max_mortgage:,.0f}")
    
    return "\n".join(results)

# MORTGAGE SOFTWARE TOOL

@tool("Run mortgage affordability scenario")
def mortgage_software_tool(application_data: str) -> str:
    """
    Calculate mortgage payment and affordability.
    Input: price=600000, down=120000, rate=5.0, term_years=25, income=90000
    """
    data = _parse_financial_data(application_data)
    
    try:
        price = data.get('price', 0)
        down = data.get('down', 0)
        rate = data.get('rate', 5.0) / 100
        years = int(data.get('term_years', 25))
        income = data.get('income', 0)
        
        principal = price - down
        payment = _monthly_payment(principal, rate, years)
        stress_payment = _monthly_payment(principal, max(rate + 0.02, 0.0525), years)
        
        results = [
            f"Mortgage: ${principal:,.0f}",
            f"Monthly payment: ${payment:,.0f} (at {rate*100:.2f}%)",
            f"Stress test payment: ${stress_payment:,.0f}"
        ]
        
        if income > 0:
            ratio = (stress_payment / (income/12)) * 100
            results.append(f"Payment/Income: {ratio:.1f}%")
        
        # CMHC check
        if down / price < 0.20:
            results.append("Note: CMHC insurance required (down payment < 20%)")
        
        return "\n".join(results)
    except Exception as e:
        return f"Error: {e}"


# RATE FINDER TOOL

@tool("Get mortgage rate information")
def rate_finder_tool(rate_query: str) -> str:
    """
    Get typical mortgage rate ranges.
    Input: "5-year fixed", "variable", "compare"
    """
    q = rate_query.lower()
    
    if "5" in q and "fixed" in q:
        return """5-Year Fixed: 4.49% - 5.49%
Pros: Payment stability, protection from increases
Cons: Higher break penalty, won't benefit if rates drop"""
    
    elif "variable" in q:
        return """Variable: Prime ± 0.50% (currently ~6.70% - 7.70%)
Pros: Lower break penalty, benefits if rates drop
Cons: Payment can change, less predictable"""
    
    elif "compare" in q:
        return """5-Year Fixed: 4.49% - 5.49% (stable, higher penalty)
3-Year Fixed: 4.69% - 5.29% (shorter commitment)
Variable: Prime ± 0.50% (flexible, rate risk)"""
    
    else:
        return """Current typical ranges:
5-Year Fixed: 4.49% - 5.49%
3-Year Fixed: 4.69% - 5.29%
Variable: Prime ± 0.50%
Note: Actual rates depend on credit and lender."""

# DIGITAL SCANNER TOOL

@tool("Scan and digitize documents")
def digital_scanner_tool(scan_request: str) -> str:
    """
    Guide user through document scanning.
    Input: document type to scan (e.g., "pay stub", "ID")
    """
    doc = scan_request.lower()
    
    if 'pay' in doc or 'stub' in doc:
        tips = "Include all pages, ensure salary figures are visible"
    elif 'employ' in doc or 'letter' in doc:
        tips = "Show company letterhead and signature"
    elif 'bank' in doc or 'statement' in doc:
        tips = "Include all pages with account number and balances"
    elif 'id' in doc or 'passport' in doc or 'license' in doc:
        tips = "Capture front and back, ensure photo is clear"
    elif 'tax' in doc or 't4' in doc:
        tips = "Include all pages, income figures must be readable"
    else:
        tips = "Ensure all text is readable, include all pages"
    
    return f"Ready to scan. Tips: {tips}\n[In production: Would launch camera/scanner]"


# DOCUMENT TOOLS

@tool("List uploaded documents")
def document_loader_tool(doc_description: str) -> str:
    """List uploaded documents and identify their types."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    docs_dir = os.path.join(base_dir, "uploaded_docs")
    
    if not os.path.isdir(docs_dir):
        return "No uploaded_docs folder. User needs to upload documents."
    
    files = glob.glob(os.path.join(docs_dir, "*.*"))
    if not files:
        return "No documents uploaded yet."
    
    doc_list = []
    for f in files:
        name = os.path.basename(f).lower()
        if 'pay' in name or 'stub' in name:
            dtype = "Pay Stub"
        elif 'bank' in name or 'statement' in name:
            dtype = "Bank Statement"
        elif 'employ' in name or 'letter' in name:
            dtype = "Employment Letter"
        elif 'passport' in name or 'license' in name or 'id' in name:
            dtype = "ID"
        elif 'tax' in name or 't4' in name or 't1' in name:
            dtype = "Tax Document"
        else:
            dtype = "Other"
        doc_list.append(f"• {os.path.basename(f)} → {dtype}")
    
    return f"Uploaded ({len(doc_list)}):\n" + "\n".join(doc_list) + "\n\nRequired: Pay stubs, Employment letter, Bank statements, ID, Tax returns"


@tool("Read document content")
def document_reader_tool(filename: str) -> str:
    """Extract text from a specific PDF document."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(base_dir, "uploaded_docs", filename)
    
    if not os.path.exists(filepath):
        return f"File not found: {filename}"
    
    if not filename.lower().endswith('.pdf'):
        return "Only PDF files supported."
    
    if PyPDF2 is None:
        return "PyPDF2 not installed."
    
    try:
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages[:2]:
                text += (page.extract_text() or "") + "\n"
        
        if not text.strip():
            return "Could not extract text (may be scanned image)."
        
        return text[:2500] + ("..." if len(text) > 2500 else "")
    except Exception as e:
        return f"Error reading file: {e}"


# CRM TOOL

@tool("Access CRM system")
def crm_tool(action: str) -> str:
    """
    Access customer relationship data.
    
    Actions:
      - "history" - Get interaction history
      - "profile" - Get customer profile
      - "log:<event>" - Log an event (e.g., "log:documents_uploaded")
      - "status:<new_status>" - Update status (e.g., "status:pre-approved")
    """
    action = action.lower().strip()
    
    if 'history' in action:
        return """Interaction History:
- Today: Chat session, 4 documents uploaded
- Yesterday: Initial inquiry
- 2 days ago: Website visit (rate calculator)
Engagement: High (78/100)"""
    
    elif 'profile' in action:
        return """Customer Profile:
- Status: Active Lead
- Stage: Document Collection
- Type: First-time buyer
- Timeline: 2-3 months
- Preferred contact: Chat"""
    
    elif action.startswith('log:'):
        event = action.split(':', 1)[1] if ':' in action else 'interaction'
        return f"Logged: {event}"
    
    elif action.startswith('status:'):
        status = action.split(':', 1)[1] if ':' in action else 'updated'
        return f"Status updated to: {status}"
    
    else:
        return "CRM actions: history, profile, log:<event>, status:<new_status>"


# CALENDAR TOOL

@tool("Schedule appointments")
def calendar_tool(request: str) -> str:
    """
    Manage appointment scheduling.
    
    Actions:
      - "available" - Show available slots
      - "book:<slot>" - Book appointment (e.g., "book:Tuesday 2pm")
      - "upcoming" - Show scheduled appointments
    """
    request = request.lower().strip()
    
    if 'available' in request or 'slots' in request:
        return """Available slots:
- Tuesday 2:00 PM
- Wednesday 10:00 AM
- Wednesday 3:30 PM
- Thursday 11:00 AM
- Friday 9:00 AM
To book: "book:Tuesday 2pm" """
    
    elif request.startswith('book:') or 'book' in request:
        slot = request.split(':', 1)[1] if ':' in request else "requested time"
        return f"""Appointment booked: {slot}
- Type: Mortgage Consultation (30 min)
- Confirmation email sent
Please have your documents ready."""
    
    elif 'upcoming' in request:
        return "No upcoming appointments. Ask for 'available' slots to book."
    
    else:
        return "Calendar actions: available, book:<slot>, upcoming"