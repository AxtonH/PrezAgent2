# expense_report_helper.py
"""
Expense Report Helper for Chatbot
Handles the workflow for creating a new expense report (hr.expense) in Odoo via the chatbot.
Currently supports only the [EXP_GEN] Miscellaneous category, with fields:
- Description
- Total paid (JOD)
- Expense date
- Company (auto from user)

Future extensions: receipt upload, more categories, currency selection.
"""

import streamlit as st
from datetime import datetime
from typing import Optional, Dict, Any

# Placeholder for Odoo connector import (to be implemented)
# from odoo_connector import create_expense_report
from odoo_connector import create_and_submit_expense

# --- Workflow State Keys ---
EXPENSE_STATE_KEY = "expense_report_state"

# --- Main Workflow Functions ---
def start_expense_workflow(session_state: Any, user_profile: dict):
    """
    Initiate the expense report workflow. Set up state and prompt for category selection.
    """
    session_state[EXPENSE_STATE_KEY] = {
        "step": "category",
        "data": {},
        "user_id": user_profile.get("odoo_user_id"),
        "company_id": user_profile.get("company_id"),
        "company_name": user_profile.get("company_name"),
    }
    return (
        "Let's create a new expense report! Please choose a category:\n"
        "1. [EXP_GEN] Miscellaneous\n"
        "2. [TRANS & ACC] Travel & Accommodation\n"
        "3. [PER_DIEM] Per Diem\n"
        "\nType the number or the category name.\n(Type 'cancel' at any time to abort.)"
    )

def fetch_per_diem_destinations():
    """Fetch the list of available destinations (res.country.state) from Odoo."""
    try:
        states = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'res.country.state',
            'search_read',
            [[]],
            {'fields': ['id', 'name'], 'limit': 100}
        )
        return states
    except Exception as e:
        return []

def handle_expense_workflow(session_state: Any, user_input: str) -> Optional[str]:
    """
    Handle the next step in the expense workflow based on current state and user input.
    Returns a prompt for the next step, or None if the workflow is complete.
    """
    state = session_state.get(EXPENSE_STATE_KEY)
    if not state:
        return ""
    step = state["step"]
    data = state["data"]

    # Universal cancel support
    if user_input.strip().lower() == "cancel":
        session_state.pop(EXPENSE_STATE_KEY, None)
        return "Expense report creation cancelled. Returning to normal bot activity."

    if step == "category":
        val = user_input.strip().lower()
        if val in ["1", "[exp_gen] miscellaneous", "miscellaneous", "exp_gen"]:
            data["category"] = "misc"
            state["step"] = "description"
            return "Please enter a description for your expense (e.g., 'Lunch with Customer')."
        elif val in ["2", "[trans & acc] travel & accommodation", "travel & accommodation", "trans & acc", "travel", "accommodation"]:
            data["category"] = "travel"
            state["step"] = "description"
            return "Please enter a description for your Travel & Accommodation expense (e.g., 'Hotel for business trip')."
        elif val in ["3", "[per_diem] per diem", "per diem", "perdiem", "per-diem"]:
            data["category"] = "per_diem"
            state["step"] = "description"
            return "Please enter a description for your Per Diem expense (e.g., 'Business trip per diem')."
        else:
            return (
                "Invalid category. Please choose one of the following:\n"
                "1. [EXP_GEN] Miscellaneous\n"
                "2. [TRANS & ACC] Travel & Accommodation\n"
                "3. [PER_DIEM] Per Diem\n"
                "\nType the number or the category name.\n(Type 'cancel' at any time to abort.)"
            )

    if step == "description":
        data["description"] = user_input.strip()
        state["step"] = "purpose"
        return "Optionally, please enter the purpose of this expense (or type 'skip' to leave blank)."

    elif step == "purpose":
        if user_input.strip().lower() != "skip":
            data["purpose"] = user_input.strip()
        else:
            data["purpose"] = None
        state["step"] = "attached_link"
        return "Optionally, please enter an attached link (or type 'skip' to leave blank)."

    elif step == "attached_link":
        if user_input.strip().lower() != "skip":
            data["attached_link"] = user_input.strip()
        else:
            data["attached_link"] = None
        # Now continue to the next required step based on category
        if data.get("category") == "per_diem":
            state["step"] = "date"
            return "What is the expense date? (please use DD/MM/YYYY)"
        elif data.get("category") == "travel":
            state["step"] = "total"
            return "What is the total amount paid? (in JOD)"
        else:
            state["step"] = "total"
            return "What is the total amount paid? (in JOD)"

    elif step == "total":
        try:
            total = float(user_input.strip())
            if total <= 0:
                raise ValueError
            data["total"] = total
            state["step"] = "date"
            return "What is the expense date? (please use DD/MM/YYYY)"
        except ValueError:
            return "Please enter a valid positive number for the total amount (in JOD)."

    elif step == "date":
        try:
            date_obj = datetime.strptime(user_input.strip(), "%d/%m/%Y")
            data["date"] = date_obj.strftime("%Y-%m-%d")
            if data.get("category") == "per_diem":
                state["step"] = "from_date"
                return "What is the start date for your per diem? (please use DD/MM/YYYY)"
            else:
                state["step"] = "confirm"
                cat_display = (
                    "[EXP_GEN] Miscellaneous" if data.get("category") == "misc" else "[TRANS & ACC] Travel & Accommodation"
                )
                summary = (
                    f"Expense Summary:\n"
                    f"Description: {data['description']}\n"
                    f"Purpose: {data.get('purpose') or '-'}\n"
                    f"Attached Link: {data.get('attached_link') or '-'}\n"
                    f"Category: {cat_display}\n"
                    f"Total: {data['total']} JOD\n"
                    f"Date: {date_obj.strftime('%d/%m/%Y')}\n"
                    f"Company: {state['company_name']}\n\n"
                    "Type 'confirm' to submit this expense, or 'cancel' to abort."
                )
                return summary
        except ValueError:
            return "Please enter a valid date in DD/MM/YYYY format."

    elif step == "from_date":
        try:
            from_date_obj = datetime.strptime(user_input.strip(), "%d/%m/%Y")
            data["from_date"] = from_date_obj.strftime("%Y-%m-%d")
            state["step"] = "to_date"
            return "What is the end date for your per diem? (please use DD/MM/YYYY)"
        except ValueError:
            return "Please enter a valid date in DD/MM/YYYY format."

    elif step == "to_date":
        try:
            to_date_obj = datetime.strptime(user_input.strip(), "%d/%m/%Y")
            data["to_date"] = to_date_obj.strftime("%Y-%m-%d")
            state["step"] = "destination"
            # Fetch destinations
            destinations = fetch_per_diem_destinations()
            if not destinations:
                return "❌ Could not fetch destinations from Odoo. Please contact HR."
            state["available_destinations"] = destinations
            dest_list = "\n".join([f"- {d['name']}" for d in destinations[:10]])
            return f"Please select the destination for your per diem. Here are some options:\n\n{dest_list}\n\nType the destination name or ID. (Type 'show all' to see the full list.)"
        except ValueError:
            return "Please enter a valid date in DD/MM/YYYY format."

    elif step == "destination":
        destinations = state.get("available_destinations", [])
        if user_input.strip().lower() == "show all":
            dest_list = "\n".join([f"- {d['name']} (ID: {d['id']})" for d in destinations])
            return f"All available destinations:\n\n{dest_list}\n\nType the destination name or ID."
        # Try to match by name or ID
        match = None
        for d in destinations:
            if user_input.strip().lower() == d["name"].lower() or user_input.strip() == str(d["id"]):
                match = d
                break
        if match:
            data["destination_id"] = match["id"]
            state["step"] = "confirm"
            summary = (
                f"Expense Summary:\n"
                f"Description: {data['description']}\n"
                f"Purpose: {data.get('purpose') or '-'}\n"
                f"Attached Link: {data.get('attached_link') or '-'}\n"
                f"Category: [PER_DIEM] Per Diem\n"
                f"Date: {data['date']}\n"
                f"From: {data['from_date']}\n"
                f"To: {data['to_date']}\n"
                f"Destination: {match['name']}\n"
                f"Company: {state['company_name']}\n\n"
                "Type 'confirm' to submit this expense, or 'cancel' to abort."
            )
            return summary
        else:
            dest_list = "\n".join([f"- {d['name']} (ID: {d['id']})" for d in destinations[:10]])
            return f"I couldn't find a matching destination. Here are some options:\n\n{dest_list}\n\nType the destination name or ID. (Type 'show all' to see the full list.)"

    elif step == "confirm":
        if user_input.strip().lower() == "confirm":
            # Actually call Odoo to create and submit the expense
            if data.get("category") == "per_diem":
                result = create_expense_report_odoo_per_diem(
                    state["user_id"],
                    state["company_id"],
                    data["description"],
                    0,  # total is not needed for per diem, pass 0
                    data["date"],
                    data["from_date"],
                    data["to_date"],
                    data["destination_id"],
                    data.get("purpose"),
                    data.get("attached_link")
                )
            elif data.get("category") == "travel":
                result = create_expense_report_odoo_travel(
                    state["user_id"],
                    state["company_id"],
                    data["description"],
                    data["total"],
                    data["date"],
                    data.get("purpose"),
                    data.get("attached_link")
                )
            else:
                result = create_expense_report_odoo(
                    state["user_id"],
                    state["company_id"],
                    data["description"],
                    data["total"],
                    data["date"],
                    data.get("purpose"),
                    data.get("attached_link")
                )
            session_state.pop(EXPENSE_STATE_KEY, None)
            if result.get("success"):
                return f"✅ Your expense report has been submitted for approval! (ID: {result.get('expense_id', 'N/A')})"
            else:
                return f"❌ Failed to submit expense: {result.get('message', 'Unknown error')}"
        elif user_input.strip().lower() == "cancel":
            session_state.pop(EXPENSE_STATE_KEY, None)
            return "Expense report creation cancelled."
        else:
            return "Please type 'confirm' to submit or 'cancel' to abort."

    return None

# --- Odoo Connector Function (to be implemented) ---
def create_expense_report_odoo(
    user_id: int,
    company_id: int,
    description: str,
    total: float,
    date: str,
    purpose: Optional[str] = None,
    attached_link: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create and submit a new expense report in Odoo (hr.expense) for the given user.
    Returns the created expense record or error info.
    """
    return create_and_submit_expense(user_id, company_id, description, total, date, purpose, attached_link)

def create_expense_report_odoo_travel(
    user_id: int,
    company_id: int,
    description: str,
    total: float,
    date: str,
    purpose: Optional[str] = None,
    attached_link: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create and submit a new Travel & Accommodation expense report in Odoo (hr.expense) for the given user.
    Returns the created expense record or error info.
    """
    from odoo_connector import create_and_submit_travel_accommodation_expense
    return create_and_submit_travel_accommodation_expense(user_id, company_id, description, total, date, purpose, attached_link)

def create_expense_report_odoo_per_diem(
    user_id: int,
    company_id: int,
    description: str,
    total: float,
    date: str,
    from_date: str,
    to_date: str,
    destination_id: int,
    purpose: Optional[str] = None,
    attached_link: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create and submit a new Per Diem expense report in Odoo (hr.expense) for the given user.
    Returns the created expense record or error info.
    """
    from odoo_connector import create_and_submit_per_diem_expense
    return create_and_submit_per_diem_expense(user_id, company_id, description, total, date, from_date, to_date, destination_id, purpose, attached_link)

# --- Helper Functions (if needed) ---
# (Add validation, formatting, etc. here) 