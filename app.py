# app.py
import streamlit as st
from config import OPENAI_API_KEY, ODOO_URL, ODOO_DB
from auth import AuthManager
from ui_components import render_header, render_login_form, render_sidebar, render_empty_state
from chat import ChatManager
from employee_search import EmployeeSearchManager
from style_manager import StyleManager

# Page configuration must come first
st.set_page_config(
    page_title="Prezlab Employee Chatbot",
    page_icon="💜",  # Changed to purple heart
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state with a function to ensure it's done properly
def init_session_state():
    """Initialize all session state variables"""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.logged_in = False
        st.session_state.manual_search_mode = False
        st.session_state.auto_loaded = False
        st.session_state.debug_info = {}  # Changed from None to empty dict
        st.session_state.messages = []
        st.session_state.employee_data = None
        st.session_state.username = None

# Call the initialization function
init_session_state()

# Initialize managers
auth_manager = AuthManager(ODOO_URL, ODOO_DB)
chat_manager = ChatManager()
search_manager = EmployeeSearchManager()
style_manager = StyleManager()

# Load styles
style_manager.load_css()

# Add custom CSS for the lilac background and header fix
st.markdown("""
<style>
    /* GRADIENT BACKGROUND - Force on all elements */
    html, body, #root, .stApp, .main, section.main > div {
        background: linear-gradient(135deg, #F3E8FF 0%, #FFFFFF 100%) !important;
        background-attachment: fixed !important;
    }
    
    .block-container {
        background: transparent !important;
    }
    
    /* CHAT MESSAGES - WhatsApp Style */
    /* User messages - Right aligned with purple background */
    div[data-testid="stChatMessageContainer"] > div[data-testid="stChatMessage"]:has(img[data-testid="chatAvatarIcon-user"]) {
        flex-direction: row-reverse !important;
        text-align: right !important;
    }
    
    div[data-testid="stChatMessageContainer"] > div[data-testid="stChatMessage"]:has(img[data-testid="chatAvatarIcon-user"]) > div:last-child {
        background-color: #9B6DD6 !important;
        color: white !important;
        border-radius: 18px 18px 4px 18px !important;
        margin-left: auto !important;
        margin-right: 0 !important;
        max-width: 70% !important;
        padding: 12px 16px !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1) !important;
    }
    
    /* Assistant messages - Left aligned with white background */
    div[data-testid="stChatMessageContainer"] > div[data-testid="stChatMessage"]:has(img[data-testid="chatAvatarIcon-assistant"]) > div:last-child {
        background-color: white !important;
        color: #2B1B4C !important;
        border: 1px solid rgba(212, 181, 247, 0.3) !important;
        border-radius: 18px 18px 18px 4px !important;
        margin-right: auto !important;
        margin-left: 0 !important;
        max-width: 70% !important;
        padding: 12px 16px !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    }
    
    /* Hide avatars */
    img[data-testid="chatAvatarIcon-user"],
    img[data-testid="chatAvatarIcon-assistant"] {
        display: none !important;
    }
    
    /* Remove default message styling */
    div[data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
    }
    
    /* Chat container - Bottom to top flow */
    div[data-testid="stChatMessageContainer"] {
        display: flex !important;
        flex-direction: column !important;
        padding-bottom: 20px !important;
    }
    
    /* Ensure messages start from bottom */
    div[data-testid="stChatMessageContainer"]:before {
        content: '';
        flex: 1 1 auto;
    }
    
    /* Chat input styling */
    div[data-testid="stChatInput"] {
        position: fixed !important;
        bottom: 20px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: calc(100% - 40px) !important;
        max-width: 900px !important;
        background-color: rgba(255, 255, 255, 0.95) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid #D4B5F7 !important;
        border-radius: 24px !important;
        box-shadow: 0 2px 8px rgba(155, 109, 214, 0.15) !important;
        padding: 4px !important;
        z-index: 999 !important;
    }
    
    /* Add padding to bottom of main container for chat input */
    section.main {
        padding-bottom: 100px !important;
    }
    
    /* Sidebar with semi-transparent background */
    section[data-testid="stSidebar"] {
        background: rgba(248, 242, 255, 0.9) !important;
        backdrop-filter: blur(10px) !important;
    }
    
    /* Hide Streamlit elements */
    header {
        display: none !important;
    }
    
    #MainMenu, footer, .stDeployButton {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Main app logic
if not st.session_state.logged_in:
    # Show login screen
    saved_credentials = auth_manager.cred_manager.load_credentials()
    render_login_form(auth_manager.login, saved_credentials)
else:
    # User is logged in
    render_sidebar(st.session_state.username, st.session_state.manual_search_mode, auth_manager.logout)
    
    # Main interface with better container styling
    with st.container():
        # Add header
        render_header()
        
        # Main interface
        search_manager.render_search_interface()
        
        # Display debug info if enabled
        if st.session_state.get('show_debug', False) and st.session_state.get('debug_info'):
            with st.expander("🔍 Debug Information", expanded=True):
                st.json(st.session_state.debug_info)
                
                # Also show employee data if available
                if st.session_state.get('employee_data'):
                    st.subheader("Employee Data:")
                    st.json(st.session_state.employee_data)
        
        # Display chat interface if employee data is available
        if st.session_state.employee_data:
            data = st.session_state.employee_data
            
            # Add some spacing
            st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
            
            # Display chat interface in a nice container
            with st.container():
                chat_manager.display_chat_interface(data) 
        else:
            # Empty state
            render_empty_state(st.session_state.manual_search_mode)

