# streamlit_app.py
import os
import re
import json
import uuid
import time
import requests
import streamlit as st
from datetime import datetime

# =========================
# Config
# =========================
DEFAULT_WEBHOOK_URL_TEST = os.getenv(
    "N8N_WEBHOOK_URL_TEST",
    "http://localhost:5678/webhook-test/fb032013-9f36-4f3b-82f1-33f2fe2e5380"
)
DEFAULT_WEBHOOK_URL_PROD = os.getenv(
    "N8N_WEBHOOK_URL_PROD",
    "http://localhost:5678/webhook/fb032013-9f36-4f3b-82f1-33f2fe2e5380"  # paste your exact Production URL if different
)
DEFAULT_TIMEOUT_SECS = int(os.getenv("N8N_TIMEOUT_SECS", "120"))

# Regex helpers (optional: parse model-suggested actions/options from text)
ACTION_RE  = re.compile(r"^ACTION:\s*(\{[\s\S]*\})\s*$",  re.MULTILINE)
OPTIONS_RE = re.compile(r"^OPTIONS:\s*(\[[\s\S]*\])\s*$", re.MULTILINE)

# =========================
# Page setup & styles
# =========================
st.set_page_config(
    page_title="CSR Agent",
    page_icon="🎧",
    layout="centered",
)

st.markdown("""
<style>
:root { --st-topbar: 56px; }     /* Streamlit top bar height (approx) */
:root { --app-header-h: 96px; }  /* Your fixed header height */

/* Let the main container start *below* the fixed header */
.block-container {
  padding-top: calc(var(--st-topbar) + var(--app-header-h) + 16px) !important;
  margin-top: 0 !important;
}

/* Full-width fixed header, centered inner content */
.app-header {
  position: fixed;
  top: var(--st-topbar);
  left: 0;
  right: 0;
  width: 100%;
  background: linear-gradient(90deg,#0F172A,#111827);
  color: #E5E7EB;
  z-index: 1000;
  border-radius: 0 0 12px 12px;
  box-shadow: 0 6px 16px rgba(0,0,0,0.15);
  display: flex;
  justify-content: center;
}

.app-header-inner {
  width: 100%;
  max-width: 800px;
  padding: 14px 16px;
}

.app-header h1 {
  font-size: 20px;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  letter-spacing: .2px;
}
.meta { font-size: 12px; color: #9CA3AF; }

/* Optional: give top toolbar buttons a tiny breathing room */
.stButton > button {
  margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="app-header">
  <div class="app-header-inner">
    <h1>🎧 CSR Agent Assistant</h1>
    <div class="meta">Ask about orders, fulfillment, or tickets.</div>
  </div>
</div>
""", unsafe_allow_html=True)

# =========================
# Sidebar Settings
# =========================
with st.sidebar:
    st.subheader("Settings")
    env_choice = st.radio("Webhook Environment", ["Test URL", "Production URL"], horizontal=True)
    default_url = DEFAULT_WEBHOOK_URL_TEST if env_choice == "Test URL" else DEFAULT_WEBHOOK_URL_PROD
    webhook_url = st.text_input("n8n Webhook URL", value=default_url)
    timeout_secs = st.number_input("Request timeout (sec)", min_value=10, max_value=300, value=DEFAULT_TIMEOUT_SECS, step=5)
    st.caption("Tip: Use the Webhook node’s Test URL while building; switch to Production once activated.")

# =========================
# Session state
# =========================
if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex
if "messages" not in st.session_state:
    st.session_state.messages = []   # [{role, content, ts}]
if "pending_action" not in st.session_state:
    st.session_state.pending_action = None  # dict or None

def add_message(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content, "ts": time.time()})

def clear_chat():
    st.session_state.messages = []
    st.session_state.pending_action = None
    st.session_state.session_id = uuid.uuid4().hex  # new session for memory isolation

# =========================
# HTTP helpers
# =========================
def post_webhook(payload: dict, url: str = None):
    """Send JSON to n8n webhook."""
    if url is None:
        url = webhook_url
    return requests.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=timeout_secs,
    )

def safe_parse_response(resp):
    """
    Returns (agent_text, data_json_or_none).
    - Accepts JSON arrays like: [{"output": "..."}] and returns the first item's 'output' (or similar)
    - Accepts JSON dicts and prefers common keys
    - Falls back to raw text if not JSON
    """
    data = None
    try:
        data = resp.json()
    except Exception:
        data = None

    if isinstance(data, list) and len(data) > 0:
        first = data[0]
        if isinstance(first, dict):
            for k in ["output", "answer", "message", "text", "result"]:
                if k in first and isinstance(first[k], (str, int, float, bool)):
                    return str(first[k]), data
            try:
                return "```json\n" + json.dumps(first, indent=2) + "\n```", data
            except Exception:
                return str(first), data
        try:
            return "```json\n" + json.dumps(data, indent=2) + "\n```", data
        except Exception:
            return str(data), data

    if isinstance(data, dict):
        for k in ["output", "answer", "result", "message", "text"]:
            if k in data and isinstance(data[k], (str, int, float, bool)):
                return str(data[k]), data
        try:
            return "```json\n" + json.dumps(data, indent=2) + "\n```", data
        except Exception:
            return str(data), data

    return resp.text.strip(), None

# =========================
# Header actions (now render just below the fixed header)
# =========================
cols = st.columns([1,1,1,1])
with cols[-1]:
    if st.button("🧹 New Chat", use_container_width=True):
        clear_chat()
        st.rerun()

# =========================
# Render history
# =========================
for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "🤖"
    with st.chat_message("user" if msg["role"] == "user" else "assistant", avatar=avatar):
        st.markdown(msg["content"])

# =========================
# Chat input
# =========================
user_input = st.chat_input("Type your message (e.g., 'Is the order returnable?').")
if user_input:
    add_message("user", user_input)
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    payload = {
        "sessionId": st.session_state.session_id,
        "action": "sendMessage",
        "chatInput": user_input,
    }

    agent_text = None
    error_text = None
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Agent thinking..."):
            try:
                resp = post_webhook(payload, webhook_url)
                if resp.ok:
                    agent_text, _ = safe_parse_response(resp)
                else:
                    error_text = f"n8n error: {resp.status_code} — {resp.text}"
            except requests.exceptions.RequestException as e:
                error_text = f"Request failed: {e}"

        if error_text:
            st.error(error_text)
            add_message("assistant", f"**Error:** {error_text}")
        else:
            agent_text = agent_text or "_(No content returned by webhook)_"
            st.markdown(agent_text)
            add_message("assistant", agent_text)

            # ==== ACTION (confirmation for state-changing ops) ====
            def extract_action_block(text: str):
                if not text:
                    return None
                m = ACTION_RE.search(text)
                if not m:
                    return None
                try:
                    return json.loads(m.group(1))
                except json.JSONDecodeError:
                    return None

            action = extract_action_block(agent_text)
            if action:
                st.session_state.pending_action = action
                st.info("Confirmation required before performing this action.")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Yes, proceed", use_container_width=True, key="confirm_yes"):
                        confirm_payload = {
                            "sessionId": st.session_state.session_id,
                            "action": "confirmAction",
                            "pendingAction": st.session_state.pending_action,
                        }
                        try:
                            resp2 = post_webhook(confirm_payload, webhook_url)
                            if resp2.ok:
                                result_text, _ = safe_parse_response(resp2)
                                st.session_state.pending_action = None
                                add_message("assistant", result_text)
                                st.markdown(result_text)
                            else:
                                st.error(f"n8n error: {resp2.status_code} — {resp2.text}")
                        except requests.exceptions.RequestException as e:
                            st.error(f"Request failed: {e}")
                with c2:
                    if st.button("❌ No, cancel", use_container_width=True, key="confirm_no"):
                        st.session_state.pending_action = None
                        cancel_text = "Okay, I’ve canceled that request. How else can I help?"
                        add_message("assistant", cancel_text)
                        st.markdown(cancel_text)

            # ==== OPTIONS (quick actions) ====
            def extract_options_block(text: str):
                if not text:
                    return []
                m = OPTIONS_RE.search(text)
                if not m:
                    return []
                try:
                    data = json.loads(m.group(1))
                    if isinstance(data, list):
                        norm = []
                        for opt in data:
                            if isinstance(opt, dict) and "label" in opt and "intent" in opt:
                                norm.append({
                                    "label": opt["label"],
                                    "intent": opt["intent"],
                                    "args": opt.get("args", {})
                                })
                        return norm
                    return []
                except Exception:
                    return []

            options = extract_options_block(agent_text)
            if options:
                st.markdown("**Suggested actions**")
                grid = st.columns(min(3, len(options)))
                for idx, opt in enumerate(options):
                    with grid[idx % len(grid)]:
                        if st.button(opt["label"], use_container_width=True, key=f"opt_{idx}"):
                            followup_payload = {
                                "sessionId": st.session_state.session_id,
                                "action": "quickIntent",
                                "intent": opt["intent"],
                                "args": opt.get("args", {}),
                            }
                            try:
                                resp3 = post_webhook(followup_payload, webhook_url)
                                if resp3.ok:
                                    text, _ = safe_parse_response(resp3)
                                    add_message("assistant", text)
                                    st.markdown(text)
                                else:
                                    st.error(f"n8n error: {resp3.status_code} — {resp3.text}")
                            except requests.exceptions.RequestException as e:
                                st.error(f"Request failed: {e}")

# Footer (optional)
# st.markdown(
#     '<div class="footer-note">Powered by n8n • FastAPI (MCP) • RAG Policies • Streamlit</div>',
#     unsafe_allow_html=True
# )
