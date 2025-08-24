# style_manager.py
import streamlit as st
import os

class StyleManager:
    def __init__(self, css_file="style.css"):
        self.css_file = css_file
    
    def load_css(self):
        """
        Final bubble layout:
        • Orange-icon user → right, white bubble
        • Yellow-icon bot  → left, light-purple bubble
        • Icons now perfectly centred vertically beside the bubble
        """
        import streamlit as st, os, textwrap

        # keep your own stylesheet first
        if os.path.exists(self.css_file):
            with open(self.css_file) as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

        st.markdown(
            textwrap.dedent(
                """
                <style>
                #MainMenu, footer {visibility:hidden;}
                .user-bubble {
                    display: flex;
                    flex-direction: row-reverse;
                    align-items: center;
                    background: #B794E6; /* lighter purple */
                    color: #fff;
                    border-radius: 18px 18px 4px 18px;
                    margin-left: auto;
                    margin-right: 0;
                    max-width: 70%;
                    padding: 12px 16px;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                    text-align: left;
                    margin-bottom: 8px;
                }
                .user-bubble span {
                    flex: 1;
                    text-align: left;
                }
                .bot-bubble {
                    background: #fff;
                    color: #2B1B4C;
                    border: 1px solid #E5E5E5;
                    border-radius: 18px 18px 18px 4px;
                    margin-right: auto;
                    margin-left: 0;
                    max-width: 70%;
                    padding: 12px 16px;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                    text-align: left;
                    margin-bottom: 8px;
                }
                /* Hide user and assistant avatars */
                img[alt="User"], img[alt="Assistant"] {
                    display: none !important;
                }
                /* Hide all avatars/emojis in chat messages */
                div[data-testid="stChatMessage"] img {
                    display: none !important;
                }
                div[data-testid="stChatMessage"] > div:first-child {
                    display: none !important;
                }
                </style>
                """
            ),
            unsafe_allow_html=True,
        )

    def _load_fallback_css(self):
        """Load fallback CSS if file doesn't exist"""
        fallback_css = """
        <style>
        /* Your fallback CSS here */
        </style>
        """
        st.markdown(fallback_css, unsafe_allow_html=True)