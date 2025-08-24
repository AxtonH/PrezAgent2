import streamlit as st

# OpenAI API Key - loaded from Streamlit secrets
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# Odoo connection details - loaded from Streamlit secrets
ODOO_URL = st.secrets["ODOO_URL"]
ODOO_DB = st.secrets["ODOO_DB"]
ODOO_USERNAME = st.secrets["ODOO_USERNAME"]
ODOO_PASSWORD = st.secrets["ODOO_PASSWORD"]

# Odoo model field mappings
# Dictionary of relation models for resolving Many2one relationships
RELATION_MODELS = {
    'department_id': 'hr.department',
    'parent_id': 'hr.employee',
    'coach_id': 'hr.employee',
    'address_id': 'res.partner',
    'company_id': 'res.company',
    'job_id': 'hr.job',
    'resource_calendar_id': 'resource.calendar',
    'work_location_id': 'hr.work.location',  # The correct relation
    'holiday_status_id': 'hr.leave.type',    # Leave type relation
    'role_id': 'planning.role',              # Planning role relation
    'project_id': 'project.project',         # Project relation
    'resource_id': 'resource.resource',      # Resource relation
    'sale_line_id': 'sale.order.line',       # Sales order line relation
    'place_id': 'res.partner'                # Work place relation
}

# Basic employee fields that are safe to request
EMPLOYEE_BASIC_FIELDS = ['name', 'job_title', 'work_email', 'work_phone', 'department_id']

# Additional employee fields that might require permissions
EMPLOYEE_ADDITIONAL_FIELDS = [
    'mobile_phone', 
    'identification_id',
    'gender',
    'birthday',
    'address_id',
    'work_location_id',  # The correct field name
    'parent_id',         # Manager
    'coach_id',          # Coach
    'department_id',
    'job_id',
    'resource_calendar_id',  # Working hours
    'tz',                # Timezone
    'category_ids',      # Tags
    'marital',
    'company_id',
    'planning_role_ids'  # Planning roles
]

# Partner fields to retrieve
PARTNER_FIELDS = [
    'name', 'email', 'phone', 'mobile', 
    'street', 'city', 'zip', 'country_id',
    'function', 'title', 'company_id', 'user_id'
]

# OpenAI model configuration
OPENAI_MODEL = "gpt-3.5-turbo"
OPENAI_TEMPERATURE = 1
OPENAI_MAX_TOKENS = 2000
