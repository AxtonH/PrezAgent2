# ui_components.py
import streamlit as st
import time
import os
from activity_tracker import get_recent_activities, format_activity_time

def load_css():
    """Load CSS styles"""
    css_file = "style.css"
    if os.path.exists(css_file):
        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        # Fallback CSS if file doesn't exist (no chat bubble or chat alignment CSS)
        fallback_css = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        :root {
            --primary-purple: #9B6DD6;
            --light-purple: #B794E6;
            --lilac-bg: #F3E8FF;
            --lilac-light: #F8F2FF;
            --dark-purple: #2B1B4C;
            --border-purple: #D4B5F7;
        }
        body {
            font-family: 'Inter', sans-serif;
            color: var(--dark-purple);
        }
        .stApp {
            background: linear-gradient(135deg, #F3E8FF 0%, #FFFFFF 100%) !important;
            min-height: 100vh;
        }
        .main > div {
            background: transparent !important;
        }
        section[data-testid="stSidebar"] {
            background: rgba(248, 242, 255, 0.8) !important;
            backdrop-filter: blur(10px);
            border-right: 1px solid var(--border-purple);
        }
        section[data-testid="stSidebar"] > div {
            background: transparent !important;
        }
        .prezlab-logo {
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            font-size: 28px;
            color: var(--dark-purple);
            margin: 0;
            padding: 0;
        }
        .point {
            color: var(--primary-purple);
        }
        .scribble-bottom {
            display: block;
            height: 4px;
            background-color: var(--light-purple);
            border-radius: 2px;
            margin: 10px 0 20px 0;
            width: 100px;
        }
        .scribble-highlight {
            position: relative;
            display: inline-block;
        }
        .scribble-highlight::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 6px;
            background-color: rgba(155, 109, 214, 0.3);
            border-radius: 3px;
            z-index: -1;
        }
        /* (All chat bubble, chat-message, chat-messages-container, user-bubble, bot-bubble, and related chat CSS removed) */
        </style>
        """
        st.markdown(fallback_css, unsafe_allow_html=True)

def render_header():
    """Render the PrezAgent header"""
    st.markdown(
        """
        <div style="display: flex; align-items: center; justify-content: center; padding: 1.5rem 0; background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(10px); border-radius: 12px; margin-bottom: 2rem; border: 1px solid rgba(155, 109, 214, 0.2); box-shadow: 0 4px 16px rgba(155, 109, 214, 0.1);">
            <div style="font-size: 24px; font-weight: 700; color: #9B6DD6;">PrezAgent</div>
            <div style="margin-left: 10px; font-size: 18px; color: #6e7681;">✨</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

def render_login_form(login_callback, saved_credentials=None):
    """
    Render the PrezAgent login form with lilac theme
    
    Args:
        login_callback: Function to call when login is submitted
        saved_credentials: Optional saved credentials dict
    """
    # Centered logo and welcome message
    st.markdown("""
    <div style="text-align: center; margin: 4rem 0 3rem 0;">
        <div style="font-size: 3rem; font-weight: 700; color: #9B6DD6; margin-bottom: 1rem;">PrezAgent</div>
        <div style="font-size: 1.25rem; color: #6e7681; margin-bottom: 0.5rem;">Welcome back!</div>
        <p style="color: #8B5CF6; font-size: 1rem;">Sign in to access PrezAgent</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create three columns for centering - expand center column by 10%
    col1, col2, col3 = st.columns([0.95, 1.1, 0.95])
    
    with col2:
        # Login form in a glass card
        with st.container():
            with st.form("login_form", clear_on_submit=False):
                # Pre-fill username if available
                default_username = saved_credentials['username'] if saved_credentials else ""
                username = st.text_input("Email", 
                                       value=default_username,
                                       placeholder="your.email@prezlab.com",
                                       label_visibility="collapsed")
                
                st.markdown("<div style='margin-bottom: 0.2rem;'></div>", unsafe_allow_html=True)
                
                # Pre-fill password if available (hidden)
                default_password = saved_credentials['password'] if saved_credentials else ""
                password = st.text_input("Password", 
                                       value=default_password,
                                       type="password", 
                                       placeholder="Enter your password",
                                       label_visibility="collapsed")
                
                st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)
                
                # Remember me checkbox with custom styling (restored)
                remember_me = st.checkbox(
                    "Remember me",
                    value=bool(saved_credentials),
                    help="Save your credentials for faster login next time",
                )
                
                st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)
                
                submitted = st.form_submit_button("Sign In", use_container_width=True)
                
                if submitted:
                    if username and password:
                        login_callback(username, password, remember_me)
                    else:
                        st.error("Please enter both email and password")
            
            # Show if credentials are saved
            if saved_credentials:
                st.info("🔐 Saved credentials found")
                
                # Auto-login if not already attempted
                if 'auto_login_attempted' not in st.session_state:
                    st.session_state.auto_login_attempted = True
                    time.sleep(0.5)  # Small delay for UI
                    login_callback(saved_credentials['username'], saved_credentials['password'], remember_me=True)
            
            # Show forget credentials option if credentials are saved
            if saved_credentials:
                st.markdown("<div style='text-align: center; margin-top: 1rem;'>", unsafe_allow_html=True)
                if st.button("Forget saved credentials", key="forget_btn", use_container_width=True):
                    # This should trigger a callback to clear credentials
                    st.session_state.clear_credentials = True
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
        
        # Clean footer
        st.markdown("""
        <div style="margin-top: 2rem; text-align: center; color: #9ca3af; font-size: 0.875rem;">
            Powered by OpenAI & Odoo
        </div>
        """, unsafe_allow_html=True)

def render_sidebar(username, is_manual_search_mode, logout_callback):
    """
    Render the clean ChatGPT-style sidebar
    
    Args:
        username: Current user's username
        is_manual_search_mode: Boolean for manual search mode
        logout_callback: Function to call when logout is clicked
    """
    with st.sidebar:
        # Harmonious header
        st.markdown(
            f"""
            <div style="padding: 1.5rem 0.75rem; text-align: center; margin-bottom: 1rem;">
              <div style="font-weight: 700; color: #9B6DD6; font-size: 16px; margin-bottom: 0.5rem; word-wrap: break-word; overflow-wrap: break-word; hyphens: auto; line-height: 1.3;">{username}</div>
              <div style="color: #6e7681; font-size: 12px; background: rgba(155, 109, 214, 0.1); padding: 0.25rem 0.75rem; border-radius: 12px; display: inline-block;">● Online</div>
            </div>
            <div style="height: 1px; background: linear-gradient(90deg, transparent, rgba(155, 109, 214, 0.3), transparent); margin: 0 0 1.5rem 0;"></div>
            """,
            unsafe_allow_html=True,
        )

        # Removed legacy last completed flow card to avoid duplication

        # Recent Activities list
        activities = get_recent_activities()
        st.markdown("""
            <div style="font-weight: 600; color: #9B6DD6; margin: 0.5rem 1rem 0.5rem 1rem; font-size: 14px; display: flex; align-items: center;">
                <span style="margin-right: 0.5rem;">🕘</span>Recent Activities
            </div>
        """, unsafe_allow_html=True)

        if activities:
            # Render up to 6 most recent items
            for act in activities[:6]:
                icon = act.get('icon', '📋')
                title = act.get('title', 'Activity')
                summary = act.get('summary', '')
                ts = act.get('timestamp', '')
                when = format_activity_time(ts)
                st.markdown(
                    f"""
                    <div style="background: rgba(255, 255, 255, 0.8); border: 1px solid rgba(155, 109, 214, 0.15); padding: 0.75rem 1rem; border-radius: 12px; margin: 0.5rem 1rem; box-shadow: 0 2px 8px rgba(155, 109, 214, 0.08);">
                      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                        <span>{icon}</span>
                        <div style="font-weight: 600; color: #2d333a; font-size: 13px;">{title}</div>
                        <div style="margin-left: auto; color: #6e7681; font-size: 12px;">{when}</div>
                      </div>
                      <div style="font-size: 12px; color: #6e7681; line-height: 1.4;">{summary}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.markdown("""
                <div style="color: #6e7681; font-size: 12px; margin: 0 1rem 0.5rem 1rem;">No activities yet</div>
            """, unsafe_allow_html=True)

        # Settings section
        st.markdown("""
            <div style="font-weight: 600; color: #9B6DD6; margin: 1.5rem 1rem 0.75rem 1rem; font-size: 14px; display: flex; align-items: center;">
                <span style="margin-right: 0.5rem;">⚙️</span>Settings
            </div>
        """, unsafe_allow_html=True)
        
        show_debug = st.toggle("Debug mode", value=st.session_state.get('show_debug', False), key='debug_toggle')
        manual_mode = st.toggle("Manual search", value=is_manual_search_mode, key='manual_mode_toggle')

        if show_debug != st.session_state.get('show_debug', False):
            st.session_state.show_debug = show_debug
            st.rerun()
        if manual_mode != st.session_state.get('manual_search_mode', False):
            st.session_state.manual_search_mode = manual_mode
            st.rerun()

        # Logout button
        st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
        if st.button("Sign out", use_container_width=True):
            logout_callback()

def render_chat_message(message, message_type="user"):
    """
    Render a single chat message in WhatsApp-like style
    
    Args:
        message: Message content
        message_type: "user" or "bot"
    """
    if message_type == "user":
        # User messages on the right
        st.markdown(f"""
        <div class="chat-message-wrapper chat-message-user">
            <div class="chat-bubble user-bubble">
                {message}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Bot messages on the left
        st.markdown(f"""
        <div class="chat-message-wrapper chat-message-bot">
            <div class="chat-bubble bot-bubble">
                {message}
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_empty_state(is_manual_mode):
    """
    Render the beautiful empty state when no employee data is loaded
    
    Args:
        is_manual_mode: Boolean indicating if in manual search mode
    """
    if is_manual_mode:
        st.markdown("""
        <div style="text-align: center; padding: 4rem 2rem; background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(15px); border-radius: 20px; margin: 2rem 0; border: 1px solid rgba(155, 109, 214, 0.2); box-shadow: 0 8px 32px rgba(155, 109, 214, 0.15);">
            <div style="font-size: 3rem; margin-bottom: 1rem;">🔍</div>
            <div style="font-size: 1.5rem; font-weight: 600; color: #9B6DD6; margin-bottom: 1rem;">
                Ready to explore employee data
            </div>
            <div style="font-size: 1.1rem; color: #6e7681; line-height: 1.6;">
                Enter a name in the sidebar and click 'Search' to get started.<br>
                I'll help you analyze and understand employee information.
            </div>
            <div style="margin-top: 2rem; display: flex; justify-content: center; gap: 1rem;">
                <div style="padding: 0.5rem 1rem; background: rgba(155, 109, 214, 0.1); border-radius: 20px; font-size: 0.9rem; color: #8B5CF6;">Search by name</div>
                <div style="padding: 0.5rem 1rem; background: rgba(155, 109, 214, 0.1); border-radius: 20px; font-size: 0.9rem; color: #8B5CF6;">Get insights</div>
                <div style="padding: 0.5rem 1rem; background: rgba(155, 109, 214, 0.1); border-radius: 20px; font-size: 0.9rem; color: #8B5CF6;">Generate reports</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Add the loading animation CSS first
        st.markdown("""
        <style>
        @keyframes loading {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Then add the loading state HTML
        st.markdown("""
        <div style="text-align: center; padding: 4rem 2rem; background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(15px); border-radius: 20px; margin: 2rem 0; border: 1px solid rgba(155, 109, 214, 0.2); box-shadow: 0 8px 32px rgba(155, 109, 214, 0.15);">
            <div style="font-size: 3rem; margin-bottom: 1rem;">⚡</div>
            <div style="font-size: 1.5rem; font-weight: 600; color: #9B6DD6; margin-bottom: 1rem;">
                Loading your data...
            </div>
            <div style="font-size: 1.1rem; color: #6e7681; line-height: 1.6;">
                Your employee information will load automatically.<br>
                Please wait while I prepare your personalized assistant.
            </div>
            <div style="margin-top: 2rem;">
                <div style="width: 200px; height: 4px; background: rgba(155, 109, 214, 0.2); border-radius: 2px; margin: 0 auto; position: relative; overflow: hidden;">
                    <div style="width: 100%; height: 100%; background: linear-gradient(90deg, transparent, #9B6DD6, transparent); animation: loading 1.5s infinite; position: absolute;"></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_search_result(found, name):
    """
    Display search result
    
    Args:
        found: Boolean indicating if employee was found
        name: Name of the employee searched
    """
    if found:
        st.markdown(f"""
        <div style="display: flex; align-items: center;">
            <div style="background-color: var(--primary-purple); width: 8px; height: 8px; border-radius: 50%; margin-right: 8px;"></div>
            <span style="color: var(--dark-purple); font-weight: 600;">Found:</span> {name}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="display: flex; align-items: center;">
            <div style="background-color: #FF6B6B; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px;"></div>
            <span style="color: var(--dark-purple); font-weight: 600;">Not found:</span> {name}
        </div>
        """, unsafe_allow_html=True)
