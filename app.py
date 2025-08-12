# app.py
import streamlit as st
import streamlit.components.v1 as components
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
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  :root {
    --bg-start: #F7F7FB;
    --bg-end: #ECE9F7;
    --primary: #6F57E8;
    --primary-600: #5b44e1;
    --text: #1f1b2d;
    --muted: #6a6580;
    --ring: rgba(111, 87, 232, .35);
  }

  html, body, #root, .stApp, .main, section.main > div {
    background: radial-gradient(1200px 600px at 10% 10%, var(--bg-end), transparent),
                radial-gradient(1200px 600px at 90% 10%, #f0f7ff, transparent),
                linear-gradient(180deg, var(--bg-start), #ffffff);
    background-attachment: fixed !important;
    font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
    color: var(--text);
  }

  /* Main content width ~75% of viewport on wide screens */
  .block-container { max-width: 75vw; }

  /* Chat list */
  div[data-testid="stChatMessageContainer"] {
    display: flex !important;
    flex-direction: column !important;
    gap: 12px !important;
    padding: 8px 0 240px !important; /* allow space for fixed input */
    scroll-behavior: smooth !important;
  }
  div[data-testid="stChatMessageContainer"]:before { content: ''; flex: 1 1 auto; }

  /* Hide avatars */
  img[data-testid="chatAvatarIcon-user"],
  img[data-testid="chatAvatarIcon-assistant"] { display: none !important; }

  /* Reset default message wrapper */
  div[data-testid="stChatMessage"] { background: transparent !important; border: none !important; }

  /* User bubble (right) */
  div[data-testid="stChatMessageContainer"] > div[data-testid="stChatMessage"]:has(img[data-testid="chatAvatarIcon-user"]) {
    flex-direction: row-reverse !important; text-align: right !important;
  }
  div[data-testid="stChatMessageContainer"] > div[data-testid="stChatMessage"]:has(img[data-testid="chatAvatarIcon-user"]) > div:last-child {
    background: linear-gradient(135deg, var(--primary), var(--primary-600)) !important;
    color: #fff !important;
    border-radius: 18px 18px 4px 18px !important;
    margin-left: auto !important; margin-right: 0 !important;
    max-width: 72% !important; padding: 12px 16px !important;
    box-shadow: 0 6px 20px rgba(111, 87, 232, .25) !important;
  }

  /* Assistant bubble (left) */
  div[data-testid="stChatMessageContainer"] > div[data-testid="stChatMessage"]:has(img[data-testid="chatAvatarIcon-assistant"]) > div:last-child {
    background: #ffffffcc !important;
    backdrop-filter: saturate(1.2) blur(6px) !important;
    color: var(--text) !important;
    border: 1px solid rgba(111, 87, 232, .12) !important;
    border-radius: 18px 18px 18px 4px !important;
    margin-right: auto !important; margin-left: 0 !important;
    max-width: 72% !important; padding: 12px 16px !important;
    box-shadow: 0 8px 18px rgba(31, 27, 45, .06) !important;
  }

  /* Links & code in bubbles */
  .bot-bubble a { color: var(--primary) !important; text-decoration: none; font-weight: 600; }
  .bot-bubble a:hover { text-decoration: underline; }
  .bot-bubble code, .user-bubble code { background: #f3f2f9; padding: 2px 6px; border-radius: 6px; }

  /* Fixed input at bottom (glassmorphism) */
  div[data-testid="stChatInput"] {
    position: fixed !important; bottom: 20px !important; left: 50% !important; transform: translateX(-50%) !important;
    width: calc(100% - 40px) !important; max-width: 920px !important;
    background: rgba(255, 255, 255, 0.75) !important; backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(111, 87, 232, .25) !important; border-radius: 20px !important;
    box-shadow: 0 10px 30px rgba(31, 27, 45, .12) !important; padding: 6px 8px !important; z-index: 999 !important;
  }
  div[data-testid="stChatInput"] textarea { border: none !important; }
  div[data-testid="stChatInput"]:focus-within { box-shadow: 0 0 0 4px var(--ring) !important; }

  /* Sidebar */
  section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #fbfbffcc, #ffffffcc) !important;
    backdrop-filter: blur(12px) !important;
    border-right: 1px solid rgba(111, 87, 232, .12) !important;
    transition: transform .25s ease, opacity .25s ease;
  }

  /* Class-based sidebar hide (JS toggles .sb-hidden on <html>) */
  .sb-hidden section[data-testid="stSidebar"] {
    transform: translateX(-110%);
    opacity: 0;
    pointer-events: none;
  }

  /* Global tweaks */
  header, #MainMenu, .stDeployButton { display: none !important; }

  /* Floating sidebar toggle */
  #sb-toggle {
    position: fixed; top: 16px; left: 16px; z-index: 10000;
    background: #ffffffcc; backdrop-filter: blur(8px);
    border: 1px solid rgba(111,87,232,.25); color: var(--primary);
    border-radius: 10px; padding: 6px 10px; font-size: 13px; cursor: pointer;
    box-shadow: 0 6px 18px rgba(31,27,45,.12);
  }
  #sb-toggle:hover { background: #fff; }

</style>
""", unsafe_allow_html=True)

# Handle sidebar toggle via query param (JS-free and reliable)
params = {}
try:
    params = dict(st.query_params)
except Exception:
    try:
        params = st.experimental_get_query_params()
    except Exception:
        params = {}

if 'sb' in params:
    raw_val = params.get('sb')
    value = raw_val[0] if isinstance(raw_val, list) else str(raw_val)
    st.session_state.sidebar_hidden = (value == '1')
    # Clear param to keep URL clean
    try:
        del st.query_params['sb']
    except Exception:
        try:
            cleaned = {k: v for k, v in params.items() if k != 'sb'}
            st.experimental_set_query_params(**cleaned)
        except Exception:
            pass

# Conditionally hide sidebar via CSS (no JS needed)
if st.session_state.sidebar_hidden:
    st.markdown(
        """
        <style>
          section[data-testid="stSidebar"] {
            transform: translateX(-110%) !important;
            opacity: 0 !important;
            pointer-events: none !important;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

# Floating sidebar toggle using a component (no page refresh)
components.html(
    """
    <style>
      #sb-toggle {
        position: fixed; top: 16px; left: 16px; z-index: 10000;
        background: #ffffffcc; backdrop-filter: blur(8px);
        border: 1px solid rgba(111,87,232,.25); color: #6F57E8;
        border-radius: 10px; padding: 6px 10px; font-size: 13px; cursor: pointer;
        box-shadow: 0 6px 18px rgba(31,27,45,.12);
      }
      #sb-toggle:hover { background: #fff; }
    </style>
    <button id=\"sb-toggle\">☰ Menu</button>
    <script>
      (function(){
        const btn = document.getElementById('sb-toggle');
        if (!btn) return;
        const send = (target, msg) => { try { target.postMessage(msg, '*'); } catch(e){} };
        btn.addEventListener('click', () => {
          const msgs = [
            { isStreamlitMessage: true, type: 'streamlit:toggleSidebar' },
            { isStreamlitMessage: true, command: 'toggleSidebar' }
          ];
          msgs.forEach(m => { send(window, m); if (window.parent && window.parent !== window) send(window.parent, m); });
        });
      })();
    </script>
    """,
    height=60,
)

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

