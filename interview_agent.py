import streamlit as st
import os
import time
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="ElevenLabs AI Interview Agent",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Get API credentials
AGENT_ID = os.getenv("AGENT_ID")
API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_active" not in st.session_state:
    st.session_state.conversation_active = False
if "conversation_obj" not in st.session_state:
    st.session_state.conversation_obj = None
if "error_count" not in st.session_state:
    st.session_state.error_count = 0

# Custom audio interface with better error handling
class RobustAudioInterface(DefaultAudioInterface):
    def stop(self):
        try:
            if hasattr(self, 'in_stream') and self.in_stream:
                self.in_stream.stop_stream()
                self.in_stream.close()
        except Exception as e:
            st.warning(f"Audio cleanup warning: {e}")
        
        try:
            if hasattr(self, 'out_stream') and self.out_stream:
                self.out_stream.stop_stream()
                self.out_stream.close()
        except Exception as e:
            st.warning(f"Audio output cleanup warning: {e}")
        
        try:
            if hasattr(self, 'pa') and self.pa:
                self.pa.terminate()
        except Exception as e:
            st.warning(f"PyAudio termination warning: {e}")

# Sidebar configuration
with st.sidebar:
    st.header("🎤 Agent Configuration")
    
    if AGENT_ID and API_KEY:
        st.success("✅ API credentials loaded")
        st.info(f"Agent ID: {AGENT_ID[:8]}...")
    else:
        st.error("❌ Missing API credentials in .env file")
    
    st.divider()
    st.header("🎛️ Controls")
    
    # Start conversation with enhanced error handling
    if st.button("🎙️ Start Voice Conversation", 
                disabled=st.session_state.conversation_active or not (AGENT_ID and API_KEY)):
        
        if AGENT_ID and API_KEY:
            try:
                # Reset error count
                st.session_state.error_count = 0
                
                # Initialize ElevenLabs client
                elevenlabs = ElevenLabs(api_key=API_KEY)
                
                # Enhanced callbacks with error handling
                def on_user_transcript(transcript):
                    try:
                        st.session_state.messages.append({"role": "user", "content": transcript})
                    except Exception as e:
                        st.error(f"Error processing user transcript: {e}")
                
                def on_agent_response(response):
                    try:
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    except Exception as e:
                        st.error(f"Error processing agent response: {e}")
                
                # Create conversation with robust audio interface
                conversation = Conversation(
                    elevenlabs,
                    AGENT_ID,
                    requires_auth=bool(API_KEY),
                    audio_interface=RobustAudioInterface(),
                    callback_user_transcript=on_user_transcript,
                    callback_agent_response=on_agent_response,
                )
                
                # Start session with timeout handling
                conversation.start_session()
                
                st.session_state.conversation_obj = conversation
                st.session_state.conversation_active = True
                
                st.success("🎙️ Voice conversation started!")
                st.rerun()
                
            except Exception as e:
                st.session_state.error_count += 1
                st.error(f"Failed to start conversation (Attempt {st.session_state.error_count}): {str(e)}")
                
                if st.session_state.error_count >= 3:
                    st.error("Multiple connection failures. Please check your audio device settings.")
    
    # Stop conversation with proper cleanup
    if st.button("⏹️ Stop Voice Conversation", 
                disabled=not st.session_state.conversation_active):
        
        if st.session_state.conversation_obj:
            try:
                st.session_state.conversation_obj.end_session()
                st.session_state.conversation_active = False
                st.session_state.conversation_obj = None
                st.success("Voice conversation stopped.")
                st.rerun()
            except Exception as e:
                st.warning(f"Cleanup warning: {str(e)}")
                # Force reset even if cleanup fails
                st.session_state.conversation_active = False
                st.session_state.conversation_obj = None
                st.rerun()
    
    # Clear chat history
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()
    
    # Status and troubleshooting info
    if st.session_state.conversation_active:
        st.success("🔴 Voice conversation active")
    else:
        st.info("⚪ Voice conversation inactive")
    
    if st.session_state.error_count > 0:
        st.warning(f"⚠️ Error count: {st.session_state.error_count}")

# Main interface
st.title("🎤 ElevenLabs AI Interview Agent")
st.markdown("**Jordan** - Your Technical Interview Assistant")

# Display conversation status and troubleshooting
if st.session_state.conversation_active:
    st.info("🎙️ Voice conversation is active. Speak into your microphone!")
elif st.session_state.error_count > 0:
    st.warning("⚠️ Audio issues detected. Try the troubleshooting steps below.")

# Chat display
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Text input fallback
if not st.session_state.conversation_active:
    if prompt := st.chat_input("Type your message here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.write(prompt)
        
        with st.chat_message("assistant"):
            response = f"I received: '{prompt}'. Start voice conversation for full capabilities!"
            st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

# Auto-refresh with reduced frequency to minimize resource usage
if st.session_state.conversation_active:
    time.sleep(2)  # Increased sleep time to reduce resource contention
    st.rerun()

# Troubleshooting section
st.markdown("---")
st.markdown("## 🔧 Troubleshooting Audio Issues")

with st.expander("Common Solutions"):
    st.markdown("""
    **If you're experiencing audio errors:**
    
    1. **Check Audio Device Access**
       - Ensure your microphone is not being used by other applications
       - Close other audio applications (Discord, Zoom, etc.)
       - Check Windows audio device permissions
    

    
    2. **Connection Problems**
       - Check your internet connection stability
       - Verify your ElevenLabs API key and agent ID
       - Try restarting the conversation after a few seconds
    """)
