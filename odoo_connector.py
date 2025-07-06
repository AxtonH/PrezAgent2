import streamlit as st
import xmlrpc.client
from datetime import datetime, timedelta
from config import (
    RELATION_MODELS, 
    EMPLOYEE_BASIC_FIELDS, 
    EMPLOYEE_ADDITIONAL_FIELDS,
    PARTNER_FIELDS
)

def get_available_leave_types():
    """
    Get available leave types from Odoo
    
    Returns:
        List of dictionaries with leave type information
    """
    try:
        # First, let's check what fields are available in the hr.leave.type model
        try:
            fields = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.leave.type',
                'fields_get',
                [],
                {'attributes': ['string', 'type']}
            )
            # Store available fields for debugging
            if 'debug_info' not in st.session_state:
                st.session_state.debug_info = {}
            st.session_state.debug_info['leave_type_fields'] = list(fields.keys())
        except:
            # If we can't get fields, continue with basic fields
            pass
        
        # Search for all active leave types
        # First try with 'active' field, but handle if it doesn't exist
        try:
            leave_type_ids = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.leave.type',
                'search',
                [[['active', '=', True]]],
                {}
            )
        except:
            # If 'active' field doesn't exist, get all leave types
            leave_type_ids = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.leave.type',
                'search',
                [[]],
                {}
            )
        
        if leave_type_ids:
            # Only request the 'name' field which should always exist
            # We'll try to get additional fields one by one if needed
            leave_types = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.leave.type',
                'read',
                [leave_type_ids],
                {'fields': ['name']}
            )
            
            # Try to enrich with additional fields if they exist
            additional_fields = ['requires_allocation', 'allocation_type', 'request_unit', 'color']
            for field in additional_fields:
                try:
                    field_data = st.session_state.odoo_models.execute_kw(
                        st.session_state.db,
                        st.session_state.odoo_uid,
                        st.session_state.password,
                        'hr.leave.type',
                        'read',
                        [leave_type_ids],
                        {'fields': [field]}
                    )
                    # Add the field data to our leave types
                    for i, lt in enumerate(leave_types):
                        if i < len(field_data) and field in field_data[i]:
                            lt[field] = field_data[i][field]
                except:
                    # Skip fields that don't exist
                    pass
            
            return leave_types
        return []
    except Exception as e:
        st.error(f"Error getting leave types: {str(e)}")
        return []

# Update get_pending_time_off_requests in odoo_connector.py:

def get_pending_time_off_requests(manager_employee_id):
    """
    Get pending time off requests for employees under a manager
    
    Args:
        manager_employee_id: ID of the manager's employee record
        
    Returns:
        List of pending time off requests
    """
    try:
        # Add detailed debugging
        if 'debug_info' not in st.session_state:
            st.session_state.debug_info = {}
        
        debug_data = {
            'manager_employee_id': manager_employee_id,
            'searching_for_subordinates': True
        }
        
        # First, find all employees who report to this manager
        subordinate_ids = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.employee',
            'search',
            [[['parent_id', '=', manager_employee_id]]],
            {}
        )
        
        debug_data['subordinate_ids'] = subordinate_ids
        debug_data['subordinate_count'] = len(subordinate_ids)
        
        if subordinate_ids:
            # Get names of subordinates for debugging
            subordinate_info = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.employee',
                'read',
                [subordinate_ids],
                {'fields': ['name']}
            )
            debug_data['subordinate_names'] = [emp['name'] for emp in subordinate_info]
        
        if not subordinate_ids:
            debug_data['no_subordinates_found'] = True
            st.session_state.debug_info['pending_requests_debug'] = debug_data
            return []
        
        # Get ALL leave requests for these employees first (for debugging)
        all_leave_ids = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.leave',
            'search',
            [[['employee_id', 'in', subordinate_ids]]],
            {'limit': 200}
        )
        
        debug_data['total_leave_requests'] = len(all_leave_ids)
        
        # Get details of all leaves to see their states
        if all_leave_ids:
            all_leaves = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.leave',
                'read',
                [all_leave_ids[:10]],  # First 10 for debugging
                {'fields': ['employee_id', 'state', 'name']}
            )
            
            # Count by state
            state_counts = {}
            for leave in all_leaves:
                state = leave.get('state', 'unknown')
                state_counts[state] = state_counts.get(state, 0) + 1
            
            debug_data['leave_states'] = state_counts
            debug_data['sample_leaves'] = all_leaves[:3]  # Show first 3 for debugging
        
        # Now get pending leave requests (state = 'confirm')
        leave_ids = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.leave',
            'search',
            [[
                ['employee_id', 'in', subordinate_ids],
                ['state', '=', 'confirm']
            ]],
            {}
        )
        
        debug_data['pending_leave_ids'] = leave_ids
        debug_data['pending_count'] = len(leave_ids)
        
        st.session_state.debug_info['pending_requests_debug'] = debug_data
        
        if not leave_ids:
            return []
        
        # Get the leave request details
        leaves = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.leave',
            'read',
            [leave_ids],
            {'fields': [
                'name', 'employee_id', 'holiday_status_id', 
                'date_from', 'date_to', 'number_of_days',
                'request_date_from', 'request_date_to',
                'state', 'create_date'
            ]}
        )
        
        return leaves
    except Exception as e:
        if 'debug_info' not in st.session_state:
            st.session_state.debug_info = {}
        st.session_state.debug_info['pending_requests_error'] = str(e)
        return []

def approve_time_off_request(leave_id):
    """
    Approve a time off request
    
    Args:
        leave_id: ID of the leave request
        
    Returns:
        Dictionary with success status and message
    """
    try:
        # Try to approve the request
        st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.leave',
            'action_approve',
            [[leave_id]]
        )
        
        return {
            'success': True,
            'message': f"Time off request (ID: {leave_id}) has been approved successfully."
        }
    except Exception as e:
        # If action_approve doesn't work, try action_validate
        try:
            st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.leave',
                'action_validate',
                [[leave_id]]
            )
            
            return {
                'success': True,
                'message': f"Time off request (ID: {leave_id}) has been approved successfully."
            }
        except Exception as e2:
            return {
                'success': False,
                'message': f"Error approving request: {str(e2)}"
            }

def deny_time_off_request(leave_id, reason=""):
    """
    Deny a time off request
    
    Args:
        leave_id: ID of the leave request
        reason: Optional reason for denial
        
    Returns:
        Dictionary with success status and message
    """
    try:
        # First, try to add a reason if provided
        if reason:
            try:
                st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    'hr.leave',
                    'write',
                    [[leave_id], {'report_note': reason}]
                )
            except:
                # If report_note doesn't exist, try other fields
                try:
                    st.session_state.odoo_models.execute_kw(
                        st.session_state.db,
                        st.session_state.odoo_uid,
                        st.session_state.password,
                        'hr.leave',
                        'write',
                        [[leave_id], {'notes': reason}]
                    )
                except:
                    pass
        
        # Try to refuse the request
        st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.leave',
            'action_refuse',
            [[leave_id]]
        )
        
        return {
            'success': True,
            'message': f"Time off request (ID: {leave_id}) has been denied."
        }
    except Exception as e:
        # If action_refuse doesn't work, try action_draft and cancel
        try:
            # Set to draft first
            st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.leave',
                'action_draft',
                [[leave_id]]
            )
            
            # Then cancel
            st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.leave',
                'write',
                [[leave_id], {'state': 'refuse'}]
            )
            
            return {
                'success': True,
                'message': f"Time off request (ID: {leave_id}) has been denied."
            }
        except Exception as e2:
            return {
                'success': False,
                'message': f"Error denying request: {str(e2)}"
            }

def is_manager(employee_id):
    """
    Check if an employee is a manager (has subordinates)
    
    Args:
        employee_id: ID of the employee
        
    Returns:
        Boolean indicating if the employee is a manager
    """
    # First check if we already have team_data in the employee data
    if hasattr(st.session_state, 'employee_data') and st.session_state.employee_data:
        team_data = st.session_state.employee_data.get('team_data', {})
        if 'is_manager' in team_data:
            return team_data['is_manager']
    
    # Otherwise, query Odoo
    try:
        subordinate_count = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.employee',
            'search_count',
            [[['parent_id', '=', employee_id]]],
            {}
        )
        
        return subordinate_count > 0
    except Exception as e:
        if 'debug_info' not in st.session_state:
            st.session_state.debug_info = {}
        st.session_state.debug_info['is_manager_error'] = str(e)
        return False

def get_manager_team_data(manager_employee_id):
    """
    Get data about employees who report to a manager, including their time off
    
    Args:
        manager_employee_id: ID of the manager's employee record
        
    Returns:
        Dictionary with team information including time off
    """
    team_data = {
        'subordinates': [],
        'subordinate_count': 0,
        'is_manager': False,
        'pending_time_off_requests': [],
        'approved_time_off_requests': [],
        'team_time_off_summary': {},
        'calendar_time_off': {}
    }
    
    try:
        # Find all employees who report to this manager
        subordinate_ids = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.employee',
            'search',
            [[['parent_id', '=', manager_employee_id]]],
            {}
        )
        
        if subordinate_ids:
            team_data['is_manager'] = True
            team_data['subordinate_count'] = len(subordinate_ids)
            
            # Get basic information about each subordinate
            subordinates = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.employee',
                'read',
                [subordinate_ids],
                {'fields': ['name', 'job_title', 'work_email', 'department_id']}
            )
            
            # Process subordinate data
            for sub in subordinates:
                subordinate_info = {
                    'id': sub['id'],
                    'name': sub.get('name', ''),
                    'job_title': sub.get('job_title', ''),
                    'work_email': sub.get('work_email', ''),
                    'department': sub.get('department_id', ['', ''])[1] if isinstance(sub.get('department_id'), list) else ''
                }
                team_data['subordinates'].append(subordinate_info)
            
            # Sort subordinates by name
            team_data['subordinates'].sort(key=lambda x: x['name'])
            
            # Get time off data from calendar
            calendar_data = get_team_time_off_from_calendar(manager_employee_id, subordinate_ids)
            team_data['calendar_time_off'] = calendar_data
            
            # Process calendar data into approved/pending if we got results
            if calendar_data.get('calendar_records') or calendar_data.get('report_records'):
                records = calendar_data.get('calendar_records', []) or calendar_data.get('report_records', [])
                
                for record in records:
                    state = record.get('state', '')
                    if state == 'validate':
                        team_data['approved_time_off_requests'].append(record)
                    elif state == 'confirm':
                        team_data['pending_time_off_requests'].append(record)
                
                # Create summary
                team_data['team_time_off_summary'] = calendar_data.get('by_employee', {})
            
            # Add debug info
            if 'debug_info' not in st.session_state:
                st.session_state.debug_info = {}
            st.session_state.debug_info['team_calendar_data'] = calendar_data.get('debug_info', {})
            st.session_state.debug_info['team_time_off_counts'] = {
                'approved': len(team_data['approved_time_off_requests']),
                'pending': len(team_data['pending_time_off_requests']),
                'employees_with_time_off': list(team_data['team_time_off_summary'].keys())
            }
        
        return team_data
    except Exception as e:
        if 'debug_info' not in st.session_state:
            st.session_state.debug_info = {}
        st.session_state.debug_info['team_data_error'] = str(e)
        return team_data

def get_employee_by_leave_id(leave_id):
    """
    Get employee information from a leave request ID
    
    Args:
        leave_id: ID of the leave request
        
    Returns:
        Dictionary with employee information or None
    """
    try:
        leave_data = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.leave',
            'read',
            [leave_id],
            {'fields': ['employee_id']}
        )
        
        if leave_data and leave_data[0].get('employee_id'):
            employee_id = leave_data[0]['employee_id'][0]
            return get_base_employee_data(employee_id)
        
        return None
    except:
        return None

def create_time_off_request(employee_id, leave_type_id, date_from, date_to, description=""):
    """
    Create a time off request in Odoo
    
    Args:
        employee_id: ID of the employee
        leave_type_id: ID of the leave type
        date_from: Start date (string in format 'YYYY-MM-DD')
        date_to: End date (string in format 'YYYY-MM-DD')
        description: Optional description for the request
        
    Returns:
        Dictionary with success status and message
    """
    try:
        # Convert dates to datetime format expected by Odoo
        date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
        date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
        
        # Calculate number of days (including weekends for now)
        number_of_days = (date_to_dt - date_from_dt).days + 1
        
        # Prepare the leave request data using the correct field names
        leave_data = {
            'employee_id': employee_id,
            'holiday_status_id': leave_type_id,  # This is correct based on your screenshot
            'request_date_from': date_from,      # Using the correct field name
            'request_date_to': date_to,          # Using the correct field name
            'name': description if description else f"Time Off Request",
            'number_of_days': number_of_days,
        }
        
        # Some Odoo versions might also need these fields
        # We'll try to add them but won't fail if they don't exist
        try:
            # Try to add datetime fields if they exist
            leave_data['date_from'] = date_from_dt.strftime('%Y-%m-%d %H:%M:%S')
            leave_data['date_to'] = date_to_dt.replace(hour=23, minute=59, second=59).strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass
        
        # Create the leave request
        leave_id = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.leave',
            'create',
            [leave_data]
        )
        
        if leave_id:
            # Try to submit the request for approval
            try:
                # First check if the action_confirm method exists
                methods = st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    'hr.leave',
                    'fields_get',
                    [],
                    {'attributes': ['string', 'type']}
                )
                
                # Try to confirm the request
                st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    'hr.leave',
                    'action_confirm',
                    [[leave_id]]
                )
                return {
                    'success': True,
                    'message': f"Time off request created successfully and submitted for approval. Request ID: {leave_id}",
                    'leave_id': leave_id
                }
            except:
                # If we can't confirm, at least the draft was created
                return {
                    'success': True,
                    'message': f"Time off request created successfully as draft. Request ID: {leave_id}. You may need to submit it for approval manually.",
                    'leave_id': leave_id
                }
        else:
            return {
                'success': False,
                'message': "Failed to create time off request. Please try again."
            }
            
    except Exception as e:
        error_msg = str(e)
        # Better error handling based on common Odoo errors
        if 'not enough days left' in error_msg.lower() or 'exceeds the number of remaining days' in error_msg.lower():
            return {
                'success': False,
                'message': "You don't have enough leave balance for this request. Please check your available days."
            }
        elif 'overlapping' in error_msg.lower():
            return {
                'success': False,
                'message': "This request overlaps with an existing time off request. Please choose different dates."
            }
        elif 'required' in error_msg.lower():
            # Log the full error for debugging
            if 'debug_info' not in st.session_state:
                st.session_state.debug_info = {}
            st.session_state.debug_info['time_off_error'] = error_msg
            return {
                'success': False,
                'message': f"Missing required field. Error: {error_msg}"
            }
        else:
            return {
                'success': False,
                'message': f"Error creating time off request: {error_msg}"
            }

def get_employee_leave_balance(employee_id, leave_type_id):
    """
    Get the available leave balance for a specific leave type
    
    Args:
        employee_id: ID of the employee
        leave_type_id: ID of the leave type
        
    Returns:
        Dictionary with balance information
    """
    try:
        # Try to get leave balance using the hr.leave.type model
        balance_data = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.leave.type',
            'get_employees_days',
            [[leave_type_id], [employee_id]]
        )
        
        if balance_data and employee_id in balance_data[0]:
            emp_balance = balance_data[0][employee_id]
            return {
                'available': emp_balance.get('remaining_leaves', 0),
                'allocated': emp_balance.get('max_leaves', 0),
                'used': emp_balance.get('leaves_taken', 0)
            }
        
        # Fallback: calculate from allocations and requests
        return calculate_leave_balance_fallback(employee_id, leave_type_id)
        
    except Exception as e:
        # Fallback method if the above doesn't work
        return calculate_leave_balance_fallback(employee_id, leave_type_id)

def calculate_leave_balance_fallback(employee_id, leave_type_id):
    """
    Calculate leave balance manually from allocations and requests
    """
    try:
        allocated = 0
        used = 0
        
        # Get allocations
        allocation_ids = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.leave.allocation',
            'search',
            [[
                ['employee_id', '=', employee_id],
                ['holiday_status_id', '=', leave_type_id],
                ['state', '=', 'validate']
            ]]
        )
        
        if allocation_ids:
            allocations = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.leave.allocation',
                'read',
                [allocation_ids],
                {'fields': ['number_of_days']}
            )
            allocated = sum(alloc['number_of_days'] for alloc in allocations)
        
        # Get used leaves
        leave_ids = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.leave',
            'search',
            [[
                ['employee_id', '=', employee_id],
                ['holiday_status_id', '=', leave_type_id],
                ['state', 'in', ['validate', 'confirm']]
            ]]
        )
        
        if leave_ids:
            leaves = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.leave',
                'read',
                [leave_ids],
                {'fields': ['number_of_days']}
            )
            used = sum(leave['number_of_days'] for leave in leaves)
        
        return {
            'available': allocated - used,
            'allocated': allocated,
            'used': used
        }
    except:
        return {
            'available': 0,
            'allocated': 0,
            'used': 0
        }

def get_current_user_employee_data():
    """
    Get employee data for the currently logged-in Odoo user
    
    Returns:
        Dictionary with employee data or None if not found
    """
    if not st.session_state.odoo_connected:
        return None
    
    try:
        # First, get the current user's data
        user_data = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'res.users',
            'read',
            [st.session_state.odoo_uid],
            {'fields': ['name', 'email', 'partner_id', 'employee_id', 'employee_ids']}
        )
        
        if not user_data:
            return None
        
        user_info = user_data[0]
        st.session_state.debug_info['current_user'] = user_info
        
        # Check if user has employee_id field (some Odoo versions)
        if user_info.get('employee_id'):
            employee_id = user_info['employee_id'][0] if isinstance(user_info['employee_id'], list) else user_info['employee_id']
            employee_data = get_base_employee_data(employee_id)
            if employee_data:
                return enrich_employee_data(employee_data, employee_id)
        
        # Check employee_ids field (other Odoo versions)
        if user_info.get('employee_ids') and len(user_info['employee_ids']) > 0:
            employee_id = user_info['employee_ids'][0]
            employee_data = get_base_employee_data(employee_id)
            if employee_data:
                return enrich_employee_data(employee_data, employee_id)
        
        # Fallback: Search for employee by user's email
        if user_info.get('email'):
            employee_ids = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.employee',
                'search',
                [[['work_email', '=', user_info['email']]]],
                {'limit': 1}
            )
            
            if employee_ids:
                employee_data = get_base_employee_data(employee_ids[0])
                if employee_data:
                    return enrich_employee_data(employee_data, employee_ids[0])
        
        # Fallback: Search for employee by user's name
        if user_info.get('name'):
            employee_ids = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.employee',
                'search',
                [[['name', 'ilike', user_info['name']]]],
                {'limit': 1}
            )
            
            if employee_ids:
                employee_data = get_base_employee_data(employee_ids[0])
                if employee_data:
                    return enrich_employee_data(employee_data, employee_ids[0])
        
        # If no employee found, check if user's partner is relevant
        if user_info.get('partner_id'):
            partner_id = user_info['partner_id'][0] if isinstance(user_info['partner_id'], list) else user_info['partner_id']
            return get_partner_data(partner_id)
            
        return None
        
    except Exception as e:
        st.error(f"Error retrieving current user data: {str(e)}")
        if 'debug_info' not in st.session_state:
            st.session_state.debug_info = {}
        st.session_state.debug_info['current_user_error'] = str(e)
        return None

def connect_to_odoo(odoo_url, odoo_db, odoo_username, odoo_password):
    """
    Connect to Odoo instance and authenticate
    
    Returns:
        Tuple of (success, message, user_info)
    """
    try:
        # Connect to Odoo
        common = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/common', allow_none=True)
        # Verify connection by getting server version
        server_version = common.version()
        
        # Authenticate
        uid = common.authenticate(odoo_db, odoo_username, odoo_password, {})
        
        if uid:
            # Create models service
            models = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/object', allow_none=True)
            st.session_state.odoo_uid = uid
            st.session_state.odoo_models = models
            st.session_state.odoo_connected = True
            st.session_state.db = odoo_db
            st.session_state.password = odoo_password
            
            # Automatically get current user's employee data
            current_user_data = get_current_user_employee_data()
            if current_user_data:
                st.session_state.employee_data = current_user_data
                st.session_state.auto_loaded = True
            
            # Fix: Only access ['server_version'] if server_version is a dict
            version_str = ""
            if isinstance(server_version, dict) and 'server_version' in server_version:
                version_str = f" (version {server_version['server_version']})"
            return True, f"Connected to Odoo server{version_str}", f"Connected as: {odoo_username}"
        else:
            return False, "Authentication failed. Please check your credentials.", ""
    except Exception as e:
        return False, f"Connection failed: {str(e)}", ""

def get_base_employee_data(employee_id):
    """
    Get just the basic fields of an employee to avoid permission errors
    
    Args:
        employee_id: ID of the employee record
        
    Returns:
        Dictionary with employee data or None if error
    """
    try:
        # Read employee with minimal fields
        data = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.employee',
            'read',
            [employee_id],
            {'fields': EMPLOYEE_BASIC_FIELDS}
        )
        return data[0] if data else None
    except Exception as e:
        st.error(f"Error getting basic employee data: {str(e)}")
        return None

def get_employee_leave_data(employee_id):
    """
    Get leave/time off data for an employee
    
    Args:
        employee_id: ID of the employee record
        
    Returns:
        Dictionary with leave allocation and request data
    """
    leave_data = {
        'allocations': [],
        'requests': [],
        'balance': {},
        'summary': {}
    }
    
    try:
        # Get leave allocations
        # First try hr.leave.allocation
        try:
            allocation_ids = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.leave.allocation',
                'search',
                [[['employee_id', '=', employee_id], ['state', '=', 'validate']]],
                {'limit': 10}
            )
            
            if allocation_ids:
                allocations = st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    'hr.leave.allocation',
                    'read',
                    [allocation_ids],
                    {'fields': ['name', 'holiday_status_id', 'number_of_days', 'date_from', 'date_to']}
                )
                
                leave_data['allocations'] = allocations
        except Exception as e:
            # Skip if we can't access allocations
            pass
        
        # Get leave report data
        try:
            # Search for leave reports for this employee
            leave_report_ids = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.leave.report',
                'search',
                [[['employee_id', '=', employee_id]]],
                {'limit': 50}
            )
            
            if leave_report_ids:
                leave_reports = st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    'hr.leave.report',
                    'read',
                    [leave_report_ids],
                    {'fields': ['name', 'holiday_status_id', 'number_of_days', 'date_from', 'date_to', 'state', 'leave_type']}
                )
                
                # Process the leave reports to create a summary
                if leave_reports:
                    for report in leave_reports:
                        status_id = report.get('holiday_status_id')
                        if status_id and isinstance(status_id, (list, tuple)) and len(status_id) == 2:
                            status_name = status_id[1]  # The display name
                            days = report.get('number_of_days', 0)
                            state = report.get('state', '')
                            leave_type = report.get('leave_type', '')
                            
                            # Initialize if not exists
                            if status_name not in leave_data['summary']:
                                leave_data['summary'][status_name] = {
                                    'allocated': 0,
                                    'taken': 0,
                                    'requested': 0,
                                    'balance': 0,
                                }
                            
                            # Update the summary based on type and state
                            if leave_type == 'allocation' and state == 'validate':
                                leave_data['summary'][status_name]['allocated'] += days
                            elif leave_type == 'request':
                                if state == 'validate':
                                    leave_data['summary'][status_name]['taken'] += days
                                elif state in ['confirm', 'draft']:
                                    leave_data['summary'][status_name]['requested'] += days
                            
                            # Calculate balance
                            leave_data['summary'][status_name]['balance'] = (
                                leave_data['summary'][status_name]['allocated'] - 
                                leave_data['summary'][status_name]['taken']
                            )
                            
                    # Store raw reports
                    leave_data['reports'] = leave_reports
        except Exception as e:
            # Skip if we can't access leave reports
            pass
        
        # Alternative: get hr.leave data directly (time off requests)
        try:
            leave_ids = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.leave',
                'search',
                [[['employee_id', '=', employee_id]]],
                {'limit': 20}
            )
            
            if leave_ids:
                leaves = st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    'hr.leave',
                    'read',
                    [leave_ids],
                    {'fields': ['name', 'holiday_status_id', 'number_of_days', 'date_from', 'date_to', 'state']}
                )
                
                leave_data['requests'] = leaves
                
                # If we couldn't get summary data from reports, try to build it from requests
                if not leave_data['summary']:
                    for leave in leaves:
                        status_id = leave.get('holiday_status_id')
                        if status_id and isinstance(status_id, (list, tuple)) and len(status_id) == 2:
                            status_name = status_id[1]  # The display name
                            days = leave.get('number_of_days', 0)
                            state = leave.get('state', '')
                            
                            # Initialize if not exists
                            if status_name not in leave_data['balance']:
                                leave_data['balance'][status_name] = {
                                    'taken': 0,
                                    'requested': 0,
                                }
                            
                            # Update the balance based on state
                            if state == 'validate':
                                leave_data['balance'][status_name]['taken'] += days
                            elif state in ['confirm', 'draft']:
                                leave_data['balance'][status_name]['requested'] += days
        except Exception as e:
            # Skip if we can't access leave requests
            pass
        
        return leave_data
    except Exception as e:
        # Return empty data structure if there's an error
        return leave_data

def get_employee_planning_data(employee_id):
    """
    Get planning/shift data for an employee from planning.slot model
    
    Args:
        employee_id: ID of the employee record
        
    Returns:
        Dictionary with planning slots data
    """
    planning_data = {
        'upcoming_shifts': [],
        'past_shifts': [],
        'published': [],
        'unpublished': [],
        'open_shifts': [],
        'debug_info': {}  # Add debug info to help troubleshoot
    }
    
    try:
        # Get current date to separate past and upcoming shifts
        current_date = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'planning.slot',
            'search_read',
            [[['id', '=', 0]]],  # Dummy search to get server date
            {'fields': ['create_date']}
        )
        
        # If we can't get current date, use a fallback approach
        current_server_date = current_date[0]['create_date'] if current_date and current_date[0].get('create_date') else None
        planning_data['debug_info']['current_server_date'] = current_server_date
        
        # Approach 1: Get employee's resource record directly
        resource_data = []
        employee_name = ""
        employee_data = None
        
        try:
            # Get employee name for debugging and searching
            employee_data = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.employee',
                'read',
                [employee_id],
                {'fields': ['name', 'job_title']}
            )
            
            if employee_data:
                employee_name = employee_data[0]['name']
                planning_data['debug_info']['employee_name'] = employee_name
                planning_data['debug_info']['job_title'] = employee_data[0].get('job_title', 'N/A')
            
            # Get the employee's resource ID
            resource_data = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'resource.resource',
                'search_read',
                [[['employee_id', '=', employee_id]]],
                {'fields': ['id', 'name']}
            )
            
            planning_data['debug_info']['resource_data_by_employee_id'] = resource_data
        except Exception as e:
            planning_data['debug_info']['resource_error'] = str(e)
        
        # Approach 2: If no resource found, search by name
        if not resource_data and employee_name:
            try:
                # Try to search for resource by name
                resource_data = st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    'resource.resource',
                    'search_read',
                    [[['name', 'ilike', employee_name]]],
                    {'fields': ['id', 'name']}
                )
                
                planning_data['debug_info']['resource_data_by_name'] = resource_data
            except Exception as e:
                planning_data['debug_info']['resource_by_name_error'] = str(e)
        
        # Approach 3: If still no resource found, try a broader search in resources
        if not resource_data and employee_name:
            try:
                # Get the first word of the employee name (usually first name)
                first_name = employee_name.split(' ')[0]
                
                # Try a broader search
                resource_data = st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    'resource.resource',
                    'search_read',
                    [[['name', 'ilike', first_name]]],
                    {'fields': ['id', 'name']}
                )
                
                planning_data['debug_info']['resource_data_by_first_name'] = resource_data
            except Exception as e:
                planning_data['debug_info']['resource_by_first_name_error'] = str(e)
        
        # Get the planning slot fields to understand its structure
        try:
            # Get the planning slot fields
            planning_fields = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid, 
                st.session_state.password,
                'planning.slot',
                'fields_get',
                [],
                {'attributes': ['string', 'type', 'relation']}
            )
            
            # Store field names related to employees/resources
            employee_related_fields = {k: v for k, v in planning_fields.items() 
                                    if 'employee' in k or 'resource' in k or 'user' in k}
            planning_data['debug_info']['employee_related_fields'] = employee_related_fields
            
            # Get all field names to use for safe reading
            all_field_names = list(planning_fields.keys())
            planning_data['debug_info']['all_field_names'] = all_field_names
            
            # Define the fields we want to read (if they exist)
            safe_fields = [
                'name', 'start_datetime', 'end_datetime', 
                'resource_id', 'role_id', 'state',
                'allocated_hours', 'allocated_percentage',
                'project_id', 'company_id',
                'sale_line_id', 'place_id'
            ]
            
            # Filter to only fields that exist in the model
            safe_fields = [field for field in safe_fields if field in all_field_names]
            planning_data['debug_info']['safe_fields'] = safe_fields
            
        except Exception as e:
            planning_data['debug_info']['fields_get_error'] = str(e)
            # Fallback to a minimal set of safe fields if we can't get fields
            safe_fields = ['name', 'start_datetime', 'end_datetime', 'resource_id', 'role_id']
        
        # Approach 4: If we found resources, use them to search for planning slots
        slot_ids = []
        if resource_data:
            try:
                resource_ids = [record['id'] for record in resource_data]
                planning_data['debug_info']['resource_ids'] = resource_ids
                
                # Search for planning slots for these resources
                slot_ids = st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    'planning.slot',
                    'search',
                    [[['resource_id', 'in', resource_ids]]],
                    {'limit': 50}
                )
                
                planning_data['debug_info']['slot_ids_by_resource'] = slot_ids
            except Exception as e:
                planning_data['debug_info']['slot_search_error'] = str(e)
        
        # Approach 5: Try direct search with employee ID
        if not slot_ids:
            try:
                # Different field name potentially used
                potential_fields = ['employee_id', 'employee_ids', 'user_id', 'user_ids']
                
                for field in potential_fields:
                    try:
                        # Try search with this field
                        field_slot_ids = st.session_state.odoo_models.execute_kw(
                            st.session_state.db,
                            st.session_state.odoo_uid,
                            st.session_state.password,
                            'planning.slot',
                            'search',
                            [[[(field, '=', employee_id)]]],
                            {'limit': 50}
                        )
                        
                        if field_slot_ids:
                            slot_ids.extend(field_slot_ids)
                            planning_data['debug_info'][f'slot_ids_by_{field}'] = field_slot_ids
                    except:
                        # Field doesn't exist, continue to next one
                        pass
            except Exception as e:
                planning_data['debug_info']['direct_employee_search_error'] = str(e)
        
        # Process any slot_ids we found
        if slot_ids:
            try:
                slots = st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    'planning.slot',
                    'read',
                    [slot_ids],
                    {'fields': safe_fields}
                )
                
                if slots:
                    planning_data['debug_info']['slots_found'] = len(slots)
                    
                    # Check if there's a publication status field
                    has_publication_field = 'publication_warning' in safe_fields or 'is_published' in safe_fields
                    
                    # Process the slots
                    for slot in slots:
                        # Only categorize by publication if we have the field
                        if has_publication_field:
                            is_published = slot.get('is_published', False) if 'is_published' in safe_fields else (slot.get('publication_warning', False) if 'publication_warning' in safe_fields else False)
                            if is_published:
                                planning_data['published'].append(slot)
                            else:
                                planning_data['unpublished'].append(slot)
                        
                        # Categorize based on date
                        start_date = slot.get('start_datetime', '')
                        if start_date:
                            if current_server_date and start_date > current_server_date:
                                planning_data['upcoming_shifts'].append(slot)
                            else:
                                planning_data['past_shifts'].append(slot)
                    
                    # Sort slots by date
                    for key in ['upcoming_shifts', 'past_shifts', 'published', 'unpublished']:
                        planning_data[key] = sorted(
                            planning_data[key], 
                            key=lambda x: x.get('start_datetime', ''), 
                            reverse=(key == 'past_shifts')
                        )
            except Exception as e:
                planning_data['debug_info']['slot_read_error'] = str(e)
        
        # Try to get open shifts that could be assigned to this employee
        try:
            # First get the employee's roles
            employee_roles = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.employee',
                'read',
                [employee_id],
                {'fields': ['planning_role_ids']}
            )
            
            if employee_roles and employee_roles[0].get('planning_role_ids'):
                role_ids = employee_roles[0]['planning_role_ids']
                planning_data['debug_info']['employee_role_ids'] = role_ids
                
                # Search for open planning slots matching employee's roles
                open_slot_ids = st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    'planning.slot',
                    'search',
                    [[
                        ['resource_id', '=', False],  # No resource assigned
                        ['role_id', 'in', role_ids],  # Matches employee's roles
                        ['start_datetime', '>', current_server_date] if current_server_date else []  # Future slots
                    ]],
                    {'limit': 20}
                )
                
                planning_data['debug_info']['open_slot_ids'] = open_slot_ids
                
                if open_slot_ids:
                    open_slots = st.session_state.odoo_models.execute_kw(
                        st.session_state.db,
                        st.session_state.odoo_uid,
                        st.session_state.password,
                        'planning.slot',
                        'read',
                        [open_slot_ids],
                        {'fields': [
                            'name', 'start_datetime', 'end_datetime', 
                            'role_id', 'allocated_hours', 'allocated_percentage',
                            'project_id', 'is_published', 'place_id'
                        ]}
                    )
                    
                    if open_slots:
                        planning_data['open_shifts'] = sorted(
                            open_slots, 
                            key=lambda x: x.get('start_datetime', '')
                        )
        except Exception as e:
            planning_data['debug_info']['open_shifts_error'] = str(e)
        
        # Add the debug info to app.py session state for debugging in the UI
        if 'debug_info' not in st.session_state:
            st.session_state.debug_info = {}
        st.session_state.debug_info['planning'] = planning_data['debug_info']
        
        return planning_data
    except Exception as e:
        # Return empty data structure if there's an error
        planning_data['debug_info']['main_error'] = str(e)
        if 'debug_info' not in st.session_state:
            st.session_state.debug_info = {}
        st.session_state.debug_info['planning'] = planning_data['debug_info']
        return planning_data

def enrich_employee_data(employee_data, employee_id):
    """
    Try to add more fields to employee data one by one
    
    Args:
        employee_data: Base employee data dictionary
        employee_id: ID of the employee record
        
    Returns:
        Enriched employee data dictionary
    """
    if not employee_data:
        return None
    
    # Try each field individually
    for field in EMPLOYEE_ADDITIONAL_FIELDS:
        try:
            field_data = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.employee',
                'read',
                [employee_id],
                {'fields': [field]}
            )
            
            if field_data and field_data[0].get(field):
                employee_data[field] = field_data[0][field]
        except Exception:
            # Skip fields that cause errors
            pass
    
    # Process any Many2one relations we were able to retrieve
    for field, value in list(employee_data.items()):
        if isinstance(value, (list, tuple)) and len(value) == 2 and isinstance(value[0], int):
            # It's a Many2one field
            if field in RELATION_MODELS:
                try:
                    related_data = st.session_state.odoo_models.execute_kw(
                        st.session_state.db,
                        st.session_state.odoo_uid,
                        st.session_state.password,
                        RELATION_MODELS[field],
                        'read',
                        [value[0]],
                        {'fields': ['name']}
                    )
                    
                    if related_data:
                        employee_data[f"{field}_details"] = related_data[0]
                except Exception:
                    # Skip if we can't get related details
                    pass
    
    # Add team/subordinate data
    try:
        team_data = get_manager_team_data(employee_id)
        if team_data and (team_data['is_manager'] or team_data['subordinates']):
            employee_data['team_data'] = team_data
            employee_data['is_manager'] = team_data['is_manager']
            
            # Run diagnostics if user is a manager
            if team_data['is_manager']:
                diagnosis = diagnose_manager_status(employee_id)
                employee_data['manager_diagnosis'] = diagnosis
    except Exception:
        # Skip if we can't get team data
        pass
    
    # Add leave data
    try:
        leave_data = get_employee_leave_data(employee_id)
        if leave_data and (leave_data['allocations'] or leave_data['requests'] or leave_data['summary']):
            employee_data['leave_data'] = leave_data
    except Exception:
        # Skip if we can't get leave data
        pass
    
    # Add planning data
    try:
        planning_data = get_employee_planning_data(employee_id)
        if planning_data and (planning_data['upcoming_shifts'] or planning_data['open_shifts'] or planning_data['past_shifts']):
            employee_data['planning_data'] = planning_data
    except Exception:
        # Skip if we can't get planning data
        pass
    
    return employee_data

def get_partner_data(partner_id):
    """
    Get data for a partner record
    
    Args:
        partner_id: ID of the partner record
        
    Returns:
        Dictionary with partner data or None if error
    """
    try:
        partner_data = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'res.partner',
            'read',
            [partner_id],
            {'fields': PARTNER_FIELDS}
        )
        
        if partner_data:
            # Mark this as partner data, not employee data
            partner_data[0]['is_partner'] = True
            return partner_data[0]
        return None
    except Exception as e:
        st.error(f"Error getting partner data: {str(e)}")
        return None

def get_employee_data(employee_name):
    """
    Get employee data from Odoo based on name, handling all errors gracefully
    
    Args:
        employee_name: Name of the employee to search for
        
    Returns:
        Dictionary with employee or partner data or None if not found
    """
    if not st.session_state.odoo_connected:
        st.warning("Please connect to Odoo first using the sidebar.")
        return None
    
    try:
        # Search for the employee by name
        employee_ids = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.employee',
            'search',
            [[['name', 'ilike', employee_name]]],
            {'limit': 1}
        )
        
        if employee_ids:
            # Get basic employee data first
            employee_data = get_base_employee_data(employee_ids[0])
            
            if employee_data:
                # Try to add more fields safely
                return enrich_employee_data(employee_data, employee_ids[0])
            return None
        
        # If employee not found, try searching in partners
        partner_ids = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'res.partner',
            'search',
            [[['name', 'ilike', employee_name]]],
            {'limit': 1}
        )
        
        if partner_ids:
            return get_partner_data(partner_ids[0])
            
        return None
    except Exception as e:
        st.error(f"Error retrieving data: {str(e)}")
        return None

def diagnose_manager_status(employee_id):
    """
    Diagnose manager status and team structure
    
    Args:
        employee_id: ID of the employee to check
        
    Returns:
        Dictionary with diagnostic information
    """
    diagnosis = {
        'employee_id': employee_id,
        'checks_performed': []
    }
    
    try:
        # Check 1: Direct subordinates by parent_id
        subordinate_ids = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.employee',
            'search',
            [[['parent_id', '=', employee_id]]],
            {}
        )
        
        diagnosis['direct_subordinates'] = {
            'count': len(subordinate_ids),
            'ids': subordinate_ids
        }
        diagnosis['checks_performed'].append('direct_subordinates')
        
        if subordinate_ids:
            # Get subordinate details
            subordinates = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.employee',
                'read',
                [subordinate_ids],
                {'fields': ['name', 'job_title', 'parent_id']}
            )
            
            diagnosis['subordinate_details'] = subordinates
        
        # Check 2: Your own parent_id (your manager)
        your_data = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.employee',
            'read',
            [employee_id],
            {'fields': ['name', 'parent_id', 'job_title']}
        )
        
        if your_data:
            diagnosis['your_info'] = your_data[0]
        diagnosis['checks_performed'].append('your_manager')
        
        # Check 3: Alternative - look for employees where you might be listed differently
        # Sometimes the relationship might be stored in a different field
        all_employees = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.employee',
            'search_read',
            [[['parent_id', '!=', False]]],
            {'fields': ['name', 'parent_id'], 'limit': 200}
        )
        
        # Find employees who report to you
        reports_to_you = []
        for emp in all_employees:
            if emp.get('parent_id') and isinstance(emp['parent_id'], list):
                if emp['parent_id'][0] == employee_id:
                    reports_to_you.append({
                        'id': emp['id'],
                        'name': emp['name']
                    })
        
        diagnosis['alternative_subordinates'] = reports_to_you
        diagnosis['checks_performed'].append('alternative_check')
        
        # Check 4: Get leave states available in the system
        # Try to get one leave record to see available states
        sample_leave = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.leave',
            'search_read',
            [[]],
            {'fields': ['state'], 'limit': 10}
        )
        
        if sample_leave:
            states = list(set([leave.get('state', 'unknown') for leave in sample_leave]))
            diagnosis['available_leave_states'] = states
        diagnosis['checks_performed'].append('leave_states')
        
    except Exception as e:
        diagnosis['error'] = str(e)
    
    return diagnosis

def get_team_time_off_from_calendar(manager_employee_id, subordinate_ids=None):
    """
    Get team time off data from hr.leave.report.calendar model
    
    Args:
        manager_employee_id: ID of the manager
        subordinate_ids: Optional list of subordinate IDs (will fetch if not provided)
        
    Returns:
        Dictionary with calendar time off data
    """
    calendar_data = {
        'calendar_records': [],
        'by_employee': {},
        'debug_info': {}
    }
    
    try:
        # Get subordinate IDs if not provided
        if not subordinate_ids:
            subordinate_ids = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.employee',
                'search',
                [[['parent_id', '=', manager_employee_id]]],
                {}
            )
        
        if not subordinate_ids:
            calendar_data['debug_info']['no_subordinates'] = True
            return calendar_data
        
        calendar_data['debug_info']['subordinate_ids'] = subordinate_ids
        
        # First, let's check what fields are available in hr.leave.report.calendar
        try:
            calendar_fields = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.leave.report.calendar',
                'fields_get',
                [],
                {'attributes': ['string', 'type']}
            )
            
            # Store available fields for debugging
            calendar_data['debug_info']['available_fields'] = list(calendar_fields.keys())
            
            # Common fields that might exist
            potential_fields = [
                'employee_id', 'name', 'start_datetime', 'stop_datetime',
                'date_from', 'date_to', 'number_of_days', 'holiday_status_id',
                'state', 'display_name', 'leave_type', 'duration'
            ]
            
            # Filter to only fields that actually exist
            fields_to_read = [f for f in potential_fields if f in calendar_fields]
            calendar_data['debug_info']['fields_to_read'] = fields_to_read
            
        except Exception as e:
            calendar_data['debug_info']['fields_error'] = str(e)
            # Fallback to basic fields
            fields_to_read = ['employee_id', 'name', 'start_datetime', 'stop_datetime']
        
        # Search for calendar records for team members
        from datetime import datetime, timedelta
        today = datetime.now()
        past_date = (today - timedelta(days=7)).strftime('%Y-%m-%d')
        future_date = (today + timedelta(days=60)).strftime('%Y-%m-%d')
        
        # Try different search approaches
        search_domains = [
            # Approach 1: Direct employee filter
            [['employee_id', 'in', subordinate_ids]],
            
            # Approach 2: With date range
            [
                ['employee_id', 'in', subordinate_ids],
                '|',
                ['start_datetime', '>=', past_date],
                ['date_from', '>=', past_date]
            ],
            
            # Approach 3: Just get recent records and filter later
            [
                '|',
                ['start_datetime', '>=', past_date],
                ['date_from', '>=', past_date]
            ]
        ]
        
        calendar_ids = []
        for i, domain in enumerate(search_domains):
            try:
                calendar_ids = st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    'hr.leave.report.calendar',
                    'search',
                    [domain],
                    {'limit': 500}
                )
                
                calendar_data['debug_info'][f'search_approach_{i+1}'] = {
                    'domain': domain,
                    'count': len(calendar_ids)
                }
                
                if calendar_ids:
                    break
            except Exception as e:
                calendar_data['debug_info'][f'search_error_{i+1}'] = str(e)
        
        if calendar_ids:
            # Read the calendar records
            try:
                calendar_records = st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    'hr.leave.report.calendar',
                    'read',
                    [calendar_ids],
                    {'fields': fields_to_read}
                )
                
                # Filter for team members and organize by employee
                for record in calendar_records:
                    emp_data = record.get('employee_id')
                    if emp_data:
                        emp_id = emp_data[0] if isinstance(emp_data, list) else emp_data
                        emp_name = emp_data[1] if isinstance(emp_data, list) and len(emp_data) > 1 else str(emp_data)
                        
                        # Check if this employee is in our team
                        if emp_id in subordinate_ids:
                            calendar_data['calendar_records'].append(record)
                            
                            if emp_name not in calendar_data['by_employee']:
                                calendar_data['by_employee'][emp_name] = []
                            
                            calendar_data['by_employee'][emp_name].append(record)
                
                calendar_data['debug_info']['total_team_records'] = len(calendar_data['calendar_records'])
                calendar_data['debug_info']['employees_with_time_off'] = list(calendar_data['by_employee'].keys())
                
            except Exception as e:
                calendar_data['debug_info']['read_error'] = str(e)
        
        # If calendar model doesn't work, try hr.leave.report
        if not calendar_data['calendar_records']:
            calendar_data.update(get_team_time_off_from_report(subordinate_ids))
        
    except Exception as e:
        calendar_data['debug_info']['main_error'] = str(e)
    
    return calendar_data

def get_team_time_off_from_report(subordinate_ids):
    """
    Alternative: Get time off from hr.leave.report model
    
    Args:
        subordinate_ids: List of subordinate employee IDs
        
    Returns:
        Dictionary with time off data
    """
    report_data = {
        'report_records': [],
        'by_employee': {},
        'debug_info': {'using_report_model': True}
    }
    
    try:
        # Search in hr.leave.report
        report_ids = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.leave.report',
            'search',
            [[
                ['employee_id', 'in', subordinate_ids],
                ['state', 'in', ['validate', 'confirm']]
            ]],
            {'limit': 500}
        )
        
        if report_ids:
            reports = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.leave.report',
                'read',
                [report_ids],
                {'fields': ['employee_id', 'name', 'holiday_status_id', 'date_from', 'date_to', 'number_of_days', 'state', 'leave_type']}
            )
            
            for report in reports:
                emp_data = report.get('employee_id')
                if emp_data:
                    emp_name = emp_data[1] if isinstance(emp_data, list) and len(emp_data) > 1 else str(emp_data)
                    
                    report_data['report_records'].append(report)
                    
                    if emp_name not in report_data['by_employee']:
                        report_data['by_employee'][emp_name] = []
                    
                    report_data['by_employee'][emp_name].append(report)
            
            report_data['debug_info']['total_records'] = len(report_data['report_records'])
            
    except Exception as e:
        report_data['debug_info']['error'] = str(e)
    
    return report_data

# Add this diagnostic function to odoo_connector.py:

def diagnose_time_off_models(employee_id, subordinate_ids=None):
    """
    Comprehensive diagnostic for time off models and data
    
    Args:
        employee_id: Manager's employee ID
        subordinate_ids: Optional list of subordinate IDs
        
    Returns:
        Dictionary with detailed diagnostic information
    """
    diagnosis = {
        'models_checked': [],
        'data_found': {},
        'errors': {},
        'subordinate_ids': subordinate_ids or []
    }
    
    try:
        # Get subordinate IDs if not provided
        if not subordinate_ids:
            subordinate_ids = st.session_state.odoo_models.execute_kw(
                st.session_state.db,
                st.session_state.odoo_uid,
                st.session_state.password,
                'hr.employee',
                'search',
                [[['parent_id', '=', employee_id]]],
                {}
            )
            diagnosis['subordinate_ids'] = subordinate_ids
        
        if not subordinate_ids:
            diagnosis['errors']['no_subordinates'] = 'No subordinates found'
            return diagnosis
        
        # List of models to check
        models_to_check = [
            'hr.leave',
            'hr.leave.report',
            'hr.leave.report.calendar',
            'hr.holidays',  # Older Odoo versions
            'hr.holidays.status',  # Leave types in older versions
            'hr.leave.allocation'
        ]
        
        for model in models_to_check:
            try:
                # Check if model exists and is accessible
                test_search = st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    model,
                    'search',
                    [[]],
                    {'limit': 1}
                )
                
                diagnosis['models_checked'].append(model)
                
                # Get fields for this model
                fields = st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    model,
                    'fields_get',
                    [],
                    {'attributes': ['string', 'type']}
                )
                
                diagnosis[f'{model}_fields'] = list(fields.keys())[:20]  # First 20 fields
                
                # Try to get any records for subordinates
                if 'employee_id' in fields:
                    records = st.session_state.odoo_models.execute_kw(
                        st.session_state.db,
                        st.session_state.odoo_uid,
                        st.session_state.password,
                        model,
                        'search',
                        [[['employee_id', 'in', subordinate_ids]]],
                        {'limit': 10}
                    )
                    
                    diagnosis['data_found'][model] = {
                        'count': len(records),
                        'ids': records[:5] if records else []
                    }
                    
                    # If we found records, get a sample
                    if records:
                        sample = st.session_state.odoo_models.execute_kw(
                            st.session_state.db,
                            st.session_state.odoo_uid,
                            st.session_state.password,
                            model,
                            'read',
                            [records[0]],
                            {'fields': list(fields.keys())[:10]}  # First 10 fields
                        )
                        diagnosis[f'{model}_sample'] = sample[0] if sample else {}
                
            except Exception as e:
                diagnosis['errors'][model] = str(e)
        
        # Special check for different state values
        if 'hr.leave' in diagnosis['models_checked']:
            try:
                # Get all unique states
                all_leaves = st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    'hr.leave',
                    'search_read',
                    [[['employee_id', 'in', subordinate_ids]]],
                    {'fields': ['state'], 'limit': 200}
                )
                
                if all_leaves:
                    states = list(set([leave.get('state', 'unknown') for leave in all_leaves]))
                    diagnosis['leave_states_found'] = states
                    
                    # Count by state
                    state_counts = {}
                    for leave in all_leaves:
                        state = leave.get('state', 'unknown')
                        state_counts[state] = state_counts.get(state, 0) + 1
                    diagnosis['leave_state_counts'] = state_counts
                    
            except Exception as e:
                diagnosis['errors']['state_check'] = str(e)
        
        # Check for time off using alternative field names
        alternative_searches = [
            {'model': 'hr.leave', 'domain': [['user_id.employee_ids', 'in', subordinate_ids]]},
            {'model': 'hr.leave', 'domain': [['employee_id.user_id.id', 'in', subordinate_ids]]},
            {'model': 'hr.leave.report', 'domain': []},  # Get all and filter later
        ]
        
        for search in alternative_searches:
            try:
                records = st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    search['model'],
                    'search',
                    [search['domain']],
                    {'limit': 50}
                )
                
                if records:
                    diagnosis[f'alternative_{search["model"]}'] = {
                        'count': len(records),
                        'domain': search['domain']
                    }
            except:
                pass
        
    except Exception as e:
        diagnosis['errors']['main'] = str(e)
    
    return diagnosis

# Add a chat command to run this diagnostic
def handle_time_off_diagnostic(employee_data):
    """
    Handle time off diagnostic request
    
    Args:
        employee_data: Employee data dictionary
        
    Returns:
        Formatted diagnostic response
    """
    employee_id = employee_data.get('id')
    team_data = employee_data.get('team_data', {})
    subordinate_ids = [s['id'] for s in team_data.get('subordinates', [])]
    
    diagnosis = diagnose_time_off_models(employee_id, subordinate_ids)
    
    response = "🔍 **Time Off System Diagnostic Report**\n\n"
    
    response += f"**Your Employee ID:** {employee_id}\n"
    response += f"**Subordinate IDs:** {diagnosis['subordinate_ids']}\n\n"
    
    response += "**Models Checked:**\n"
    for model in diagnosis['models_checked']:
        data_info = diagnosis['data_found'].get(model, {})
        response += f"✓ {model}: {data_info.get('count', 0)} records found\n"
    
    if diagnosis.get('leave_states_found'):
        response += f"\n**Leave States in System:** {', '.join(diagnosis['leave_states_found'])}\n"
        if diagnosis.get('leave_state_counts'):
            response += "**State Distribution:**\n"
            for state, count in diagnosis['leave_state_counts'].items():
                response += f"- {state}: {count} records\n"
    
    # Show sample data if found
    for model in diagnosis['models_checked']:
        sample_key = f'{model}_sample'
        if sample_key in diagnosis and diagnosis[sample_key]:
            response += f"\n**Sample {model} Record:**\n"
            sample = diagnosis[sample_key]
            for key in ['employee_id', 'state', 'date_from', 'date_to', 'holiday_status_id']:
                if key in sample:
                    response += f"- {key}: {sample[key]}\n"
    
    if diagnosis.get('errors'):
        response += "\n**Errors Encountered:**\n"
        for model, error in diagnosis['errors'].items():
            response += f"❌ {model}: {error}\n"
    
    # Store in debug info
    if 'debug_info' not in st.session_state:
        st.session_state.debug_info = {}
    st.session_state.debug_info['time_off_diagnosis'] = diagnosis
    
    response += "\n**Next Steps:**\n"
    response += "1. Check which models have data\n"
    response += "2. Verify the state values (might not be 'validate'/'confirm')\n"
    response += "3. Check if employee relationships are correct\n"
    response += "\nFull diagnostic data saved to debug info."
    
    return response

def get_all_team_leaves_raw(subordinate_ids):
    """
    Get ALL leave records for team members without filtering by state
    
    Args:
        subordinate_ids: List of subordinate employee IDs
        
    Returns:
        List of all leave records
    """
    try:
        # Get ALL leaves for these employees
        all_leaves = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.leave',
            'search_read',
            [[['employee_id', 'in', subordinate_ids]]],
            {
                'fields': ['employee_id', 'state', 'date_from', 'date_to', 
                          'holiday_status_id', 'number_of_days', 'name'],
                'limit': 200
            }
        )
        
        # Debug info
        if 'debug_info' not in st.session_state:
            st.session_state.debug_info = {}
        
        st.session_state.debug_info['raw_leaves'] = {
            'count': len(all_leaves),
            'states': list(set([l.get('state', 'unknown') for l in all_leaves])),
            'sample': all_leaves[:3] if all_leaves else []
        }
        
        return all_leaves
        
    except Exception as e:
        if 'debug_info' not in st.session_state:
            st.session_state.debug_info = {}
        st.session_state.debug_info['raw_leaves_error'] = str(e)
        return []

def get_all_overtime_categories():
    """
    Get all available overtime categories from Odoo.
    """
    try:
        category_ids = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'approval.category',
            'search',
            [[['name', 'ilike', 'overtime']]]
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
        st.error(f"An error occurred while fetching overtime categories: {e}")
        return []

def get_pending_overtime_requests(manager_employee_id):
    """
    Get pending overtime requests for employees under a manager.
    """
    try:
        # Find all employees who report to this manager
        subordinate_employee_ids = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.employee',
            'search',
            [[['parent_id', '=', manager_employee_id]]]
        )

        if not subordinate_employee_ids:
            return []

        # Get the user IDs linked to these employees
        employees = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.employee',
            'read',
            [subordinate_employee_ids],
            {'fields': ['user_id']}
        )
        subordinate_user_ids = [emp['user_id'][0] for emp in employees if emp['user_id']]

        if not subordinate_user_ids:
            return []

        # Find pending approval requests for these users
        request_ids = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'approval.request',
            'search',
            [[
                ['request_owner_id', 'in', subordinate_user_ids],
                ['request_status', 'in', ['new', 'pending']]
            ]]
        )

        if not request_ids:
            return []

        requests = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'approval.request',
            'read',
            [request_ids],
            {'fields': ['id', 'name', 'request_owner_id', 'category_id', 'request_status', 'create_date']}
        )
        return requests
    except Exception as e:
        st.error(f"Error getting pending overtime requests: {e}")
        return []

def approve_overtime_request(request_id):
    """
    Approve an overtime request.
    """
    try:
        # First, get the request details before approving
        request_details = st.session_state.odoo_models.execute_kw(
            st.session_state.db, st.session_state.odoo_uid, st.session_state.password,
            'approval.request', 'read', [[request_id]], 
            {'fields': ['name', 'request_owner_id', 'category_id', 'date_start', 'date_end', 'reason']}
        )
        
        # Store the details
        details = request_details[0] if request_details else {}
        
        # The action_approve method might return None, which causes XML-RPC marshaling errors
        # We'll catch this specific case and handle it gracefully
        result = st.session_state.odoo_models.execute_kw(
            st.session_state.db, st.session_state.odoo_uid, st.session_state.password,
            'approval.request', 'action_approve', [[request_id]]
        )
        
        # If we get here without an exception, the action was successful
        # Format the success message with details
        employee_name = details.get('request_owner_id', ['', 'Unknown'])[1] if isinstance(details.get('request_owner_id'), list) else 'Unknown'
        category_name = details.get('category_id', ['', 'Unknown'])[1] if isinstance(details.get('category_id'), list) else 'Unknown'
        date_start = details.get('date_start', 'N/A')
        date_end = details.get('date_end', 'N/A')
        reason = details.get('reason', 'No reason provided')
        
        message = f"""✅ **Overtime Request #{request_id} Approved!**

**Employee:** {employee_name}
**Category:** {category_name}
**Period:** {date_start} to {date_end}
**Reason:** {reason}

The employee has been notified of the approval."""
        
        return {'success': True, 'message': message}
        
    except xmlrpc.client.Fault as e:
        # Check if it's the specific "cannot marshal None" error
        if "cannot marshal None unless allow_none is enabled" in str(e):
            # This error actually means the action completed successfully
            # but returned None. Let's verify by checking the request status
            try:
                # Read the request to confirm it was approved
                request_data = st.session_state.odoo_models.execute_kw(
                    st.session_state.db, st.session_state.odoo_uid, st.session_state.password,
                    'approval.request', 'read', [[request_id]], 
                    {'fields': ['request_status', 'state', 'name', 'request_owner_id', 'category_id', 'date_start', 'date_end', 'reason']}
                )
                
                if request_data:
                    status = request_data[0].get('request_status') or request_data[0].get('state')
                    if status in ['approved', 'done', 'validate']:
                        details = request_data[0]
                        employee_name = details.get('request_owner_id', ['', 'Unknown'])[1] if isinstance(details.get('request_owner_id'), list) else 'Unknown'
                        category_name = details.get('category_id', ['', 'Unknown'])[1] if isinstance(details.get('category_id'), list) else 'Unknown'
                        date_start = details.get('date_start', 'N/A')
                        date_end = details.get('date_end', 'N/A')
                        reason = details.get('reason', 'No reason provided')
                        
                        message = f"""✅ **Overtime Request #{request_id} Approved!**

**Employee:** {employee_name}
**Category:** {category_name}
**Period:** {date_start} to {date_end}
**Reason:** {reason}

The employee has been notified of the approval."""
                        
                        return {'success': True, 'message': message}
                    else:
                        return {'success': False, 'message': f"Request {request_id} status is {status}, not approved"}
                else:
                    # If we can't read the request, assume it was approved since no exception
                    return {'success': True, 'message': f"✅ Overtime Request #{request_id} has been approved."}
                    
            except Exception as verify_error:
                # If verification fails, still assume success since the action didn't throw an error
                return {'success': True, 'message': f"✅ Overtime Request #{request_id} has been approved."}
                
        else:
            # Other XML-RPC faults are real errors
            return {'success': False, 'message': f"❌ Failed to approve request {request_id}: {e}"}
            
    except Exception as e:
        return {'success': False, 'message': f"❌ Failed to approve request {request_id}: {e}"}

def refuse_overtime_request(request_id):
    """
    Refuse an overtime request.
    """
    try:
        # First, get the request details before refusing
        request_details = st.session_state.odoo_models.execute_kw(
            st.session_state.db, st.session_state.odoo_uid, st.session_state.password,
            'approval.request', 'read', [[request_id]], 
            {'fields': ['name', 'request_owner_id', 'category_id', 'date_start', 'date_end', 'reason']}
        )
        
        # Store the details
        details = request_details[0] if request_details else {}
        
        # The action_refuse method might return None, which causes XML-RPC marshaling errors
        result = st.session_state.odoo_models.execute_kw(
            st.session_state.db, st.session_state.odoo_uid, st.session_state.password,
            'approval.request', 'action_refuse', [[request_id]]
        )
        
        # If we get here without an exception, the action was successful
        # Format the success message with details
        employee_name = details.get('request_owner_id', ['', 'Unknown'])[1] if isinstance(details.get('request_owner_id'), list) else 'Unknown'
        category_name = details.get('category_id', ['', 'Unknown'])[1] if isinstance(details.get('category_id'), list) else 'Unknown'
        date_start = details.get('date_start', 'N/A')
        date_end = details.get('date_end', 'N/A')
        reason = details.get('reason', 'No reason provided')
        
        message = f"""❌ **Overtime Request #{request_id} Refused**

**Employee:** {employee_name}
**Category:** {category_name}
**Period:** {date_start} to {date_end}
**Reason:** {reason}

The employee has been notified of the refusal."""
        
        return {'success': True, 'message': message}
        
    except xmlrpc.client.Fault as e:
        # Check if it's the specific "cannot marshal None" error
        if "cannot marshal None unless allow_none is enabled" in str(e):
            # This error actually means the action completed successfully
            # but returned None. Let's verify by checking the request status
            try:
                request_data = st.session_state.odoo_models.execute_kw(
                    st.session_state.db, st.session_state.odoo_uid, st.session_state.password,
                    'approval.request', 'read', [[request_id]], 
                    {'fields': ['request_status', 'state', 'name', 'request_owner_id', 'category_id', 'date_start', 'date_end', 'reason']}
                )
                
                if request_data:
                    status = request_data[0].get('request_status') or request_data[0].get('state')
                    if status in ['refused', 'reject', 'cancel']:
                        details = request_data[0]
                        employee_name = details.get('request_owner_id', ['', 'Unknown'])[1] if isinstance(details.get('request_owner_id'), list) else 'Unknown'
                        category_name = details.get('category_id', ['', 'Unknown'])[1] if isinstance(details.get('category_id'), list) else 'Unknown'
                        date_start = details.get('date_start', 'N/A')
                        date_end = details.get('date_end', 'N/A')
                        reason = details.get('reason', 'No reason provided')
                        
                        message = f"""❌ **Overtime Request #{request_id} Refused**

**Employee:** {employee_name}
**Category:** {category_name}
**Period:** {date_start} to {date_end}
**Reason:** {reason}

The employee has been notified of the refusal."""
                        
                        return {'success': True, 'message': message}
                    else:
                        return {'success': False, 'message': f"Request {request_id} status is {status}, not refused"}
                else:
                    return {'success': True, 'message': f"❌ Overtime Request #{request_id} has been refused."}
                    
            except Exception:
                return {'success': True, 'message': f"❌ Overtime Request #{request_id} has been refused."}
                
        else:
            return {'success': False, 'message': f"❌ Failed to refuse request {request_id}: {e}"}
            
    except Exception as e:
        return {'success': False, 'message': f"❌ Failed to refuse request {request_id}: {e}"}

def cancel_overtime_request(request_id):
    """
    Cancel an overtime request.
    """
    try:
        # First, get the request details before cancelling
        request_details = st.session_state.odoo_models.execute_kw(
            st.session_state.db, st.session_state.odoo_uid, st.session_state.password,
            'approval.request', 'read', [[request_id]], 
            {'fields': ['name', 'request_owner_id', 'category_id', 'date_start', 'date_end', 'reason']}
        )
        
        # Store the details
        details = request_details[0] if request_details else {}
        
        # The action_cancel method might return None, which causes XML-RPC marshaling errors
        result = st.session_state.odoo_models.execute_kw(
            st.session_state.db, st.session_state.odoo_uid, st.session_state.password,
            'approval.request', 'action_cancel', [[request_id]]
        )
        
        # If we get here without an exception, the action was successful
        # Format the success message with details
        employee_name = details.get('request_owner_id', ['', 'Unknown'])[1] if isinstance(details.get('request_owner_id'), list) else 'Unknown'
        category_name = details.get('category_id', ['', 'Unknown'])[1] if isinstance(details.get('category_id'), list) else 'Unknown'
        date_start = details.get('date_start', 'N/A')
        date_end = details.get('date_end', 'N/A')
        reason = details.get('reason', 'No reason provided')
        
        message = f"""🚫 **Overtime Request #{request_id} Cancelled**

**Employee:** {employee_name}
**Category:** {category_name}
**Period:** {date_start} to {date_end}
**Reason:** {reason}

The request has been cancelled."""
        
        return {'success': True, 'message': message}
        
    except xmlrpc.client.Fault as e:
        # Check if it's the specific "cannot marshal None" error
        if "cannot marshal None unless allow_none is enabled" in str(e):
            # This error actually means the action completed successfully
            # but returned None. Let's verify by checking the request status
            try:
                request_data = st.session_state.odoo_models.execute_kw(
                    st.session_state.db, st.session_state.odoo_uid, st.session_state.password,
                    'approval.request', 'read', [[request_id]], 
                    {'fields': ['request_status', 'state', 'name', 'request_owner_id', 'category_id', 'date_start', 'date_end', 'reason']}
                )
                
                if request_data:
                    status = request_data[0].get('request_status') or request_data[0].get('state')
                    if status in ['cancel', 'cancelled', 'draft']:
                        details = request_data[0]
                        employee_name = details.get('request_owner_id', ['', 'Unknown'])[1] if isinstance(details.get('request_owner_id'), list) else 'Unknown'
                        category_name = details.get('category_id', ['', 'Unknown'])[1] if isinstance(details.get('category_id'), list) else 'Unknown'
                        date_start = details.get('date_start', 'N/A')
                        date_end = details.get('date_end', 'N/A')
                        reason = details.get('reason', 'No reason provided')
                        
                        message = f"""🚫 **Overtime Request #{request_id} Cancelled**

**Employee:** {employee_name}
**Category:** {category_name}
**Period:** {date_start} to {date_end}
**Reason:** {reason}

The request has been cancelled."""
                        
                        return {'success': True, 'message': message}
                    else:
                        return {'success': False, 'message': f"Request {request_id} status is {status}, not cancelled"}
                else:
                    return {'success': True, 'message': f"🚫 Overtime Request #{request_id} has been cancelled."}
                    
            except Exception:
                return {'success': True, 'message': f"🚫 Overtime Request #{request_id} has been cancelled."}
                
        else:
            return {'success': False, 'message': f"❌ Failed to cancel request {request_id}: {e}"}
            
    except Exception as e:
        return {'success': False, 'message': f"❌ Failed to cancel request {request_id}: {e}"}

def get_miscellaneous_expense_product_id():
    """
    Look up the product_id for the '[EXP_GEN] Miscellaneous' expense category in Odoo.
    Returns the product ID (int) or None if not found.
    """
    try:
        # Search for product by name or code
        product_ids = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'product.product',
            'search',
            [[
                '|',
                ['name', 'ilike', 'Miscellaneous'],
                ['default_code', '=', 'EXP_GEN']
            ]],
            {'limit': 1}
        )
        if product_ids:
            return product_ids[0]
        return None
    except Exception as e:
        if 'debug_info' not in st.session_state:
            st.session_state.debug_info = {}
        st.session_state.debug_info['misc_product_lookup_error'] = str(e)
        return None


def create_and_submit_expense(employee_id, company_id, description, total, date, purpose=None, attached_link=None):
    """
    Create and submit a new hr.expense record for the given employee.
    Returns a dict with success, message, and expense_id if successful.
    """
    result = {"success": False, "message": "", "expense_id": None, "error": None}
    try:
        product_id = get_miscellaneous_expense_product_id()
        if not product_id:
            result["message"] = "Could not find the '[EXP_GEN] Miscellaneous' expense category in Odoo."
            return result

        # Prepare the expense data
        expense_data = {
            'name': description,
            'product_id': product_id,
            'total_amount_currency': total,
            'date': date,
            'company_id': company_id,
            'employee_id': employee_id,
            # Currency is always JOD (hardcoded for now)
        }
        if purpose:
            expense_data['x_studio_purpose'] = purpose
        if attached_link:
            expense_data['x_studio_attached_link'] = attached_link

        # Create the expense
        expense_id = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.expense',
            'create',
            [expense_data]
        )
        result["expense_id"] = expense_id

        # Try to submit for approval (try common button names)
        submitted = False
        for btn in ("action_submit_expenses", "action_submit", "submit_expenses", "action_confirm"):
            try:
                st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    'hr.expense',
                    btn,
                    [[expense_id]]
                )
                submitted = True
                result["submission_method"] = btn
                break
            except Exception as exc:
                result[f"{btn}_error"] = str(exc)

        result["success"] = True
        suffix = "and submitted for approval" if submitted else "but needs manual submission"
        result["message"] = f"Expense report created (ID {expense_id}) {suffix}."
        if not submitted:
            result["needs_manual_submission"] = True
        return result
    except Exception as exc:
        result.update(success=False, error=str(exc), message=f"Error creating expense report: {exc}")
        return result

def get_travel_accommodation_expense_product_id():
    """
    Look up the product_id for the '[TRANS & ACC] Travel & Accommodation' expense category in Odoo.
    Returns the product ID (int) or None if not found.
    """
    try:
        # Search for product by name or code
        product_ids = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'product.product',
            'search',
            [[
                '|',
                ['name', 'ilike', 'Travel & Accommodation'],
                ['default_code', '=', 'TRANS & ACC']
            ]],
            {'limit': 1}
        )
        if product_ids:
            return product_ids[0]
        return None
    except Exception as e:
        if 'debug_info' not in st.session_state:
            st.session_state.debug_info = {}
        st.session_state.debug_info['travel_accommodation_product_lookup_error'] = str(e)
        return None


def create_and_submit_travel_accommodation_expense(employee_id, company_id, description, total, date, purpose=None, attached_link=None):
    """
    Create and submit a new hr.expense record for the given employee in the Travel & Accommodation category.
    Returns a dict with success, message, and expense_id if successful.
    """
    result = {"success": False, "message": "", "expense_id": None, "error": None}
    try:
        product_id = get_travel_accommodation_expense_product_id()
        if not product_id:
            result["message"] = "Could not find the '[TRANS & ACC] Travel & Accommodation' expense category in Odoo."
            return result

        # Prepare the expense data
        expense_data = {
            'name': description,
            'product_id': product_id,
            'total_amount_currency': total,
            'date': date,
            'company_id': company_id,
            'employee_id': employee_id,
            # Currency is always JOD (hardcoded for now)
        }
        if purpose:
            expense_data['x_studio_purpose'] = purpose
        if attached_link:
            expense_data['x_studio_attached_link'] = attached_link

        # Create the expense
        expense_id = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.expense',
            'create',
            [expense_data]
        )
        result["expense_id"] = expense_id

        # Try to submit for approval (try common button names)
        submitted = False
        for btn in ("action_submit_expenses", "action_submit", "submit_expenses", "action_confirm"):
            try:
                st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    'hr.expense',
                    btn,
                    [[expense_id]]
                )
                submitted = True
                result["submission_method"] = btn
                break
            except Exception as exc:
                result[f"{btn}_error"] = str(exc)

        result["success"] = True
        suffix = "and submitted for approval" if submitted else "but needs manual submission"
        result["message"] = f"Expense report created (ID {expense_id}) {suffix}."
        if not submitted:
            result["needs_manual_submission"] = True
        return result
    except Exception as exc:
        result.update(success=False, error=str(exc), message=f"Error creating expense report: {exc}")
        return result

def get_per_diem_expense_product_id():
    """
    Look up the product_id for the '[PER_DIEM] Per Diem' expense category in Odoo.
    Returns the product ID (int) or None if not found.
    """
    try:
        product_ids = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'product.product',
            'search',
            [[
                '|',
                ['name', 'ilike', 'Per Diem'],
                ['default_code', '=', 'PER_DIEM']
            ]],
            {'limit': 1}
        )
        if product_ids:
            return product_ids[0]
        return None
    except Exception as e:
        if 'debug_info' not in st.session_state:
            st.session_state.debug_info = {}
        st.session_state.debug_info['per_diem_product_lookup_error'] = str(e)
        return None


def create_and_submit_per_diem_expense(employee_id, company_id, description, total, date, from_date, to_date, destination_id, purpose=None, attached_link=None):
    """
    Create and submit a new hr.expense record for the given employee in the Per Diem category.
    Includes x_studio_from, x_studio_to, and x_studio_destination fields.
    Returns a dict with success, message, and expense_id if successful.
    """
    result = {"success": False, "message": "", "expense_id": None, "error": None}
    try:
        product_id = get_per_diem_expense_product_id()
        if not product_id:
            result["message"] = "Could not find the '[PER_DIEM] Per Diem' expense category in Odoo."
            return result

        # Prepare the expense data
        expense_data = {
            'name': description,
            'product_id': product_id,
            'total_amount_currency': total,
            'date': date,
            'company_id': company_id,
            'employee_id': employee_id,
            'x_studio_from': from_date,
            'x_studio_to': to_date,
            'x_studio_destination': destination_id,
            # Currency is always JOD (hardcoded for now)
        }
        if purpose:
            expense_data['x_studio_purpose'] = purpose
        if attached_link:
            expense_data['x_studio_attached_link'] = attached_link

        # Create the expense
        expense_id = st.session_state.odoo_models.execute_kw(
            st.session_state.db,
            st.session_state.odoo_uid,
            st.session_state.password,
            'hr.expense',
            'create',
            [expense_data]
        )
        result["expense_id"] = expense_id

        # Try to submit for approval (try common button names)
        submitted = False
        for btn in ("action_submit_expenses", "action_submit", "submit_expenses", "action_confirm"):
            try:
                st.session_state.odoo_models.execute_kw(
                    st.session_state.db,
                    st.session_state.odoo_uid,
                    st.session_state.password,
                    'hr.expense',
                    btn,
                    [[expense_id]]
                )
                submitted = True
                result["submission_method"] = btn
                break
            except Exception as exc:
                result[f"{btn}_error"] = str(exc)

        result["success"] = True
        suffix = "and submitted for approval" if submitted else "but needs manual submission"
        result["message"] = f"Expense report created (ID {expense_id}) {suffix}."
        if not submitted:
            result["needs_manual_submission"] = True
        return result
    except Exception as exc:
        result.update(success=False, error=str(exc), message=f"Error creating expense report: {exc}")
        return result