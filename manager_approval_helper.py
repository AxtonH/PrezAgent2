import streamlit as st
import re
from datetime import datetime
from typing import Optional, Dict, List
from collections import defaultdict
from odoo_connector import (
    get_pending_time_off_requests, approve_time_off_request, deny_time_off_request,
    is_manager, get_employee_by_leave_id, get_pending_overtime_requests,
    approve_overtime_request, refuse_overtime_request, cancel_overtime_request
)

def detect_approval_intent(query):
    """
    Detect if the user (manager) is trying to approve/deny time off requests or view approved time off
    
    Args:
        query: User's message
        
    Returns:
        String indicating intent: 'view_pending', 'approve', 'deny', 'view_approved', or None
    """
    query_lower = query.lower()
    
    # Check for approved time off viewing first
    if detect_approved_time_off_intent(query):
        return 'view_approved'
    
    # Keywords for viewing pending requests
    view_keywords = [
        'pending requests', 'pending time off', 'pending leave',
        'requests pending', 'time off requests', 'leave requests',
        'approve requests', 'review requests', 'show requests',
        'view requests', 'check requests', 'my team requests',
        'subordinate requests', 'employee requests',
        'who requested time off', 'any time off requests'
    ]
    
    # Keywords for approval
    approve_keywords = [
        'approve request', 'approve time off', 'approve leave',
        'approve id', 'approve #', 'yes approve', 'confirm request',
        'accept request', 'grant time off', 'grant leave'
    ]
    
    # Keywords for denial
    deny_keywords = [
        'deny request', 'deny time off', 'deny leave',
        'reject request', 'reject time off', 'reject leave',
        'decline request', 'refuse request', 'deny id', 'deny #'
    ]
    
    # Check for specific intents
    if any(keyword in query_lower for keyword in approve_keywords):
        return 'approve'
    elif any(keyword in query_lower for keyword in deny_keywords):
        return 'deny'
    elif any(keyword in query_lower for keyword in view_keywords):
        return 'view_pending'
    
    # Also check for patterns like "approve 123" or "deny 456"
    import re
    if re.search(r'\b(approve|accept|grant)\s+\d+\b', query_lower):
        return 'approve'
    elif re.search(r'\b(deny|reject|decline|refuse)\s+\d+\b', query_lower):
        return 'deny'
    
    return None

def extract_request_id(query):
    """
    Extract time off request ID from the query
    
    Args:
        query: User's message
        
    Returns:
        Integer request ID or None
    """
    import re
    
    # Look for patterns like "approve 123", "deny #456", "request 789", etc.
    patterns = [
        r'\b(?:approve|deny|reject|accept|request|id|#)\s*(\d+)\b',
        r'\b(\d+)\b'  # Just numbers
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query.lower())
        if match:
            try:
                return int(match.group(1))
            except:
                continue
    
    return None

def extract_denial_reason(query):
    """
    Extract reason for denial from the query
    
    Args:
        query: User's message
        
    Returns:
        String reason or empty string
    """
    query_lower = query.lower()
    
    # Look for patterns like "because...", "reason:...", etc.
    reason_patterns = [
        r'because\s+(.+)',
        r'reason[:\s]+(.+)',
        r'due to\s+(.+)',
        r'since\s+(.+)',
        r'-\s*(.+)',  # Dash followed by reason
        r':\s*(.+)'   # Colon followed by reason
    ]
    
    for pattern in reason_patterns:
        match = re.search(pattern, query_lower)
        if match:
            reason = match.group(1).strip()
            # Clean up the reason
            reason = reason.rstrip('.!?,;')
            return reason
    
    return ""

def _parse_date(date_str: str) -> Optional[datetime.date]:
    """
    Convert an Odoo ISO/date-time string to a `date`, or None on failure.

    Handles both "2025-06-26T00:00:00" and "2025-06-26 06:00:00".
    """
    if not date_str:
        return None

    sep = 'T' if 'T' in date_str else ' '          # split on first time separator
    date_part = date_str.split(sep)[0]

    try:
        return datetime.strptime(date_part, '%Y-%m-%d').date()
    except Exception:
        return None

def format_date_dmy(d: datetime.date) -> str:
    """Return day-month-year as "26 - 6 - 2025" (no leading zeros)."""
    return f"{d.day} - {d.month} - {d.year}"

def leave_status_emoji(date_from: str, date_to: str) -> str:
    """
    🔜  future leave
    📍  currently on leave
    📅  past leave
    """
    today = datetime.now().date()
    start = _parse_date(date_from)
    end   = _parse_date(date_to)

    if not start or not end:
        return "📅"                     # fall back

    if start > today:
        return "🔜"
    if start <= today <= end:
        return "📍"
    return "📅"

def leave_status_emoji(date_from: str, date_to: str) -> str:
    """
    🔜  future leave
    📍  currently on leave
    📅  past leave (still shown for context)
    """
    today = datetime.now().date()
    start = _parse_date(date_from)
    end   = _parse_date(date_to)

    if not start or not end:
        return "📅"                    # fallback

    if start > today:
        return "🔜"
    if start <= today <= end:
        return "📍"
    return "📅"

def handle_manager_approval_flow(query, employee_data):
    """
    Handle the manager approval flow for time-off requests and give
    approve/deny recommendations based on current team coverage.
    """
    employee_id = employee_data.get('id')

    # ── manager check ─────────────────────────────────────────────────────────
    if not is_manager(employee_id):
        return ("You don't appear to have any direct reports. "
                "This feature is only available for managers.")

    # ── team context ─────────────────────────────────────────────────────────
    team_info         = employee_data.get('team_data', {})
    subordinate_count = team_info.get('subordinate_count', 0)
    subordinates      = team_info.get('subordinates', [])

    # debug snapshot
    if 'debug_info' not in st.session_state:
        st.session_state.debug_info = {}
    st.session_state.debug_info['manager_flow'] = {
        'manager_id': employee_id,
        'subordinate_count': subordinate_count,
        'subordinate_names': [s['name'] for s in subordinates],
    }

    # ── small helper: overlap-check ──────────────────────────────────────────
    def recommend_action(pending_req, approved_reqs, team_size):
        """
        Return ('Approve' | 'Deny', overlap_ratio_float).
        Consider the request DENY if >20 % of the team are already
        on overlapping approved leave.
        """
        if team_size <= 0:
            team_size = 1                       # safety

        # date range of the pending request
        p_start = _parse_date(
            pending_req.get('date_from') or pending_req.get('request_date_from', '')
        )
        p_end   = _parse_date(
            pending_req.get('date_to')   or pending_req.get('request_date_to', '')
        )
        if not p_start or not p_end:
            return ("Approve", 0.0)            # cannot judge → default approve

        overlapping_emp_ids = set()
        for appr in approved_reqs:
            a_start = _parse_date(appr.get('date_from') or appr.get('request_date_from', ''))
            a_end   = _parse_date(appr.get('date_to')   or appr.get('request_date_to',   ''))
            if not a_start or not a_end:
                continue

            # overlap?
            if (a_start <= p_end) and (a_end >= p_start):
                emp_id = (appr.get('employee_id')[0]
                          if isinstance(appr.get('employee_id'), list)
                          else appr.get('employee_id'))
                # ignore the same employee (they obviously overlap themselves)
                if emp_id != pending_req.get('employee_id', [None])[0]:
                    overlapping_emp_ids.add(emp_id)

        ratio = len(overlapping_emp_ids) / team_size
        return ("Deny", ratio) if ratio > 0.20 else ("Approve", ratio)

    # ── intent detection ─────────────────────────────────────────────────────
    intent = detect_approval_intent(query)

    # =========================================================================
    # VIEW APPROVED  (unchanged)
    # =========================================================================
    if intent == 'view_approved':
        approved_requests = get_approved_time_off_requests(employee_id)

        if not approved_requests:
            team_context = ""
            if subordinates:
                names = ", ".join([s['name'] for s in subordinates[:5]])
                if len(subordinates) > 5:
                    names += f", and {len(subordinates) - 5} others"
                team_context = (
                    f"\n\n📋 **Your team ({subordinate_count} members):** {names}"
                )
            return (f"✅ Your team has no approved time off scheduled "
                    f"for the next 30 days.{team_context}\n\n"
                    "💡 *Type \"cancel\" to return to normal chat.*")

        # ---- build bullet list (same as before) -----------------------------
        from collections import defaultdict
        grouped: Dict[str, List] = defaultdict(list)
        for req in approved_requests:
            emp_info = req.get('employee_id', ['Unknown', 'Unknown'])
            emp_name = (emp_info[1] if isinstance(emp_info, list) and len(emp_info) > 1
                        else str(emp_info))
            grouped[emp_name].append(req)

        lines: List[str] = ["📅 **Approved Time Off for Your Team**\n"]

        for emp_name in sorted(grouped):
            lines.append(f"**{emp_name}:**")
            for req in sorted(grouped[emp_name],
                              key=lambda r: r.get('date_from') or r.get('request_date_from', '')):
                days = req.get('number_of_days', 0)
                if str(days) in ("0", "0.0"):
                    continue

                lt_info = req.get('holiday_status_id', ['Unknown', 'Unknown'])
                leave_type = (lt_info[1] if isinstance(lt_info, list) and len(lt_info) > 1
                              else str(lt_info))

                raw_from = req.get('date_from') or req.get('request_date_from', 'N/A')
                raw_to   = req.get('date_to')   or req.get('request_date_to',   'N/A')
                emoji    = leave_status_emoji(raw_from, raw_to)

                df_dt  = _parse_date(raw_from)
                dt_dt  = _parse_date(raw_to)
                df_fmt = format_date_dmy(df_dt) if df_dt else raw_from
                dt_fmt = format_date_dmy(dt_dt) if dt_dt else raw_to

                desc = req.get('name', '')
                line = f"- {emoji} **{leave_type}**: {df_fmt} → {dt_fmt} ({days} days)"
                if desc and desc not in ('Time Off Request',):
                    line += f"\n     💬 {desc}"
                lines.append(line)
            lines.append("")

        lines.extend([
            "---",
            "**Legend:**",
            "🔜 = Future leave   •   📍 = Currently on leave   •   📅 = Past leave",
            "",
            "Would you like to:",
            "- View pending requests",
            "- See time off for a specific date range",
            "- Return to regular chat",
            "",
            "💡 *Type \"cancel\" to exit this view.*",
        ])
        return "\n".join(lines)

    # =========================================================================
    # VIEW PENDING  (now with recommendations)
    # =========================================================================
    elif intent == 'view_pending' or (intent is None and 'approval_flow' in st.session_state):
        pending = get_pending_time_off_requests(employee_id)
        st.session_state['pending_requests'] = pending
        st.session_state['approval_flow']    = True

        if not pending:
            team_context = ""
            if subordinates:
                names = ", ".join([s['name'] for s in subordinates[:5]])
                if len(subordinates) > 5:
                    names += f", and {len(subordinates) - 5} others"
                team_context = (
                    f"\n\n📋 **Your team ({subordinate_count} members):** {names}"
                    "\n\nIf you expected to see requests, they may have already "
                    "been processed or your team members haven't submitted any yet."
                )
            return ("✅ You have no pending time off requests from your team members."
                    f"{team_context}\n\n"
                    "💡 *Type \"cancel\" to return to normal chat.*")

        # fetch ALL approved leave for overlap check (1 year horizon)
        approved_for_overlap = get_approved_time_off_requests(employee_id, days_ahead=365)

        # ---- format list with recommendations --------------------------------
        response = f"📋 **Pending Time Off Requests ({len(pending)} total)**\n\n"

        for req in pending:
            rid = req.get('id')

            emp_info = req.get('employee_id', ['Unknown', 'Unknown'])
            emp_name = (emp_info[1] if isinstance(emp_info, list) and len(emp_info) > 1
                        else str(emp_info))

            lt_info = req.get('holiday_status_id', ['Unknown', 'Unknown'])
            leave_type = (lt_info[1] if isinstance(lt_info, list) and len(lt_info) > 1
                          else str(lt_info))

            raw_from = req.get('date_from') or req.get('request_date_from', 'N/A')
            raw_to   = req.get('date_to')   or req.get('request_date_to',   'N/A')

            df_dt = _parse_date(raw_from)
            dt_dt = _parse_date(raw_to)
            date_from = format_date_dmy(df_dt) if df_dt else raw_from
            date_to   = format_date_dmy(dt_dt) if dt_dt else raw_to

            days = req.get('number_of_days', 'N/A')
            desc = req.get('name', 'No description')

            # ---------- recommendation ---------------------------------------
            rec, ratio = recommend_action(req, approved_for_overlap, subordinate_count)
            rec_icon   = "✅" if rec == "Approve" else "❌"
            pct_txt    = f"{ratio:.0%}" if subordinate_count else "N/A"

            response += (
                f"**Request #{rid}**\n"
                f"👤 **Employee:** {emp_name}\n"
                f"📅 **Type:** {leave_type}\n"
                f"📆 **Dates:** {date_from} to {date_to} ({days} days)\n"
                f"💬 **Description:** {desc}\n"
                f"{rec_icon} **Recommendation:** {rec} "
                f"(_{pct_txt} of team already off_)\n\n"
            )

        response += (
            "---\n"
            "**Actions:**\n"
            "- To approve a request: Type \"approve [request ID]\" (e.g., \"approve 123\")\n"
            "- To deny a request:   Type \"deny [request ID] - [reason]\" (e.g., \"deny 123 - Team coverage needed\")\n"
            "- To view approved time off: Type \"show approved time off\"\n"
            "- To view more details: Ask about a specific request ID\n\n"
            "💡 *Type \"cancel\" to exit the approval process.*"
        )
        return response

    # ----------------------------------------------------------------------
    # ▸ APPROVE REQUEST
    # ----------------------------------------------------------------------
    elif intent == 'approve':
        request_id = extract_request_id(query)

        if not request_id:
            return (
                "Please specify the request ID you want to approve. "
                "For example: 'approve 123'\n\n💡 *Type \"cancel\" to exit the approval process.*"
            )

        pending_requests = st.session_state.get('pending_requests', [])
        valid_request = any(req['id'] == request_id for req in pending_requests)

        if not valid_request:
            pending_requests = get_pending_time_off_requests(employee_id)
            valid_request = any(req['id'] == request_id for req in pending_requests)
            if not valid_request:
                return (
                    f"❌ Request #{request_id} not found in your pending approvals. Please check the request ID.\n\n"
                    "💡 *Type \"cancel\" to exit the approval process.*"
                )

        result = approve_time_off_request(request_id)

        if result['success']:
            employee_info = get_employee_by_leave_id(request_id)
            employee_name = employee_info.get('name', 'Unknown') if employee_info else 'Unknown'

            if 'approval_flow' in st.session_state:
                del st.session_state['approval_flow']

            return (
                f"✅ {result['message']}\n\n"
                f"The time off request for **{employee_name}** has been approved and they will be notified.\n\n"
                "Would you like to:\n"
                "- View remaining pending requests\n"
                "- View approved time off\n"
                "- Return to regular chat"
            )
        else:
            return f"❌ {result['message']}\n\n💡 *Type \"cancel\" to exit the approval process.*"

    # ----------------------------------------------------------------------
    # ▸ DENY REQUEST
    # ----------------------------------------------------------------------
    elif intent == 'deny':
        request_id = extract_request_id(query)
        reason = extract_denial_reason(query)

        if not request_id:
            return (
                "Please specify the request ID you want to deny. "
                "For example: 'deny 123 - reason for denial'\n\n💡 *Type \"cancel\" to exit the approval process.*"
            )

        pending_requests = st.session_state.get('pending_requests', [])
        valid_request = any(req['id'] == request_id for req in pending_requests)

        if not valid_request:
            pending_requests = get_pending_time_off_requests(employee_id)
            valid_request = any(req['id'] == request_id for req in pending_requests)
            if not valid_request:
                return (
                    f"❌ Request #{request_id} not found in your pending approvals. Please check the request ID.\n\n"
                    "💡 *Type \"cancel\" to exit the approval process.*"
                )

        result = deny_time_off_request(request_id, reason)

        if result['success']:
            employee_info = get_employee_by_leave_id(request_id)
            employee_name = employee_info.get('name', 'Unknown') if employee_info else 'Unknown'

            if 'approval_flow' in st.session_state:
                del st.session_state['approval_flow']

            reason_text = f"\n**Reason:** {reason}" if reason else ""
            return (
                f"✅ {result['message']}\n\n"
                f"The time off request for **{employee_name}** has been denied and they will be notified.{reason_text}\n\n"
                "Would you like to:\n"
                "- View remaining pending requests\n"
                "- View approved time off\n"
                "- Return to regular chat"
            )
        else:
            return f"❌ {result['message']}\n\n💡 *Type \"cancel\" to exit the approval process.*"

    return None

def get_approved_time_off_requests(manager_employee_id: int,
                                   days_ahead: int = 30):
    """
    Return only *approved* leave for the manager's direct reports that is
    happening now or within the next ``days_ahead`` days.

    A leave is considered "approved" when its state is one of the values
    in APPROVED_STATES *and* its ``date_to`` is in the future.
    """
    from datetime import datetime, timedelta

    today    = datetime.now().date()
    horizon  = today + timedelta(days=days_ahead)

    # ------------------------------------------------------------------ 1 ▸ direct reports
    subordinate_ids = st.session_state.odoo_models.execute_kw(
        st.session_state.db, st.session_state.odoo_uid,
        st.session_state.password,
        'hr.employee', 'search',
        [[['parent_id', '=', manager_employee_id]]]
    )
    if not subordinate_ids:
        return []

    # ------------------------------------------------------------------ 2 ▸ approved leave only
    APPROVED_STATES = [
        'validate', 'validate1',        # Odoo standard
        'approved', 'approve',          # custom modules / aliases
        'validated'                     # legacy naming
    ]

    leave_ids = st.session_state.odoo_models.execute_kw(
        st.session_state.db, st.session_state.odoo_uid,
        st.session_state.password,
        'hr.leave', 'search',
        [[
            ['employee_id', 'in', subordinate_ids],
            ['state',       'in', APPROVED_STATES],
            ['date_to',     '>=', str(today)],          # still relevant
            ['date_from',   '<=', str(horizon)]         # within window
        ]]
    )
    if not leave_ids:
        return []

    return st.session_state.odoo_models.execute_kw(
        st.session_state.db, st.session_state.odoo_uid,
        st.session_state.password,
        'hr.leave', 'read',
        [leave_ids],
        {'fields': [
            'id', 'name', 'employee_id', 'holiday_status_id',
            'date_from', 'date_to', 'number_of_days', 'state'
        ]}
    )

def detect_approved_time_off_intent(query):
    """
    Detect if the user (manager) is trying to view approved time off
    
    Args:
        query: User's message
        
    Returns:
        Boolean indicating if they want to see approved time off
    """
    query_lower = query.lower()
    
    # Keywords for viewing approved time off
    approved_keywords = [
        'approved time off', 'approved leave', 'approved vacation',
        'team time off', 'team leave', 'team vacation',
        'who is off', 'who is out', 'who will be out',
        'upcoming time off', 'upcoming leave', 'upcoming vacation',
        'scheduled time off', 'scheduled leave', 'scheduled vacation',
        'team calendar', 'leave calendar', 'time off calendar',
        'approved requests', 'show approved', 'view approved'
    ]
    
    return any(keyword in query_lower for keyword in approved_keywords)

def detect_overtime_approval_intent(query):
    """
    Detects if the user (manager) is trying to manage overtime requests.
    """
    query_lower = query.lower()
    
    view_keywords = ['view overtime', 'show overtime', 'pending overtime', 'overtime requests']
    approve_keywords = ['approve overtime']
    refuse_keywords = ['refuse overtime', 'reject overtime']
    cancel_keywords = ['cancel overtime']

    if any(keyword in query_lower for keyword in approve_keywords):
        return 'approve_overtime'
    if any(keyword in query_lower for keyword in refuse_keywords):
        return 'refuse_overtime'
    if any(keyword in query_lower for keyword in cancel_keywords):
        return 'cancel_overtime'
    if any(keyword in query_lower for keyword in view_keywords):
        return 'view_pending_overtime'
        
    return None

def handle_manager_overtime_approval(query, employee_data):
    """
    Handles the manager approval flow for overtime requests.
    """
    employee_id = employee_data.get('id')
    if not is_manager(employee_id):
        return "This feature is available for managers only."

    intent = detect_overtime_approval_intent(query)
    request_id = extract_request_id(query)

    if intent == 'view_pending_overtime':
        pending_requests = get_pending_overtime_requests(employee_id)
        if not pending_requests:
            return "There are no pending overtime requests for your team."
        
        response = "Here are the pending overtime requests for your team:\n\n"
        for req in pending_requests:
            response += f"- **ID:** {req['id']}\n"
            response += f"  - **Subject:** {req['name']}\n"
            response += f"  - **Employee:** {req['request_owner_id'][1]}\n"
            response += f"  - **Category:** {req['category_id'][1]}\n"
            response += f"  - **Status:** {req['request_status']}\n"
            response += f"  - **Created on:** {req['create_date']}\n\n"
        response += "You can approve, refuse, or cancel a request by its ID (e.g., 'approve overtime 123')."
        return response

    elif intent in ['approve_overtime', 'refuse_overtime', 'cancel_overtime'] and request_id:
        if intent == 'approve_overtime':
            result = approve_overtime_request(request_id)
        elif intent == 'refuse_overtime':
            result = refuse_overtime_request(request_id)
        elif intent == 'cancel_overtime':
            result = cancel_overtime_request(request_id)
        
        if result.get('success'):
            return result.get('message')
        else:
            return f"An error occurred: {result.get('message')}"

    elif intent and not request_id:
        return "Please specify the ID of the overtime request you want to manage."

    return "I'm not sure how to handle that. You can view pending overtime requests or approve/refuse/cancel them by ID."