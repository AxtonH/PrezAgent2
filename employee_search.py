# employee_search.py
import streamlit as st
from odoo_connector import get_employee_data, get_current_user_employee_data
import re

class EmployeeSearchManager:
    def __init__(self):
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        if 'manual_search_mode' not in st.session_state:
            st.session_state.manual_search_mode = False
        if 'employee_data' not in st.session_state:
            st.session_state.employee_data = None
    
    def render_search_interface(self):
        """Render the employee search interface"""
        if st.session_state.manual_search_mode:
            self._render_manual_search()
        else:
            self._render_auto_load()
    
    def _render_manual_search(self):
        """Render manual search interface"""
        person_name = st.text_input("Enter name:", 
                                  placeholder="Type a name to search",
                                  help="Enter the person's name to retrieve their data")
        
        if st.button("Search") and person_name:
            self.search_employee(person_name)
    
    def _render_auto_load(self):
        """Auto-load current user data"""
        if not st.session_state.get('auto_loaded'):
            with st.spinner("Loading your data..."):
                current_user_data = get_current_user_employee_data()
                if current_user_data:
                    st.session_state.employee_data = current_user_data
                    st.session_state.auto_loaded = True
                else:
                    st.warning("Could not find employee data for your user account.")
    
    def search_employee(self, name):
        """Search for an employee by name"""
        with st.spinner(f"Searching for: {name}"):
            person_data = get_employee_data(name)
            
            if person_data:
                st.session_state.employee_data = person_data
                st.session_state.auto_loaded = False
                self._show_search_result(True, person_data['name'])
            else:
                self._show_search_result(False, name)
    
    def _show_search_result(self, found, name):
        """Display search result"""
        if found:
            st.markdown(f"""
            <div style="display: flex; align-items: center;">
                <div style="background-color: #4EF4A8; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px;"></div>
                <span style="color: #2B1B4C; font-weight: 600;">Found:</span> {name}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="display: flex; align-items: center;">
                <div style="background-color: #FF6666; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px;"></div>
                <span style="color: #2B1B4C; font-weight: 600;">Not found:</span> {name}
            </div>
            """, unsafe_allow_html=True)

def detect_employee_search_intent(query):
    """
    Detect if the user is trying to search for an employee.
    """
    query_lower = query.lower()
    search_keywords = ['who is', 'find', 'search for', 'look up', 'employee details', 'contact info for']
    if any(keyword in query_lower for keyword in search_keywords):
        return True
    return False

def handle_employee_search(query):
    """
    Handles the employee search flow.
    """
    # Extract the name from the query
    name_match = re.search(r'(?:who is|find|search for|look up)\s+(.+)', query, re.IGNORECASE)
    if name_match:
        name = name_match.group(1).strip()
        searcher = EmployeeSearchManager()
        searcher.search_employee(name)
        
        if st.session_state.get('employee_data'):
            employee = st.session_state.employee_data
            # Format a nice response
            response = f"I found details for {employee.get('name', 'N/A')}:\n"
            response += f"- **Job Title:** {employee.get('job_title', 'N/A')}\n"
            response += f"- **Email:** {employee.get('work_email', 'N/A')}\n"
            response += f"- **Work Phone:** {employee.get('work_phone', 'N/A')}\n"
            return response
        else:
            return f"Sorry, I could not find an employee named '{name}'."
    else:
        return "Who would you like to search for? Please provide a name."
