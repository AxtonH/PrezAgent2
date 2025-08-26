# overtime_request_helper.py
import streamlit as st
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from arabic_english_detection import detect_overtime_intent_multilingual, detect_exit_intent_multilingual
from activity_tracker import track_overtime_request

def detect_overtime_intent(query: str) -> bool:
    """
    Detect if the user is trying to request overtime, while ignoring policy questions.
    
    Args:
        query: User's message
        
    Returns:
        Boolean indicating if it's an overtime request
    """
    query_lower = query.lower()
    
    # Words that indicate a policy question, not a request
    policy_keywords = ['policy', 'rule', 'procedure', 'guideline', 'how does', 'what is']
    
    # If the query contains policy-related words, it's not a request
    if any(keyword in query_lower for keyword in policy_keywords):
        return False
        
    overtime_keywords = [
        'overtime', 'over time', 'extra hours', 'work extra',
        'work late', 'additional hours', 'extra work',
        'ot request', 'request overtime', 'book overtime'
    ]
    
    # Only trigger if an overtime keyword is present AND it's not a policy question
    return any(keyword in query_lower for keyword in overtime_keywords)

def parse_flexible_datetime(datetime_str: str) -> Optional[str]:
    """
    Parse datetime string with flexible format support.
    Handles various natural language date/time formats.
    
    Args:
        datetime_str: Various formats like:
            - "15/08 09:00", "15-08 9am", "Aug 15 9:00"
            - "tomorrow 9am", "today 14:30", "15th august 9:00"
            - "2024-08-15 09:00", "15.08.2024 9am"
        
    Returns:
        ISO format datetime string or None if parsing fails
    """
    if not datetime_str:
        return None
        
    datetime_str = datetime_str.strip().lower()
    current_year = datetime.now().year
    today = datetime.now()
    
    # Normalize common variations
    datetime_str = re.sub(r'\b(at|on)\s+', '', datetime_str)
    datetime_str = re.sub(r'\s+', ' ', datetime_str)
    
    # Handle relative dates first
    if 'today' in datetime_str:
        base_date = today
        time_part = re.sub(r'today\s*', '', datetime_str).strip()
    elif 'tomorrow' in datetime_str:
        base_date = today + timedelta(days=1)
        time_part = re.sub(r'tomorrow\s*', '', datetime_str).strip()
    elif 'yesterday' in datetime_str:
        base_date = today - timedelta(days=1)
        time_part = re.sub(r'yesterday\s*', '', datetime_str).strip()
    else:
        base_date = None
        time_part = datetime_str
    
    # If we have a relative date, parse the time part
    if base_date:
        parsed_time = parse_time_part(time_part)
        if parsed_time:
            hour, minute = parsed_time
            return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:00")
        else:
            # Default to start of day if no time specified
            return base_date.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:00")
    
    # Use a more robust approach: split and parse components
    # First try to split by space to separate date and time
    parts = datetime_str.split()
    
    if len(parts) >= 2:
        date_part = parts[0]
        time_part = ' '.join(parts[1:])  # In case there are multiple time parts
        
        # Parse date part
        date_formats = [
            (r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})', lambda m: (int(m.group(3)), int(m.group(2)), int(m.group(1)))),  # DD/MM/YYYY
            (r'(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})', lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3)))),  # YYYY-MM-DD
            (r'(\d{1,2})[/\-\.](\d{1,2})$', lambda m: (current_year, int(m.group(2)), int(m.group(1)))),  # DD/MM (current year)
        ]
        
        year, month, day = None, None, None
        for pattern, extractor in date_formats:
            match = re.match(pattern, date_part)
            if match:
                year, month, day = extractor(match)
                break
        
        if year and month and day:
            # Parse time part
            parsed_time = parse_time_part(time_part)
            if parsed_time:
                hour, minute = parsed_time
                try:
                    dt = datetime(year, month, day, hour, minute, 0)
                    return dt.strftime("%Y-%m-%d %H:%M:00")
                except:
                    pass
    
    # If no space found, try date-only patterns
    elif len(parts) == 1:
        date_part = parts[0]
        
        # Parse date-only formats (default to 00:00)
        date_formats = [
            (r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})$', lambda m: (int(m.group(3)), int(m.group(2)), int(m.group(1)))),  # DD/MM/YYYY
            (r'(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})$', lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3)))),  # YYYY-MM-DD
            (r'(\d{1,2})[/\-\.](\d{1,2})$', lambda m: (current_year, int(m.group(2)), int(m.group(1)))),  # DD/MM (current year)
        ]
        
        for pattern, extractor in date_formats:
            match = re.match(pattern, date_part)
            if match:
                year, month, day = extractor(match)
                try:
                    dt = datetime(year, month, day, 0, 0, 0)
                    return dt.strftime("%Y-%m-%d %H:%M:00")
                except:
                    pass
    
    # Try original function as fallback
    return parse_datetime_input_legacy(datetime_str)

def parse_time_part(time_str: str) -> Optional[tuple]:
    """
    Parse time part from string, handling am/pm and 24h formats.
    Returns (hour, minute) tuple or None.
    """
    if not time_str:
        return None
        
    time_str = time_str.strip().lower()
    
    # Handle am/pm format
    am_pm_match = re.search(r'(\d{1,2})(?:[:\.](\d{2}))?\s*([ap]m)', time_str)
    if am_pm_match:
        hour = int(am_pm_match.group(1))
        minute = int(am_pm_match.group(2) or 0)
        is_pm = am_pm_match.group(3) == 'pm'
        
        if is_pm and hour != 12:
            hour += 12
        elif not is_pm and hour == 12:
            hour = 0
            
        return (hour, minute)
    
    # Handle 24h format
    time_match = re.search(r'(\d{1,2})[:\.](\d{2})', time_str)
    if time_match:
        return (int(time_match.group(1)), int(time_match.group(2)))
    
    # Handle hour only
    hour_match = re.search(r'(\d{1,2})(?!\d)', time_str)
    if hour_match:
        return (int(hour_match.group(1)), 0)
    
    return None

def parse_custom_match(match, original_str: str, current_year: int) -> Optional[str]:
    """
    Handle custom parsing for am/pm and month name formats.
    """
    groups = match.groups()
    
    # Handle am/pm formats
    if 'am' in original_str or 'pm' in original_str:
        if len(groups) >= 4:
            day, month, hour, am_pm = groups[0], groups[1], groups[2], groups[3]
            year = current_year
            
            hour_int = int(hour)
            if am_pm == 'pm' and hour_int != 12:
                hour_int += 12
            elif am_pm == 'am' and hour_int == 12:
                hour_int = 0
                
            dt = datetime(year, int(month), int(day), hour_int, 0, 0)
            return dt.strftime("%Y-%m-%d %H:%M:00")
    
    # Handle month name formats
    month_names = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    for i, group in enumerate(groups):
        if group and group[:3] in month_names:
            month = month_names[group[:3]]
            # Try to extract other components based on pattern
            if i == 0:  # Month first: Aug 15, 2024 9:00
                day = int(groups[1])
                year = int(groups[2]) if groups[2] else current_year
                hour = int(groups[3])
                minute = int(groups[4])
            else:  # Day first: 15 Aug 2024 9:00
                day = int(groups[0])
                year = int(groups[2]) if groups[2] else current_year
                hour = int(groups[3])
                minute = int(groups[4])
                
            dt = datetime(year, month, day, hour, minute, 0)
            return dt.strftime("%Y-%m-%d %H:%M:00")
    
    return None

def parse_datetime_input_legacy(datetime_str: str) -> Optional[str]:
    """
    Legacy datetime parsing function (original implementation).
    Kept for backward compatibility.
    """
    datetime_str = datetime_str.strip()
    current_year = datetime.now().year
    
    # Try simplified format: DD/MM HH:MM (current year, seconds default to 00)
    try:
        dt = datetime.strptime(f"{datetime_str} {current_year}", "%d/%m %H:%M %Y")
        return dt.strftime("%Y-%m-%d %H:%M:00")
    except:
        pass
    
    # Try with explicit year: DD/MM/YYYY HH:MM
    try:
        dt = datetime.strptime(datetime_str, "%d/%m/%Y %H:%M")
        return dt.strftime("%Y-%m-%d %H:%M:00")
    except:
        pass
    
    # Try legacy format with seconds: DD/MM/YYYY HH:MM:SS
    try:
        dt = datetime.strptime(datetime_str, "%d/%m/%Y %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        pass
    
    # Try just date (simplified): DD/MM (assume current year, default to 00:00:00)
    try:
        dt = datetime.strptime(f"{datetime_str} {current_year}", "%d/%m %Y")
        return dt.strftime("%Y-%m-%d 00:00:00")
    except:
        pass
    
    # Try just date (with year): DD/MM/YYYY
    try:
        dt = datetime.strptime(datetime_str, "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d 00:00:00")
    except:
        pass
    
    return None

def parse_overtime_period(query: str) -> Dict[str, Any]:
    """
    Extract overtime period from user input with flexible format support.
    
    Now supports many formats:
    - "from 15/08 09:00 to 15/08 17:00" (original)
    - "tomorrow 9am to 5pm"
    - "from Aug 15 9:00 to Aug 15 17:00"
    - "15-08-2024 09:00 to 15-08-2024 17:00"
    - "start 15/8 9am end 15/8 5pm"
    
    Args:
        query: User's message
        
    Returns:
        Dictionary with start and end datetime
    """
    result = {
        'start': None,
        'end': None,
        'raw_input': query
    }
    
    # Flexible patterns with various keywords and formats
    flexible_patterns = [
        # Traditional "from X to Y" patterns with flexible date formats
        r'from\s+([^,]+?)\s+to\s+([^,\n]+?)(?:\s|$)',
        
        # "start X end Y" patterns
        r'start\s+([^,]+?)\s+end\s+([^,\n]+?)(?:\s|$)',
        
        # "begin X finish Y" patterns
        r'begin\s+([^,]+?)\s+(?:finish|end)\s+([^,\n]+?)(?:\s|$)',
        
        # Time range with dash: "9am-5pm", "09:00-17:00"
        r'(\d{1,2}(?:[:\.](\d{2}))?(?:\s*[ap]m)?)\s*[-–]\s*(\d{1,2}(?:[:\.](\d{2}))?(?:\s*[ap]m)?)',
        
        # More natural language patterns
        r'(?:work|overtime)\s+(?:from\s+)?([^,]+?)\s+(?:until|till|to)\s+([^,\n]+?)(?:\s|$)',
    ]
    
    # First try the original rigid patterns for backward compatibility
    original_patterns = [
        r'from\s+(\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2})\s+to\s+(\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2})',
        r'from\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2})\s+to\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2})',
        r'from\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2})\s+to\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2})'
    ]
    
    all_patterns = original_patterns + flexible_patterns
    
    for pattern in all_patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            groups = match.groups()
            
            # For time range patterns (like 9am-5pm), we need to handle differently
            if len(groups) >= 2 and pattern == flexible_patterns[3]:  # Time range pattern
                # Extract today's date and combine with times
                today = datetime.now().strftime('%d/%m')
                start_str = f"{today} {groups[0]}"
                end_str = f"{today} {groups[2] if groups[2] else groups[1]}"
            else:
                start_str = groups[0].strip()
                end_str = groups[1].strip()
            
            # Use the new flexible parsing function
            result['start'] = parse_flexible_datetime(start_str)
            result['end'] = parse_flexible_datetime(end_str)
            
            if result['start'] and result['end']:
                break
    
    return result

def get_all_overtime_categories() -> List[Dict[str, Any]]:
    """
    Get all available overtime categories from Odoo.
    
    Returns:
        List of category dictionaries.
    """
    try:
        category_ids = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'approval.category',
            'search',
            [[['name', 'ilike', 'overtime']]],
            {'limit': 20} # Limit to a reasonable number
        )
        
        if category_ids:
            categories = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'approval.category',
                'read',
                [category_ids],
                {'fields': ['id', 'name']}
            )
            return categories
        
        return []
    except Exception as e:
        if 'debug_info' not in st.session_state:
            st.session_state.debug_info = {}
        st.session_state.debug_info['overtime_category_error'] = str(e)
        return []

def get_all_projects() -> Dict[str, Any]:
    """
    Get all projects from Odoo
    
    Returns:
        Dictionary with projects data and status flags
    """
    result = {
        'success': False,
        'projects': [],
        'error': None,
        'count': 0
    }
    
    try:
        # First, let's check if we can access the model
        # Try different possible model names
        possible_models = ['project.project', 'project', 'x_project']
        
        for model_name in possible_models:
            try:
                # Test if we can search this model
                test_search = st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    model_name,
                    'search',
                    [[]],
                    {'limit': 1}
                )
                
                # If we get here without error, this model exists
                # Now get all active projects
                project_ids = st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    model_name,
                    'search',
                    [[]], # Remove active filter for now
                    {'limit': 200}
                )
                
                if project_ids:
                    projects = st.session_state.odoo_models.execute_kw(
                        st.session_state.db,
                        st.session_state.odoo_uid,
                        st.session_state.password,
                        model_name,
                        'read',
                        [project_ids],
                        {'fields': ['name', 'display_name']} # Try more generic fields
                    )
                    
                    result['success'] = True
                    result['projects'] = projects
                    result['count'] = len(projects)
                    result['model_used'] = model_name
                    return result
                    
            except Exception as e:
                # This model doesn't exist or we can't access it
                continue
        
        # If we get here, no model worked
        result['error'] = "Could not find project model in Odoo"
            
    except Exception as e:
        result['success'] = False
        result['error'] = str(e)
        
        # Store debug info
        if 'debug_info' not in st.session_state:
            st.session_state.debug_info = {}
        st.session_state.debug_info['project_fetch_error'] = {
            'error': str(e),
            'error_type': type(e).__name__
        }
    
    return result

def find_matching_project(project_name: str, projects: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Find a project that matches the user input
    
    Args:
        project_name: User input project name
        projects: List of project dictionaries
        
    Returns:
        Matching project dictionary or None
    """
    project_name_lower = project_name.lower().strip()
    
    # First try exact match
    for project in projects:
        if project['name'].lower() == project_name_lower:
            return project
        # Also check project code if available
        if project.get('code') and project['code'].lower() == project_name_lower:
            return project
    
    # Then try partial match
    for project in projects:
        if project_name_lower in project['name'].lower():
            return project
        if project.get('code') and project_name_lower in project['code'].lower():
            return project
    
    # Finally try if project name contains the search term
    for project in projects:
        if project['name'].lower() in project_name_lower:
            return project
    
    return None

def create_overtime_request(
        employee_id: int,
        start_datetime: str,
        end_datetime: str,
        project_id: int,
        category_id: int,
        description: str = "",
        employee_name: str = "") -> Dict[str, Any]:
    """
    Create an overtime approval request and push it to the next workflow step.
    """

    result = {
        "success": False,
        "message": "",
        "request_id": None,
        "error": None,
        "debug_info": {}
    }

    try:
        # 0 – Category is now passed in
        if not category_id:
            result["message"] = "Overtime category was not provided."
            return result

        # 1 – Discover which field keeps the workflow status
        fields = st.session_state.odoo_models.execute_kw(
            st.session_state.db, st.session_state.odoo_uid, st.session_state.password,
            "approval.request", "fields_get", [], {"attributes": ["string", "type", "selection"]}
        )
        status_field = next(
            (f for f in ("state", "request_status", "status", "request_state") if f in fields),
            None
        )
        result["debug_info"]["status_field"] = status_field   # for later troubleshooting

        # 2 – Payload
        data = {
            "name": f"Overtime Request - {employee_name}" if employee_name else "Overtime Request",
            "request_owner_id": st.session_state.odoo_uid, 
            "category_id": category_id,
            "date_start": start_datetime,
            "date_end": end_datetime,
            "reason": description or f"Overtime work from {start_datetime} to {end_datetime}",
        }
        for fname in ("x_studio_project", "project_id", "x_project_id", "project"):
            if fname in fields:
                data[fname] = project_id
                result["debug_info"]["project_field_used"] = fname
                break

        # 3 – Create
        req_id = st.session_state.odoo_models.execute_kw(
            st.session_state.db, st.session_state.odoo_uid, st.session_state.password,
            "approval.request", "create", [data]
        )
        result["request_id"] = req_id

        # 4 – Submit (try every common button once)
        submitted = False
        for btn in ("action_confirm", "action_submit", "request_confirm", "button_confirm"):
            try:
                st.session_state.odoo_models.execute_kw(
                    st.session_state.db, st.session_state.odoo_uid, st.session_state.password,
                    "approval.request", btn, [[req_id]]
                )
                submitted = True
                result["debug_info"]["submission_method"] = btn
                break
            except Exception as exc:
                result["debug_info"][f"{btn}_error"] = str(exc)

        # 5 – Read back the final status (if we know the field name)
        if status_field:
            final = st.session_state.odoo_models.execute_kw(
                st.session_state.db, st.session_state.odoo_uid, st.session_state.password,
                "approval.request", "read", [[req_id]], {"fields": [status_field, "name"]}
            )[0]
            result["debug_info"]["final_status"] = final[status_field]

        # 6 – Wrap up
        result["success"] = True
        suffix = "and submitted for approval" if submitted else "but needs manual submission"
        result["message"] = f"Overtime request created (ID {req_id}) {suffix}"
        if not submitted:
            result["needs_manual_submission"] = True

    except Exception as exc:
        result.update(success=False, error=str(exc), message=f"Error creating overtime request: {exc}")

    # keep full trace in Streamlit for easy inspection
    st.session_state.setdefault("debug_info", {})["overtime_creation"] = result["debug_info"]
    return result

def handle_overtime_request(query: str, employee_data: Dict[str, Any]) -> Optional[str]:
    """
    Handle the multi-step process of creating an overtime request.
    This function now uses st.session_state to maintain its state.
    """
    st.session_state.active_workflow = 'overtime_request'
    # Initialize state if it's the first time
    if 'overtime_request' not in st.session_state:
        st.session_state.overtime_request = {}
    
    # Check for cancellation
    if detect_exit_intent_multilingual(query) and st.session_state.overtime_request.get('step'):
        st.session_state.overtime_request = {}  # Clear the state
        st.session_state.active_workflow = None
        return "Overtime request cancelled. How else can I help you?"

    # --- Step 1: Get Overtime Period ---
    if not st.session_state.overtime_request.get('step') or st.session_state.overtime_request.get('step') == 'get_period':
        # This is the first message, which might contain the dates.
        period = parse_overtime_period(query)
        if period['start'] and period['end']:
            # Dates were found, move to next step
            st.session_state.overtime_request = {
                'start_datetime': period['start'],
                'end_datetime': period['end'],
                'step': 'get_category'
            }
            
            categories = get_all_overtime_categories()
            if not categories:
                st.session_state.overtime_request = {} # End flow on error
                return "❌ Could not find any overtime categories. Please contact HR."
            
            st.session_state.overtime_request['available_categories'] = categories
            st.session_state.overtime_request = st.session_state.overtime_request # Save state before asking next question
            
            category_list = "\n".join([f"- {cat['name']}" for cat in categories])
            return f"Great, I have the dates. Now, which overtime category does this fall under?\n\nAvailable categories:\n{category_list}"
        else:
            # No dates found, ask for them.
            st.session_state.overtime_request = {'step': 'get_period'}
            return """I'll help you submit an overtime request. 

Please provide the overtime period in any of these flexible formats:

**Simple formats:**
- from 15/08 09:00 to 15/08 17:00
- tomorrow 9am to 5pm
- today 14:00 to 18:00
- 15-08 9:00 to 15-08 17:00

**Natural language:**
- start 15/08 9am end 15/08 5pm
- work from Aug 15 9:00 until Aug 15 17:00
- overtime 9am-5pm

**Notes:**
- Year defaults to current year if not specified
- Supports both 12h (am/pm) and 24h time formats
- Various date separators accepted: /, -, .
- Flexible keywords: from/to, start/end, begin/finish"""

    elif st.session_state.overtime_request.get('step') == 'get_category':
        available_categories = st.session_state.overtime_request.get('available_categories', [])
        matched_category = next((cat for cat in available_categories if query.lower().strip() in cat['name'].lower()), None)
        
        if matched_category:
            st.session_state.overtime_request.update({
                'category_id': matched_category['id'],
                'category_name': matched_category['name'],
                'step': 'get_project'
            })
            
            projects_result = get_all_projects()
            if not projects_result.get('success') or not projects_result.get('projects'):
                st.session_state.overtime_request = {}
                return f"❌ Error fetching projects: {projects_result.get('error', 'No projects found.')}"
            
            st.session_state.overtime_request['available_projects'] = projects_result.get('projects', [])
            st.session_state.overtime_request = st.session_state.overtime_request
            
            project_list = "\n".join([f"- {p['name']}" for p in projects_result['projects'][:10]])
            return f"""Excellent. The category is set to "{matched_category['name']}".

Now, please select or type the project name. Available projects:\n\n{project_list}\n\nOr type 'show all' to see the full list."""
        else:
            category_list = "\n".join([f"- {cat['name']}" for cat in available_categories])
            return f"I couldn't find a matching category for \"{query}\". Please choose from the list below:\n\n{category_list}"

    elif st.session_state.overtime_request.get('step') == 'get_project':
        available_projects = st.session_state.overtime_request.get('available_projects', [])
        
        # Restore the 'show all' functionality
        if query.lower().strip() == 'show all':
             project_list = "\n".join([f"- {p['name']}" for p in available_projects])
             return f"📋 Here are all the available projects:\n\n{project_list}\n\nPlease type the name of the project you want to select."
        
        matched_project = find_matching_project(query, available_projects)
        if matched_project:
            employee_id = employee_data.get('id')
            if not isinstance(employee_id, int):
                st.session_state.overtime_request = {}
                return "Error: Could not identify the current employee. Please start over."

            # Save needed values before clearing session state
            start_display = st.session_state.overtime_request['start_datetime'].replace('-', '/').replace(' ', ' at ')
            end_display = st.session_state.overtime_request['end_datetime'].replace('-', '/').replace(' ', ' at ')
            category_name = st.session_state.overtime_request.get('category_name', 'N/A')

            # Save start/end before API call and clearing
            saved_start = st.session_state.overtime_request['start_datetime']
            saved_end = st.session_state.overtime_request['end_datetime']

            result = create_overtime_request(
                employee_id,
                saved_start,
                saved_end,
                matched_project['id'],
                st.session_state.overtime_request['category_id'],
                description=f"Overtime for project: {matched_project['name']}",
                employee_name=employee_data.get('name', 'Employee')
            )

            # Compute hours using saved values before clearing
            try:
                start_dt = datetime.strptime(saved_start, "%Y-%m-%d %H:%M:%S")
                end_dt = datetime.strptime(saved_end, "%Y-%m-%d %H:%M:%S")
                overtime_hours_calc = round((end_dt - start_dt).total_seconds() / 3600.0, 2)
            except Exception:
                overtime_hours_calc = 0.0

            st.session_state.overtime_request = {}
            st.session_state.active_workflow = None
            # Restore the detailed, emoji-rich confirmation message
            if result.get('success'):
                # Compute overtime hours from start/end datetimes
                # Track the activity
                track_overtime_request(
                    hours=overtime_hours_calc,
                    date=f"{start_display} to {end_display}",
                    details={
                        'category': category_name,
                        'project': matched_project.get('name', 'N/A'),
                        'request_id': result.get('request_id', 'N/A')
                    }
                )
                
                return f"""✅ {result['message']}

**Overtime Request Details:**
- 📅 Period: {start_display} to {end_display}
- 🏢 Category: {category_name}
- 👷 Project: {matched_project.get('name', 'N/A')}
- 🆔 Request ID: {result.get('request_id', 'N/A')}

Your overtime request has been successfully created and is now pending approval."""
            else:
                return result.get('message', 'An unknown error occurred.')
        else:
            return f"""❌ No matching project found for "{query}". Please type the exact project name or type 'show all' to see the full list."""

    # If we are here, it means we are not in an active overtime flow.
    return None

def diagnose_project_setup():
    """
    Diagnose project setup in Odoo
    """
    diagnosis = {
        'models_found': [],
        'approval_request_fields': [],
        'project_related_fields': []
    }
    
    try:
        # Check what models are available
        models_to_check = ['project.project', 'project.task', 'approval.request']
        
        for model in models_to_check:
            try:
                count = st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    model,
                    'search_count',
                    [[]]
                )
                diagnosis['models_found'].append(f"{model} (count: {count})")
            except:
                diagnosis['models_found'].append(f"{model} (NOT FOUND)")
        
        # Check approval.request fields
        try:
            fields = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'approval.request',
                'fields_get',
                [],
                {'attributes': ['string', 'type', 'relation']}
            )
            
            # Find project-related fields
            for field_name, field_info in fields.items():
                if 'project' in field_name.lower() or 'project' in str(field_info.get('string', '')).lower():
                    diagnosis['project_related_fields'].append({
                        'name': field_name,
                        'type': field_info.get('type'),
                        'string': field_info.get('string'),
                        'relation': field_info.get('relation')
                    })
                    
            diagnosis['approval_request_fields'] = list(fields.keys())[:20]  # First 20 fields
            
        except Exception as e:
            diagnosis['approval_fields_error'] = str(e)
            
    except Exception as e:
        diagnosis['error'] = str(e)
    
    return diagnosis

def diagnose_approval_request_actions():
    """
    Diagnose available actions for approval.request model
    """
    diagnosis = {
        'model_exists': False,
        'available_methods': [],
        'button_actions': [],
        'states': [],
        'sample_request': None
    }
    
    try:
        # Check if model exists
        test = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'approval.request',
            'search',
            [[]],
            {'limit': 1}
        )
        diagnosis['model_exists'] = True
        
        # Get fields
        fields = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'approval.request',
            'fields_get',
            [],
            {'attributes': ['string', 'type', 'selection']}
        )
        
        # Get states
        if 'state' in fields and fields['state'].get('selection'):
            diagnosis['states'] = fields['state']['selection']
        
        # Get form view to find buttons
        try:
            form_view = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'approval.request',
                'fields_view_get',
                [],
                {'view_type': 'form'}
            )
            
            if form_view and 'arch' in form_view:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(form_view['arch'])
                buttons = root.findall(".//button[@name]")
                diagnosis['button_actions'] = [(btn.get('name'), btn.get('string', 'No label')) for btn in buttons]
        except Exception as e:
            diagnosis['form_view_error'] = str(e)
        
        # Get a sample request in "To Submit" state
        if test:
            sample = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'approval.request',
                'read',
                [test],
                {'fields': ['state', 'request_status', 'name']}
            )
            if sample:
                diagnosis['sample_request'] = sample[0]
        
    except Exception as e:
        diagnosis['error'] = str(e)
    
    return diagnosis
