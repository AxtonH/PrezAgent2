# session_manager.py
import streamlit as st

class SessionStateManager:
    @staticmethod
    def initialize():
        """Initialize all session state variables"""
        defaults = {
            'logged_in': False,
            'odoo_connected': False,
            'messages': [],
            'employee_data': None,
            'odoo_uid': None,
            'odoo_models': None,
            'debug_info': {},
            'show_debug': False,
            'auto_loaded': False,
            'manual_search_mode': False,
            'template_request': {},
            'template_bytes': None,
            'template_filename': None,
            'username': "",
            'password': ""
        }
        
        for key, default_value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

def get_session_value(key, default=None):
    """Get a value from the session state."""
    return st.session_state.get(key, default)

def update_session_value(key, value):
    """Update a value in the session state."""
    st.session_state[key] = value

def clear_workflow():
    """Clear all workflow-related session state variables."""
    update_session_value('active_workflow', None)
    # Clear specific workflow states
    if 'overtime_request' in st.session_state:
        st.session_state.overtime_request = {}
    if 'employee_request' in st.session_state:
        st.session_state.employee_request = {}
    if 'time_off_request' in st.session_state:
        st.session_state.time_off_request = {}
    if 'template_request' in st.session_state:
        st.session_state.template_request = {}
