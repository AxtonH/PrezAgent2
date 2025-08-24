# activity_tracker.py
import streamlit as st
from datetime import datetime
from typing import Dict, Any, List

def log_activity(activity_type: str, details: Dict[str, Any] = None, summary: str = None):
    """
    Log a completed activity to the recent activities list
    
    Args:
        activity_type: Type of activity (template_request, overtime_request, etc.)
        details: Additional details about the activity
        summary: Human-readable summary of what was done
    """
    if 'recent_activities' not in st.session_state:
        st.session_state.recent_activities = []
    
    # Activity type mapping
    activity_titles = {
        'template_request': 'Document Generated',
        'overtime_request': 'Overtime Request',
        'employee_request': 'Time Off Request',
        'expense_report': 'Expense Report',
        'manager_approval': 'Approval Given',
        'manager_overtime_approval': 'Overtime Approval',
        'reimbursement_request': 'Reimbursement Request'
    }
    
    # Activity icons
    activity_icons = {
        'template_request': '📄',
        'overtime_request': '⏰',
        'employee_request': '🏖️',
        'expense_report': '💰',
        'manager_approval': '✅',
        'manager_overtime_approval': '⏰✅',
        'reimbursement_request': '💳'
    }
    
    activity = {
        'type': activity_type,
        'title': activity_titles.get(activity_type, 'Unknown Activity'),
        'icon': activity_icons.get(activity_type, '📋'),
        'summary': summary or f"{activity_titles.get(activity_type, 'Activity')} completed successfully",
        'timestamp': datetime.now().isoformat(),
        'details': details or {}
    }
    
    # Add to the beginning of the list (most recent first)
    st.session_state.recent_activities.insert(0, activity)
    
    # Keep only the last 10 activities
    if len(st.session_state.recent_activities) > 10:
        st.session_state.recent_activities = st.session_state.recent_activities[:10]
    
    # Also update the legacy session state for backward compatibility
    st.session_state.last_completed_flow = activity_type
    st.session_state.last_completed_meta = {
        'summary': activity['summary'],
        'timestamp': activity['timestamp'],
        'title': activity['title'],
        'icon': activity['icon']
    }
    # Mark activities as updated so UI can refresh after main render
    st.session_state['activities_dirty'] = True

def get_recent_activities() -> List[Dict[str, Any]]:
    """
    Get the list of recent activities
    
    Returns:
        List of recent activities
    """
    return st.session_state.get('recent_activities', [])

def clear_activities():
    """Clear all recent activities"""
    st.session_state.recent_activities = []
    if 'last_completed_flow' in st.session_state:
        del st.session_state.last_completed_flow
    if 'last_completed_meta' in st.session_state:
        del st.session_state.last_completed_meta

def format_activity_time(timestamp: str) -> str:
    """
    Format activity timestamp for display
    
    Args:
        timestamp: ISO format timestamp string
        
    Returns:
        Human-readable time string
    """
    try:
        dt = datetime.fromisoformat(timestamp)
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    except:
        return "Recently"

# Activity tracking decorators and helpers
def track_template_generation(template_type: str, details: Dict[str, Any] = None):
    """Track template generation activity"""
    summary = f"Generated {template_type} document"
    log_activity('template_request', details, summary)

def track_overtime_request(hours: float, date: str, details: Dict[str, Any] = None):
    """Track overtime request activity"""
    summary = f"Requested {hours} hours overtime for {date}"
    log_activity('overtime_request', details, summary)

def track_time_off_request(leave_type: str, start_date: str, end_date: str, details: Dict[str, Any] = None):
    """Track time off request activity"""
    summary = f"Requested {leave_type} from {start_date} to {end_date}"
    log_activity('employee_request', details, summary)

def track_manager_approval(request_type: str, employee_name: str, details: Dict[str, Any] = None):
    """Track manager approval activity"""
    summary = f"Approved {request_type} for {employee_name}"
    log_activity('manager_approval', details, summary)

def track_expense_report(amount: float, details: Dict[str, Any] = None):
    """Track expense report activity"""
    summary = f"Submitted expense report for ${amount:.2f}"
    log_activity('expense_report', details, summary)

def track_reimbursement_request(amount: float, reason: str, details: Dict[str, Any] = None):
    """Track reimbursement request activity"""
    summary = f"Requested ${amount:.2f} reimbursement for {reason}"
    log_activity('reimbursement_request', details, summary)

def track_manager_overtime_approval(employee_name: str, request_id: int = None, details: Dict[str, Any] = None):
    """Track manager overtime approval activity"""
    det = details or {}
    if request_id is not None:
        det['request_id'] = request_id
    summary = f"Approved overtime for {employee_name}"
    log_activity('manager_overtime_approval', det, summary)