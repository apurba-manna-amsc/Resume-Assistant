import streamlit as st
import time
from typing import Dict, Any
from resume_update import ResumeUpdater

class SidebarChatWidget:
    """
    Theme-aware sidebar-based chat widget for resume updates
    """
    
    def __init__(self):
        self.updater = ResumeUpdater()
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """Initialize chat session state"""
        if 'chat_messages' not in st.session_state:
            st.session_state.chat_messages = []
        if 'chat_processing' not in st.session_state:
            st.session_state.chat_processing = False
        if 'previous_input' not in st.session_state:
            st.session_state.previous_input = ""
    
    def inject_sidebar_css(self):
        """Inject theme-aware CSS for better sidebar chat styling"""
        st.markdown("""
        <style>
        /* Theme-aware CSS variables */
        :root {
            --chat-bg-primary: #ffffff;
            --chat-bg-secondary: #f8f9fa;
            --chat-border: #dee2e6;
            --chat-text: #333333;
            --chat-text-muted: #6c757d;
            --chat-success-bg: #d4edda;
            --chat-success-text: #155724;
            --chat-success-border: #c3e6cb;
            --chat-error-bg: #f8d7da;
            --chat-error-text: #721c24;
            --chat-error-border: #f5c6cb;
            --chat-user-bg: #007bff;
            --chat-user-text: #ffffff;
            --chat-shadow: rgba(0, 0, 0, 0.1);
        }

        /* Dark theme overrides */
        [data-theme="dark"], .stApp[data-theme="dark"] {
            --chat-bg-primary: #262730;
            --chat-bg-secondary: #1e1e1e;
            --chat-border: #404040;
            --chat-text: #ffffff;
            --chat-text-muted: #b3b3b3;
            --chat-success-bg: #1e3a29;
            --chat-success-text: #75dd8b;
            --chat-success-border: #2d5a3d;
            --chat-error-bg: #3a1e1e;
            --chat-error-text: #ff8a8a;
            --chat-error-border: #5a2d2d;
            --chat-user-bg: #0066cc;
            --chat-user-text: #ffffff;
            --chat-shadow: rgba(0, 0, 0, 0.3);
        }

        /* Auto-detect dark theme from Streamlit */
        @media (prefers-color-scheme: dark) {
            .stApp {
                --chat-bg-primary: #262730;
                --chat-bg-secondary: #1e1e1e;
                --chat-border: #404040;
                --chat-text: #ffffff;
                --chat-text-muted: #b3b3b3;
                --chat-success-bg: #1e3a29;
                --chat-success-text: #75dd8b;
                --chat-success-border: #2d5a3d;
                --chat-error-bg: #3a1e1e;
                --chat-error-text: #ff8a8a;
                --chat-error-border: #5a2d2d;
                --chat-user-bg: #0066cc;
                --chat-user-text: #ffffff;
                --chat-shadow: rgba(0, 0, 0, 0.3);
            }
        }

        /* Additional detection for Streamlit's dark theme class */
        .stApp[class*="dark"] {
            --chat-bg-primary: #262730;
            --chat-bg-secondary: #1e1e1e;
            --chat-border: #404040;
            --chat-text: #ffffff;
            --chat-text-muted: #b3b3b3;
            --chat-success-bg: #1e3a29;
            --chat-success-text: #75dd8b;
            --chat-success-border: #2d5a3d;
            --chat-error-bg: #3a1e1e;
            --chat-error-text: #ff8a8a;
            --chat-error-border: #5a2d2d;
            --chat-user-bg: #0066cc;
            --chat-user-text: #ffffff;
            --chat-shadow: rgba(0, 0, 0, 0.3);
        }
        
        /* Sidebar styling with theme awareness */
        .stSidebar {
            background: linear-gradient(180deg, var(--chat-bg-secondary) 0%, var(--chat-bg-primary) 100%);
        }
        
        .stSidebar .stMarkdown {
            font-size: 14px;
            color: var(--chat-text);
        }
        
        /* Chat message styling */
        .chat-message {
            padding: 10px 12px;
            margin: 8px 0;
            border-radius: 12px;
            font-size: 13px;
            line-height: 1.4;
            word-wrap: break-word;
            box-shadow: 0 1px 3px var(--chat-shadow);
            transition: all 0.2s ease;
        }
        
        .user-message {
            background: var(--chat-user-bg);
            color: var(--chat-user-text);
            margin-left: 20px;
            border-bottom-right-radius: 4px;
        }
        
        .bot-message {
            background: var(--chat-bg-primary);
            color: var(--chat-text);
            border: 1px solid var(--chat-border);
            margin-right: 20px;
            border-bottom-left-radius: 4px;
        }
        
        .success-message {
            background: var(--chat-success-bg);
            color: var(--chat-success-text);
            border: 1px solid var(--chat-success-border);
            margin-right: 20px;
            border-bottom-left-radius: 4px;
        }
        
        .error-message {
            background: var(--chat-error-bg);
            color: var(--chat-error-text);
            border: 1px solid var(--chat-error-border);
            margin-right: 20px;
            border-bottom-left-radius: 4px;
        }
        
        /* Typing indicator with theme awareness */
        .typing-indicator {
            background: var(--chat-bg-primary);
            color: var(--chat-text-muted);
            border: 1px solid var(--chat-border);
            margin-right: 20px;
            border-bottom-left-radius: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 12px;
            margin: 8px 0;
            border-radius: 12px;
            box-shadow: 0 1px 3px var(--chat-shadow);
        }
        
        .typing-dots {
            display: flex;
            gap: 3px;
        }
        
        .typing-dot {
            width: 5px;
            height: 5px;
            border-radius: 50%;
            background: var(--chat-user-bg);
            animation: typing-bounce 1.4s infinite ease-in-out;
        }
        
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }
        
        @keyframes typing-bounce {
            0%, 60%, 100% { opacity: 0.4; transform: translateY(0); }
            30% { opacity: 1; transform: translateY(-5px); }
        }
        
        /* Empty state styling with theme awareness */
        .chat-empty {
            text-align: center;
            color: var(--chat-text-muted);
            padding: 20px 10px;
            border: 2px dashed var(--chat-border);
            border-radius: 12px;
            margin: 20px 0;
            background: var(--chat-bg-primary);
            transition: all 0.2s ease;
        }
        
        .chat-empty-icon {
            font-size: 32px;
            margin-bottom: 10px;
            opacity: 0.5;
        }
        
        /* Input area improvements with theme awareness */
        .stSidebar .stTextInput > div > div > input {
            border-radius: 20px;
            border: 1px solid var(--chat-border) !important;
            padding: 8px 15px;
            font-size: 13px;
            background-color: var(--chat-bg-primary) !important;
            color: var(--chat-text) !important;
            transition: all 0.2s ease;
        }
        
        .stSidebar .stTextInput > div > div > input:focus {
            border-color: var(--chat-user-bg) !important;
            box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25) !important;
            outline: none !important;
        }
        
        .stSidebar .stTextInput > div > div > input::placeholder {
            color: var(--chat-text-muted) !important;
        }
        
        .stSidebar .stButton > button {
            background: var(--chat-user-bg) !important;
            color: var(--chat-user-text) !important;
            border-radius: 20px;
            border: none !important;
            padding: 8px 20px;
            font-size: 13px;
            font-weight: 500;
            width: 100%;
            transition: all 0.2s ease;
        }
        
        .stSidebar .stButton > button:hover {
            background: color-mix(in srgb, var(--chat-user-bg) 80%, black 20%) !important;
            transform: translateY(-1px);
        }
        
        .stSidebar .stButton > button:disabled {
            background: var(--chat-text-muted) !important;
            opacity: 0.6;
            transform: none;
        }
        
        /* Enter key hint with theme awareness */
        .enter-hint {
            font-size: 11px;
            color: var(--chat-text-muted);
            text-align: center;
            margin-top: 5px;
            font-style: italic;
        }

        /* Scrollbar styling for chat area */
        .stSidebar::-webkit-scrollbar {
            width: 4px;
        }
        
        .stSidebar::-webkit-scrollbar-track {
            background: var(--chat-bg-secondary);
        }
        
        .stSidebar::-webkit-scrollbar-thumb {
            background: var(--chat-border);
            border-radius: 2px;
        }
        
        .stSidebar::-webkit-scrollbar-thumb:hover {
            background: var(--chat-text-muted);
        }

        /* Expander styling for better theme integration */
        .stSidebar .streamlit-expanderHeader {
            background: var(--chat-bg-primary) !important;
            color: var(--chat-text) !important;
            border: 1px solid var(--chat-border) !important;
        }
        
        .stSidebar .streamlit-expanderContent {
            background: var(--chat-bg-primary) !important;
            border: 1px solid var(--chat-border) !important;
            border-top: none !important;
        }

        /* Better visual hierarchy */
        .stSidebar h3 {
            color: var(--chat-text) !important;
            font-weight: 600;
        }

        .stSidebar hr {
            border-color: var(--chat-border) !important;
            opacity: 0.3;
        }

        /* Hover effects for interactive elements */
        .chat-message:hover {
            transform: translateX(2px);
        }

        .user-message:hover {
            transform: translateX(-2px);
        }

        /* Animation for new messages */
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .chat-message {
            animation: slideIn 0.3s ease-out;
        }
        </style>
        """, unsafe_allow_html=True)
    
    def render_chat_widget(self):
        """Render the sidebar chat widget"""
        # Only show if resume data exists
        if not st.session_state.get('resume_data'):
            return
        
        # Inject CSS
        self.inject_sidebar_css()
        
        # Sidebar content
        with st.sidebar:
            st.markdown("### 🤖 Resume Assistant")
            st.markdown("---")
            
            # Chat messages area
            self.render_chat_messages()
            
            # Chat input
            self.render_chat_input()
    
    def render_chat_messages(self):
        """Render chat messages in sidebar"""
        if not st.session_state.chat_messages and not st.session_state.chat_processing:
            # Empty state
            st.markdown("""
            <div class="chat-empty">
                <div class="chat-empty-icon">💭</div>
                <div style="font-weight: 500; margin-bottom: 5px;">Ready to help!</div>
                <div style="font-size: 12px; opacity: 0.8;">Tell me how to update your resume</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Display messages (show last 8 messages to fit in sidebar)
            recent_messages = st.session_state.chat_messages[-8:]
            
            for msg in recent_messages:
                msg_class = {
                    'user': 'user-message',
                    'success': 'success-message',
                    'error': 'error-message',
                    'bot': 'bot-message'
                }.get(msg['type'], 'bot-message')
                
                icon = {
                    'user': '👤',
                    'success': '✅',
                    'error': '❌',
                    'bot': '🤖'
                }.get(msg['type'], '🤖')
                
                st.markdown(f"""
                <div class="chat-message {msg_class}">
                    {icon} {msg['content']}
                </div>
                """, unsafe_allow_html=True)
        
        # Typing indicator
        if st.session_state.chat_processing:
            st.markdown("""
            <div class="typing-indicator">
                <span>🤖 Updating resume</span>
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    def render_chat_input(self):
        """Render chat input area with Enter key support"""
        st.markdown("---")
        st.markdown("**💬 Send a message:**")
        
        # Input field with on_change callback
        user_input = st.text_input(
            "Message",
            key="sidebar_chat_input",
            placeholder="e.g., Add Python to my skills",
            disabled=st.session_state.chat_processing,
            label_visibility="collapsed",
            on_change=self.handle_input_change
        )
        
        # Enter key hint
        st.markdown('<div class="enter-hint">Press Enter to send</div>', unsafe_allow_html=True)
        
        # Send button (still available as backup)
        col1, col2 = st.columns([3, 1])
        with col1:
            send_clicked = st.button(
                "Send ➤",
                key="sidebar_send_btn",
                disabled=st.session_state.chat_processing or not user_input.strip(),
                use_container_width=True
            )
        
        with col2:
            if st.button("🗑️", key="clear_chat_btn", help="Clear chat", use_container_width=True):
                st.session_state.chat_messages = []
                st.session_state.previous_input = ""
                st.rerun()
        
        # Process message from button click
        if send_clicked and user_input.strip():
            self.process_message(user_input.strip())
        
        # Show some helpful examples
        if not st.session_state.chat_messages:
            with st.expander("💡 Example commands", expanded=False):
                st.markdown("""
                - "Add Python to my skills"
                - "Update my current role to Senior Developer"
                - "Add experience at Google"
                - "Remove old certifications"
                - "Add React to my projects"
                """)
    
    def handle_input_change(self):
        """Handle input change - triggered when Enter is pressed"""
        current_input = st.session_state.sidebar_chat_input
        
        # Check if input has changed and is not empty
        if (current_input != st.session_state.previous_input and 
            current_input.strip() and 
            not st.session_state.chat_processing):
            
            # Process the message
            self.process_message(current_input.strip())
            
            # Update previous input to prevent double processing
            st.session_state.previous_input = current_input
    
    def process_message(self, message: str):
        """Process user message and update resume"""
        # Add user message
        st.session_state.chat_messages.append({
            'type': 'user',
            'content': message,
            'timestamp': time.time()
        })
        
        # Set processing state
        st.session_state.chat_processing = True
        
        # Clear input
        st.session_state.sidebar_chat_input = ""
        st.session_state.previous_input = ""
        
        # Rerun to show the message and processing state
        st.rerun()
    
    def handle_message_processing(self):
        """Handle message processing - call this in main app"""
        if st.session_state.chat_processing and st.session_state.chat_messages:
            # Get the last user message
            last_message = None
            for msg in reversed(st.session_state.chat_messages):
                if msg['type'] == 'user':
                    last_message = msg['content']
                    break
            
            if last_message:
                try:
                    # Get current resume
                    current_resume = st.session_state.resume_data.copy()
                    
                    # Generate update commands
                    commands = self.updater.update_resume_with_groq(current_resume, last_message)
                    
                    if not commands:
                        # No valid commands
                        st.session_state.chat_messages.append({
                            'type': 'error',
                            'content': "I couldn't understand your request. Please be more specific about what you'd like to change.",
                            'timestamp': time.time()
                        })
                    else:
                        # Execute updates
                        updated_resume = self.updater.execute_resume_updates(current_resume, commands)
                        
                        # Update session state
                        st.session_state.resume_data = updated_resume
                        
                        # Add success message
                        change_count = len(commands)
                        st.session_state.chat_messages.append({
                            'type': 'success',
                            'content': f"Resume updated! Applied {change_count} change{'s' if change_count > 1 else ''}.",
                            'timestamp': time.time()
                        })
                
                except Exception as e:
                    # Add error message
                    st.session_state.chat_messages.append({
                        'type': 'error',
                        'content': f"Sorry, there was an error: {str(e)}",
                        'timestamp': time.time()
                    })
                
                finally:
                    # Reset processing state
                    st.session_state.chat_processing = False
                    st.rerun()
