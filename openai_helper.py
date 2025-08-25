# openai_helper.py
import openai
import json
import time
import streamlit as st
from config import OPENAI_API_KEY, OPENAI_MAX_TOKENS, OPENAI_MODEL
from odoo_connector import is_manager

# Import functions from the split modules
from manager_approval_helper import (
    detect_approval_intent,
    handle_manager_approval_flow,
    handle_manager_overtime_approval,
    detect_overtime_approval_intent
)
from employee_request_helper import (
    detect_time_off_intent,
    handle_time_off_request,
    handle_template_request,
    handle_employee_request,
    detect_leave_balance_intent,
    format_leave_balance
)
from template_generator import detect_template_intent
from test_arabic_field import handle_arabic_field_test
from overtime_request_helper import detect_overtime_intent, handle_overtime_request
from employee_search import handle_employee_search, detect_employee_search_intent
from session_manager import get_session_value, update_session_value, clear_workflow
from expense_report_helper import start_expense_workflow, handle_expense_workflow
from odoo_connector import get_employee_leave_data
import re
from rapidfuzz import fuzz

# Set the API key
openai.api_key = OPENAI_API_KEY
ASSISTANT_ID = "asst_i2akGYm7lz607bcgyPgkkE1d"  # Prezbot Assistant ID

def detect_exit_intent(query):
    """
    Detect if the user wants to exit the current flow
    
    Args:
        query: User's message
        
    Returns:
        Boolean indicating if user wants to exit
    """
    query_lower = query.lower().strip()
    
    # Exit keywords
    exit_keywords = [
        'cancel', 'exit', 'stop', 'quit', 'nevermind', 'never mind',
        'back', 'go back', 'return', 'normal chat', 'regular chat',
        'forget it', 'skip', 'abort', 'done', 'finish',
        'no thanks', 'not now', 'maybe later', 'later',
        'i changed my mind', 'actually no', 'actually, no',
        'return to chat', 'back to chat', 'normal mode'
    ]
    
    # Check for exact matches first
    if query_lower in exit_keywords:
        return True
    
    # Check if any exit keyword is in the query
    return any(keyword in query_lower for keyword in exit_keywords)

def clear_all_flows():
    """Clear all active flow states"""
    if 'time_off_request' in st.session_state:
        st.session_state.time_off_request = {}
    if 'template_request' in st.session_state:
        st.session_state.template_request = {}
    if 'approval_flow' in st.session_state:
        del st.session_state.approval_flow
    if 'pending_requests' in st.session_state:
        del st.session_state.pending_requests
    if 'overtime_request' in st.session_state:
        st.session_state.overtime_request = {}

def classify_intent_nlp(query, employee_data):
    """
    Use OpenAI to classify user intent for routing flows.
    Returns (intent_label, confidence) where confidence is a float between 0 and 1.
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        # Base intents available to everyone
        available_intents = [
            'time_off_request', 'template_request', 'overtime_request',
            'policy_question', 'employee_search', 'general'
        ]
        
        intent_descriptions = {
            'time_off_request': "User is asking for or booking time off.",
            'template_request': "User wants a document like a letter or certificate.",
            'overtime_request': "User is asking to request overtime.",
            'policy_question': "User is asking a question about a company policy (e.g., 'what is the time off policy?').",
            'employee_search': "User is trying to find a specific employee's contact information or details, usually by providing a name.",
            'manager_approval': "Manager is asking to see pending approvals for their team.",
            'manager_overtime_approval': "Manager is asking to see or manage pending overtime approvals for their team.",
            'general': "A general question, conversation, or a request that doesn't fit other categories. This includes a manager asking to see their team members (e.g., 'who are my reports?')."
        }

        system_prompt = "You are an intent classifier. Classify the user's query into one of the following categories:\n"
        
        # Check if user is a manager and add manager-specific intents
        if employee_data and is_manager(employee_data.get('id')):
            available_intents.extend(['manager_approval', 'manager_overtime_approval'])

        for intent in available_intents:
            system_prompt += f"- '{intent}': {intent_descriptions[intent]}\n"

        system_prompt += '\nRespond in valid JSON format: {"label": "<intent>", "confidence": <0-1>}'
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0,
            max_tokens=60,
            response_format={"type": "json_object"}
        )
        
        ai_response = response.choices[0].message.content
        if not ai_response:
            return 'general', 0.0
            
        result = json.loads(ai_response)
        return result.get('label', 'general'), float(result.get('confidence', 0.0))
            
    except Exception as e:
        st.session_state.debug_info['nlp_error'] = str(e)
        return 'general', 0.0

def detect_expense_report_intent(query):
    """
    Detect if the user wants to create an expense report.
    """
    query_lower = query.lower().strip()
    keywords = [
        'expense', 'reimbursement', 'claim', 'my expenses', 'submit expense', 'expense report',
        'add expense', 'new expense', 'miscellaneous expense', 'lunch with customer', 'business expense'
    ]
    return any(k in query_lower for k in keywords)

def is_policy_question(query):
    """
    Detect if this is a general policy question that should not be contaminated with personal data
    """
    query_lower = query.lower()
    
    # Policy-related keywords that indicate general policy questions
    policy_indicators = [
        'policy', 'policies', 'procedure', 'procedures', 'process', 'rule', 'rules',
        'how does', 'how do', 'what is', 'what are', 'tell me about', 'explain',
        'company policy', 'prezlab policy', 'prezlabs policy', 'holiday policy',
        'leave policy', 'vacation policy', 'sick leave policy', 'overtime policy',
        'expense policy', 'reimbursement policy', 'travel policy', 'remote work policy',
        'work from home policy', 'attendance policy', 'time off policy'
    ]
    
    # Personal data keywords that indicate it's about individual data
    personal_indicators = [
        'my leave', 'my vacation', 'my balance', 'my allocation', 'my days',
        'how many days do i have', 'my remaining', 'my available', 'my used',
        'show my', 'check my', 'view my', 'display my'
    ]
    
    # Check if it contains policy indicators
    has_policy_indicators = any(indicator in query_lower for indicator in policy_indicators)
    
    # Check if it contains personal indicators
    has_personal_indicators = any(indicator in query_lower for indicator in personal_indicators)
    
    # It's a policy question if it has policy indicators but no personal indicators
    return has_policy_indicators and not has_personal_indicators

def is_informational_question(query):
    """
    Detect if the query is an informational question that should be handled by 
    the knowledge base rather than triggering a workflow.
    """
    import re
    query_lower = query.lower().strip()
    
    # Question words/patterns that indicate informational queries
    question_patterns = [
        r'^\s*what\s+(is|are|does|do|can|would|will|should)',  # "What is...", "What are...", etc.
        r'^\s*how\s+(does|do|can|would|will|should|to)',       # "How does...", "How to...", etc.  
        r'^\s*when\s+(does|do|can|would|will|should|is|are)',  # "When does...", "When is...", etc.
        r'^\s*where\s+(does|do|can|would|will|should|is|are)', # "Where does...", "Where is...", etc.
        r'^\s*why\s+(does|do|can|would|will|should|is|are)',   # "Why does...", "Why is...", etc.
        r'^\s*who\s+(does|do|can|would|will|should|is|are)',   # "Who does...", "Who is...", etc.
        r'^\s*(can\s+you\s+)?(tell\s+me|explain|describe)',    # "Tell me about...", "Explain...", "Describe..."
        r'^\s*is\s+(there|it|this)',                           # "Is there...", "Is it...", "Is this..."
        r'^\s*are\s+(there|they|these)',                       # "Are there...", "Are they...", "Are these..."
        r'^\s*do\s+(you\s+know|we\s+have|i\s+need\s+to\s+know)', # "Do you know...", "Do we have..."
        r'^\s*(what\'s|whats)\s+the',                          # "What's the policy...", "What's the process..."
        r'information\s+(about|on|regarding)',                 # "information about..."
        r'details\s+(about|on|regarding)',                     # "details about..."
    ]
    
    # Check if it starts with question patterns
    for pattern in question_patterns:
        if re.search(pattern, query_lower):
            return True
    
    # Additional heuristics for questions
    if query_lower.endswith('?'):
        return True
    
    # Policy/process related questions
    policy_question_patterns = [
        r'\b(policy|policies|procedure|procedures|process|processes|rule|rules|guideline|guidelines)\b',
        r'\bhow\s+(long|much|many|often)',
        r'\bwhat\s+(happens|is\s+the|are\s+the)',
    ]
    
    for pattern in policy_question_patterns:
        if re.search(pattern, query_lower):
            return True
            
    return False

def generate_ai_response(query, employee_data):
    """
    Generate AI response using OpenAI Assistant (Prezbot) based on employee data and query
    """
    # Workflow Prioritization
    active_workflow = get_session_value('active_workflow')
    # --- TEMPLATE/EMBASSY LETTER WORKFLOW GUARD ---
    if st.session_state.get('template_request', {}).get('template_type') or st.session_state.get('template_request', {}).get('embassy_details'):
        return handle_template_request(query, employee_data)

    # --- INFORMATIONAL QUESTION GUARD ---
    # If it's clearly an informational question, prioritize knowledge base over workflows
    if is_informational_question(query):
        # Still check for leave balance intent for specific balance queries like "show my leave balance"
        if detect_leave_balance_intent(query):
            # But only if it's a direct balance request, not a general policy question
            # More specific check - don't block if it's asking specifically about "my balance" 
            import re
            policy_words = ['policy', 'procedure', 'process', 'rule', 'how to', 'how do', 'how does', 'work']
            what_policy_patterns = [r'what is.*(?:policy|procedure|process|rule)', r'what are.*(?:policy|procedure|process|rule)']
            
            has_policy_context = (
                any(word in query.lower() for word in policy_words) or
                any(re.search(pattern, query.lower()) for pattern in what_policy_patterns)
            )
            
            if not has_policy_context:
                return format_leave_balance(employee_data)
        # Otherwise, let it fall through to general AI response
    else:
        # --- ARABIC FIELD TEST INTENT ---
        arabic_test_result = handle_arabic_field_test(query, employee_data)
        if arabic_test_result:
            return arabic_test_result
        
        # --- LEAVE BALANCE INTENT GUARD ---
        if detect_leave_balance_intent(query):
            return format_leave_balance(employee_data)

    if active_workflow:
        if active_workflow == 'overtime_request':
            return handle_overtime_request(query, employee_data)
        elif active_workflow == 'employee_request':
            return handle_employee_request(query, employee_data)
        elif active_workflow == 'expense_report':
            # Pass st.session_state directly for expense workflow
            response = handle_expense_workflow(st.session_state, query)
            if response == "":
                # If the workflow handler returns an empty string, treat as no response and continue
                pass
            else:
                return response

    if not employee_data:
        return "I can't seem to identify who you are. Please try logging in again."

    # Check for exit intent first
    if detect_exit_intent(query):
        if get_session_value('active_workflow'):
            clear_workflow()
            return "✅ The process has been cancelled. How else can I help you?"
        # If no active workflow, let it be handled as a general query

    # NLP-based intent classification
    intent, confidence = classify_intent_nlp(query, employee_data)
    st.session_state.debug_info['last_intent'] = {'intent': intent, 'confidence': confidence}

    # Expense report intent detection (hybrid)
    if detect_expense_report_intent(query) or intent == 'expense_report':
        # Start the workflow if not already started
        if get_session_value('active_workflow') != 'expense_report':
            st.session_state.active_workflow = 'expense_report'
            # Use employee_data for user profile
            user_profile = {
                'odoo_user_id': employee_data.get('id'),
                'company_id': employee_data.get('company_id')[0] if isinstance(employee_data.get('company_id'), (list, tuple)) else employee_data.get('company_id'),
                'company_name': employee_data.get('company_id')[1] if isinstance(employee_data.get('company_id'), (list, tuple)) and len(employee_data.get('company_id')) > 1 else '',
            }
            return start_expense_workflow(st.session_state, user_profile)
        else:
            return handle_expense_workflow(st.session_state, query)

    # Route based on intent
    if confidence < 0.7:
        # If it's an informational question, don't override with specific detectors unless very specific
        if is_informational_question(query):
            intent = 'general'  # Let the knowledge base handle it
        else:
            # If confidence is low, check with more specific detectors before falling back to general
            if detect_overtime_intent(query):
                intent = 'overtime_request'
            elif detect_time_off_intent(query):
                intent = 'time_off_request'
            elif detect_template_intent(query):
                intent = 'template_request'
            elif detect_employee_search_intent(query):
                intent = 'employee_search'
            elif is_manager(employee_data.get('id')):
                if detect_approval_intent(query):
                    intent = 'manager_approval'
                elif detect_overtime_approval_intent(query):
                    intent = 'manager_overtime_approval'
            else:
                intent = 'general'

    if intent == 'manager_overtime_approval':
        return handle_manager_overtime_approval(query, employee_data)
    elif intent == 'manager_approval':
        return handle_manager_approval_flow(query, employee_data)
    elif intent == 'overtime_request':
        return handle_overtime_request(query, employee_data)
    elif intent == 'time_off_request':
        return handle_employee_request(query, employee_data)
    elif intent == 'template_request':
        return handle_template_request(query, employee_data)
    elif intent == 'employee_search':
        return handle_employee_search(query)
    elif intent == 'policy_question':
        # Let the general AI handle policy questions
        pass
    
    # Fallback to general AI response using the assistant
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # Check if this is a policy question that should use clean context
        if is_policy_question(query):
            # Clean context for policy questions - no personal data contamination
            context_message = f"""
            You are Prezbot, a specialized assistant for Prezlab employees.
            
            You have comprehensive knowledge about Prezlab's policies and procedures. Please provide 
            a detailed, accurate response about company policies based on your training data.
            
            Answer the following policy question: {query}
            """
        else:
            # Personal context for individual questions
            is_partner = employee_data.get('is_partner', False)
            data_type = "partner" if is_partner else "employee"
            
            manager_context = ""
            if not is_partner and is_manager(employee_data.get('id')):
                manager_context = """
            6. As a manager, you can:
               - List your team members (their details are in the provided data).
               - View and approve/deny pending time off requests.
               - View and manage pending overtime requests.
               - View approved time off for your team.
            """
            
            context_message = f"""
            You are answering questions about a Prezlab {data_type} named {employee_data.get('name', 'Unknown')} with the following data:
            {json.dumps(employee_data, indent=2)}
            
            Remember:
            1. This person works at Prezlab.
            2. You are Prezbot, a specialized assistant for Prezlab employees.
            3. You can help request time off.
            4. You can help generate documents like employment letters.
            5. You can help submit overtime requests.{manager_context}
            
            Use the specific information provided AND your general knowledge about Prezlab's policies 
            to answer the following question: {query}
            """
        
        thread = client.beta.threads.create()
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=context_message
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )
        
        # Wait for the run to complete
        while run.status not in ["completed", "failed"]:
            time.sleep(0.5)
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            
        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            for msg in messages.data:
                if msg.role == "assistant":
                    # Check if the content is a text block before accessing it
                    if msg.content and msg.content[0].type == 'text':
                        return msg.content[0].text.value
    
    except Exception as e:
        st.session_state.debug_info['assistant_error'] = str(e)
        return "I'm having trouble connecting to my brain right now. Please try again in a moment."
    
    return "I'm not sure how to help with that. Could you please rephrase or ask something else?"
