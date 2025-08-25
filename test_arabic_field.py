#!/usr/bin/env python3

import streamlit as st

def test_arabic_name_field():
    """Test if we can retrieve the Arabic name field from Odoo"""
    
    if not st.session_state.get('odoo_connected'):
        return "❌ Not connected to Odoo"
    
    # Get current user's employee ID
    current_employee_data = st.session_state.get('employee_data')
    if not current_employee_data:
        return "❌ No employee data available"
    
    employee_id = current_employee_data.get('id')
    if not employee_id:
        return "❌ No employee ID found"
    
    models = st.session_state.odoo_models
    uid = st.session_state.odoo_uid
    db = st.session_state.db
    password = st.session_state.password
    
    result = {
        'employee_id': employee_id,
        'tests': {}
    }
    
    # Test 1: Try to read all fields to see what's available
    try:
        all_fields_data = models.execute_kw(
            db, uid, password, 'hr.employee', 'read',
            [employee_id], {}  # No fields specified = get all readable fields
        )
        if all_fields_data:
            available_fields = list(all_fields_data[0].keys())
            result['tests']['all_available_fields'] = {
                'success': True,
                'count': len(available_fields),
                'fields': available_fields,
                'has_arabic_field': 'x_studio_employee_arabic_name' in available_fields
            }
        else:
            result['tests']['all_available_fields'] = {
                'success': False,
                'error': 'No data returned'
            }
    except Exception as e:
        result['tests']['all_available_fields'] = {
            'success': False,
            'error': str(e)
        }
    
    # Test 2: Try to read the specific Arabic field
    try:
        arabic_field_data = models.execute_kw(
            db, uid, password, 'hr.employee', 'read',
            [employee_id], {'fields': ['x_studio_employee_arabic_name']}
        )
        if arabic_field_data:
            result['tests']['arabic_field_specific'] = {
                'success': True,
                'data': arabic_field_data[0],
                'value': arabic_field_data[0].get('x_studio_employee_arabic_name')
            }
        else:
            result['tests']['arabic_field_specific'] = {
                'success': False,
                'error': 'No data returned'
            }
    except Exception as e:
        result['tests']['arabic_field_specific'] = {
            'success': False,
            'error': str(e)
        }
    
    # Test 3: Search for fields containing "arabic" or "name"
    if result['tests'].get('all_available_fields', {}).get('success'):
        available_fields = result['tests']['all_available_fields']['fields']
        arabic_related_fields = [f for f in available_fields if 'arabic' in f.lower() or 'name' in f.lower()]
        result['tests']['name_related_fields'] = arabic_related_fields
    
    return result

# Make this available as a chat command
def handle_arabic_field_test(query, employee_data):
    """Handle the arabic field test command"""
    if 'test arabic field' in query.lower() or 'debug arabic' in query.lower():
        result = test_arabic_name_field()
        
        if isinstance(result, str):
            return result
        
        response = f"## Arabic Field Test Results\n\n"
        response += f"**Employee ID:** {result['employee_id']}\n\n"
        
        # All available fields test
        all_fields_test = result['tests'].get('all_available_fields', {})
        if all_fields_test.get('success'):
            response += f"✅ **All Fields Test:** Found {all_fields_test['count']} readable fields\n"
            response += f"- Arabic field present: {'✅ YES' if all_fields_test.get('has_arabic_field') else '❌ NO'}\n\n"
            
            if all_fields_test.get('has_arabic_field'):
                response += f"🎉 **Good news!** The `x_studio_employee_arabic_name` field exists and is readable.\n\n"
            else:
                response += f"⚠️ **Issue found:** The `x_studio_employee_arabic_name` field is not available.\n\n"
                # Show name-related fields
                name_fields = result['tests'].get('name_related_fields', [])
                if name_fields:
                    response += f"**Name-related fields found:**\n"
                    for field in name_fields:
                        response += f"- {field}\n"
                    response += "\n"
        else:
            response += f"❌ **All Fields Test Failed:** {all_fields_test.get('error', 'Unknown error')}\n\n"
        
        # Specific Arabic field test
        arabic_test = result['tests'].get('arabic_field_specific', {})
        if arabic_test.get('success'):
            arabic_value = arabic_test.get('value')
            response += f"✅ **Arabic Field Specific Test:** Successfully retrieved\n"
            response += f"- Value: `{arabic_value}`\n"
            response += f"- Is Arabic script: {'✅ YES' if arabic_value and any('\u0600' <= c <= '\u06FF' for c in str(arabic_value)) else '❌ NO'}\n\n"
        else:
            response += f"❌ **Arabic Field Specific Test Failed:** {arabic_test.get('error', 'Unknown error')}\n\n"
        
        # Store full result in debug info
        if 'debug_info' not in st.session_state:
            st.session_state.debug_info = {}
        st.session_state.debug_info['arabic_field_test'] = result
        
        response += "**Full test results saved to debug info.**\n"
        response += "Enable debug mode in the sidebar to see detailed technical data."
        
        return response
    
    return None

if __name__ == "__main__":
    # This can be run as a standalone script if needed
    print("Arabic field test module loaded")
