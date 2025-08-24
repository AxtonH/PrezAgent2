# chat.py
import streamlit as st
from openai_helper import generate_ai_response
from ui_components import render_chat_message
from activity_tracker import track_template_generation
import base64
import time

class ChatManager:
    def __init__(self):
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize chat-related session state variables"""
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        if 'template_bytes' not in st.session_state:
            st.session_state.template_bytes = None
        if 'template_filename' not in st.session_state:
            st.session_state.template_filename = None
    
    def add_message(self, role, content):
        """Add a message to the chat history"""
        st.session_state.messages.append({"role": role, "content": content})
    
    def clear_history(self):
        """Clear chat history and any associated documents"""
        st.session_state.messages = []
        st.session_state.template_bytes = None
        st.session_state.template_filename = None

    def get_download_link(self, data: bytes, filename: str, link_text: str = "Download Employment Letter"):
        b64 = base64.b64encode(data).decode()
        href = f'data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,{b64}'
        return f'<a href="{href}" download="{filename}" style="display:inline-block;margin-top:8px;font-weight:bold;color:#6B46C1;">{link_text}</a>'

    # ─────────────────── UI / CHAT RENDERING ───────────────────
    def display_chat_interface(self, employee_data):
        """
        Draws the conversation using Streamlit's chat API
        while the CSS from StyleManager turns them into bubbles.
        """
        import streamlit as st
        from style_manager import StyleManager
        from openai_helper import generate_ai_response

        # 1️⃣  inject CSS once per page
        StyleManager().load_css()

        # 2️⃣  ensure a document generation activity is logged if a file is ready
        try:
            filename_ready = st.session_state.get("template_filename")
            file_bytes = st.session_state.get("template_bytes")
            last_logged = st.session_state.get("_last_logged_template_filename")
            if file_bytes and filename_ready and last_logged != filename_ready:
                track_template_generation(template_type="document", details={"filename": filename_ready})
                st.session_state._last_logged_template_filename = filename_ready
        except Exception:
            pass

        # 3️⃣  history
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                if msg["role"] == "user":
                    st.markdown(f'<div class="user-bubble"><span>{msg["content"]}</span></div>', unsafe_allow_html=True)
                else:
                    content = msg["content"]
                    if content == "[DOWNLOAD_LINK]":
                        if st.session_state.get("template_bytes") and st.session_state.get("template_filename"):
                            link_html = self.get_download_link(
                                st.session_state["template_bytes"],
                                st.session_state["template_filename"]
                            )
                            st.markdown(f'<div class="bot-bubble">{link_html}</div>', unsafe_allow_html=True)
                    elif content.startswith("[DOWNLOAD_LINK"):
                        if st.session_state.get("template_bytes") and st.session_state.get("template_filename"):
                            # Support custom link text: [DOWNLOAD_LINK|Custom Text]
                            link_text = "Download Employment Letter"
                            if content.startswith("[DOWNLOAD_LINK|") and content.endswith("]"):
                                link_text = content[len("[DOWNLOAD_LINK|"):-1]
                            link_html = self.get_download_link(
                                st.session_state["template_bytes"],
                                st.session_state["template_filename"],
                                link_text
                            )
                            st.markdown(f'<div class="bot-bubble">{link_html}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="bot-bubble">{content}</div>', unsafe_allow_html=True)

        # Add scroll target at the bottom of messages
        st.markdown('<div id="chat-bottom" style="height: 1px;"></div>', unsafe_allow_html=True)
        st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)

        # 4️⃣  input
        if prompt := st.chat_input(
            f"Ask a question about {employee_data['name']} or request a document"
        ):
            # user bubble
            self.add_message("user", prompt)
            with st.chat_message("user"):
                st.markdown(f'<div class="user-bubble"><span>{prompt}</span></div>', unsafe_allow_html=True)

            # bot bubble
            with st.chat_message("assistant"):
                with st.spinner("Thinking…"):
                    reply = generate_ai_response(prompt, employee_data)
                if reply is not None:
                    st.markdown(f'<div class="bot-bubble">{reply}</div>', unsafe_allow_html=True)
                    self.add_message("assistant", reply)
                else:
                    st.rerun()
        
        # Add a bottom spacer that ensures the last message is visible above fixed input
        st.markdown('<div id="scroll-anchor-bottom" style="height: 260px; width: 100%;"></div>', unsafe_allow_html=True)
        
        # Force scroll using component that can execute JavaScript
        if len(st.session_state.messages) > 0:
            import streamlit.components.v1 as components
            components.html(f"""
            <script>
            (function() {{
              var attempts = 0;
              function doScroll() {{
                attempts += 1;
                var parentDoc = parent.document;
                
                // 1) Scroll the explicit anchor if present
                var anchor = parentDoc.querySelector('#scroll-anchor-bottom') || parentDoc.querySelector('#chat-bottom');
                if (anchor && anchor.scrollIntoView) {{
                  anchor.scrollIntoView({{ behavior: 'smooth', block: 'end' }});
                  // Nudge past the fixed input overlay
                  setTimeout(function() {{ parent.window.scrollBy(0, 420); }}, 80);
                }}
                
                // 2) Also scroll the last chat message
                var container = parentDoc.querySelector('[data-testid="stChatMessageContainer"]');
                if (container) {{
                  var children = container.querySelectorAll('[data-testid="stChatMessage"]');
                  if (children && children.length) {{
                    var last = children[children.length - 1];
                    if (last && last.scrollIntoView) {{
                      last.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
                      setTimeout(function() {{ parent.window.scrollBy(0, 420); }}, 100);
                    }}
                  }} else {{
                    // Fallback: force container scroll
                    container.scrollTop = container.scrollHeight + 800;
                  }}
                }}
                
                // 3) Fallback to window scroll
                parent.window.scrollTo(0, parentDoc.body.scrollHeight + 800);
                
                // Retry a few times to catch post-render updates
                if (attempts < 10) {{
                  setTimeout(doScroll, 300);
                }}
              }}
              setTimeout(doScroll, 500);
            }})();
            </script>
            """, height=0)

