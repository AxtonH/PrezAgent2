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
        st.session_state.sidebar_hidden = False
        # Ensure activities list exists
        st.session_state.recent_activities = []
    
    # No need for chat visibility toggle

# Call the initialization function
init_session_state()

# Initialize managers
auth_manager = AuthManager(ODOO_URL, ODOO_DB)
chat_manager = ChatManager()
search_manager = EmployeeSearchManager()
style_manager = StyleManager()

# Load styles
style_manager.load_css()

# Lilac Galaxy ChatGPT-style design
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  :root {
    --bg-start: #F7F7FB;
    --bg-end: #ECE9F7;
    --primary: #9B6DD6;
    --primary-600: #8B5CF6;
    --text: #2d333a;
    --text-light: #6e7681;
    --border: rgba(155, 109, 214, 0.2);
    --user-bg: rgba(255, 255, 255, 0.8);
    --assistant-bg: rgba(255, 255, 255, 0.6);
    --sidebar-bg: rgba(248, 242, 255, 0.9);
  }

  /* Lilac Galaxy Background */
  html, body, #root, .stApp, .main, section.main > div {
    background: 
      radial-gradient(ellipse 1200px 600px at 10% 10%, rgba(236, 233, 247, 0.6), transparent),
      radial-gradient(ellipse 1000px 500px at 90% 10%, rgba(248, 242, 255, 0.8), transparent),
      radial-gradient(ellipse 800px 400px at 50% 90%, rgba(183, 148, 230, 0.3), transparent),
      linear-gradient(180deg, var(--bg-start), #ffffff);
    background-attachment: fixed !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
    color: var(--text);
    min-height: 100vh;
  }

  /* Main content container - 75% width */
  .block-container { 
    max-width: 75vw !important; 
    padding-top: 1rem !important;
    padding-bottom: 8rem !important;
  }

  /* Chat container - 75% width */
  div[data-testid="stChatMessageContainer"] {
    display: flex !important;
    flex-direction: column !important;
    gap: 1rem !important;
    padding: 0 !important;
    margin: 0 !important;
    max-width: 75vw !important;
    margin: 0 auto !important;
  }

  /* Hide avatars completely */
  img[data-testid="chatAvatarIcon-user"],
  img[data-testid="chatAvatarIcon-assistant"] { 
    display: none !important; 
  }

  /* Reset message wrapper */
  div[data-testid="stChatMessage"] { 
    background: transparent !important; 
    border: none !important;
    padding: 0 !important;
    margin: 0 !important;
  }

  /* User message styling */
  div[data-testid="stChatMessage"]:has(img[data-testid="chatAvatarIcon-user"]) {
    background: var(--user-bg) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 1.5rem !important;
    margin: 0 auto !important;
    max-width: 75vw !important;
    box-shadow: 0 4px 16px rgba(155, 109, 214, 0.1) !important;
  }

  div[data-testid="stChatMessage"]:has(img[data-testid="chatAvatarIcon-user"]) > div:last-child {
    background: transparent !important;
    color: var(--text) !important;
    border: none !important;
    border-radius: 0 !important;
    margin: 0 auto !important;
    max-width: 100% !important; 
    padding: 0 !important;
    box-shadow: none !important;
    font-size: 16px !important;
    line-height: 1.5 !important;
    text-align: center !important;
  }

  /* Assistant message styling */
  div[data-testid="stChatMessage"]:has(img[data-testid="chatAvatarIcon-assistant"]) {
    background: var(--assistant-bg) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 1.5rem !important;
    margin: 0 auto !important;
    max-width: 75vw !important;
    box-shadow: 0 4px 16px rgba(155, 109, 214, 0.08) !important;
  }

  div[data-testid="stChatMessage"]:has(img[data-testid="chatAvatarIcon-assistant"]) > div:last-child {
    background: transparent !important;
    color: var(--text) !important;
    border: none !important;
    border-radius: 0 !important;
    margin: 0 auto !important;
    max-width: 100% !important; 
    padding: 0 !important;
    box-shadow: none !important;
    font-size: 16px !important;
    line-height: 1.6 !important;
    text-align: center !important;
  }

  /* Code blocks in messages */
  div[data-testid="stChatMessage"] code {
    background: rgba(155, 109, 214, 0.1) !important;
    padding: 2px 6px !important;
    border-radius: 4px !important;
    font-size: 14px !important;
  }

  /* Chat input styling - 75% width */
  div[data-testid="stChatInput"] {
    position: fixed !important; 
    bottom: 2rem !important; 
    left: 50% !important; 
    transform: translateX(-50%) !important;
    width: calc(75vw - 2rem) !important; 
    max-width: calc(75vw - 2rem) !important;
    background: rgba(255, 255, 255, 0.9) !important;
    backdrop-filter: blur(15px) !important;
    border: 1px solid var(--border) !important; 
    border-radius: 20px !important;
    box-shadow: 0 8px 32px rgba(155, 109, 214, 0.2) !important; 
    padding: 0 !important; 
    z-index: 999 !important;
  }

  div[data-testid="stChatInput"] textarea { 
    border: none !important;
    background: transparent !important;
    font-size: 16px !important;
    line-height: 1.5 !important;
    padding: 1rem 1.5rem !important;
    resize: none !important;
    color: var(--text) !important;
  }

  div[data-testid="stChatInput"] textarea:focus {
    outline: none !important;
    box-shadow: none !important;
  }

  div[data-testid="stChatInput"]:focus-within { 
    border-color: var(--primary) !important;
    box-shadow: 0 8px 32px rgba(155, 109, 214, 0.3) !important;
  }

  /* Sidebar - harmonious with page theme */
  section[data-testid="stSidebar"] {
    background: rgba(255, 255, 255, 0.7) !important;
    backdrop-filter: blur(20px) !important;
    border-right: none !important;
    border-radius: 0 25px 25px 0 !important; /* Circular right edge */
    width: 280px !important;
    transition: all 0.3s ease !important;
    position: relative !important;
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    margin-top: 60px !important; /* Leave space for header */
    box-shadow: 0 8px 32px rgba(155, 109, 214, 0.15) !important;
    border: 1px solid rgba(155, 109, 214, 0.1) !important;
    border-left: none !important;
  }

  section[data-testid="stSidebar"] > div {
    background: transparent !important;
    padding-top: 1rem !important;
  }

  /* Make sure sidebar is always visible on login */
  .stApp section[data-testid="stSidebar"] {
    display: block !important;
  }

  /* Adjust main content layout based on sidebar state */
  .main .block-container {
    padding-top: 80px !important; /* Account for header */
  }

  /* Hide only specific Streamlit elements, keep header visible */
  .stDeployButton,
  footer {
    display: none !important; 
  }

  /* Transparent header - functional but subtle */
  header[data-testid="stHeader"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    background: rgba(255, 255, 255, 0.1) !important; /* Very transparent */
    backdrop-filter: blur(8px) !important;
    border-bottom: none !important; /* Remove border */
    height: 60px !important;
    z-index: 1000 !important; /* Higher than sidebar */
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    width: 100% !important;
    transition: background 0.2s ease !important;
  }

  /* Show header slightly on hover for better UX */
  header[data-testid="stHeader"]:hover {
    background: rgba(255, 255, 255, 0.3) !important;
  }

  /* Style the header toolbar */
  .stAppHeader {
    display: flex !important;
    visibility: visible !important;
  }

  /* Make sure sidebar toggle button is visible */
  button[data-testid="stSidebarNavButton"] {
    display: flex !important;
    visibility: visible !important;
  }

  /* Button styling */
  .stButton > button {
    background: var(--primary) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.75rem 1rem !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 8px rgba(155, 109, 214, 0.3) !important;
  }

  .stButton > button:hover {
    background: var(--primary-600) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(155, 109, 214, 0.4) !important;
  }

</style>


""", unsafe_allow_html=True)

# Remove custom toggle - use Streamlit's native sidebar toggle

# Custom menu component removed per request

# Always render sidebar content (so it exists to toggle)
if not st.session_state.logged_in:
    # Show login screen with minimal sidebar
    with st.sidebar:
        st.markdown("""
        <div style="padding: 1.5rem 1rem; text-align: center;">
            <div style="font-size: 1.5rem; font-weight: 700; color: #9B6DD6; margin-bottom: 0.5rem;">PrezAgent</div>
            <div style="font-size: 0.875rem; color: #6e7681;">Employee Assistant</div>
        </div>
        <div style="height: 1px; background: linear-gradient(90deg, transparent, rgba(155, 109, 214, 0.3), transparent); margin: 1rem 0;"></div>
        <div style="padding: 1.5rem; background: rgba(255, 255, 255, 0.8); border-radius: 16px; margin: 1rem; border: 1px solid rgba(155, 109, 214, 0.15); box-shadow: 0 4px 16px rgba(155, 109, 214, 0.1);">
            <div style="font-size: 0.875rem; color: #6e7681; text-align: center; line-height: 1.5;">
                🔐 Sign in to access all features
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    saved_credentials = auth_manager.cred_manager.load_credentials()
    render_login_form(auth_manager.login, saved_credentials)
else:
    # User is logged in - render full sidebar
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


# Trigger a one-time rerun when activities update so the sidebar refreshes immediately
if st.session_state.pop('activities_dirty', False):
    st.rerun()