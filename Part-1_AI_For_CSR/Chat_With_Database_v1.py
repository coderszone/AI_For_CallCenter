from dotenv import load_dotenv
import os, re
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.utilities import SQLDatabase

# ---------------- Setup ----------------
load_dotenv()
st.set_page_config(page_title="CSR DB Assistant (Part 1)", page_icon="🗃️", layout="wide")
st.title("Chat with your Orders Database 🗃️")

# Sidebar controls
with st.sidebar:
    st.header("Settings")
    provider = st.selectbox("LLM Provider", ["OpenAI", "Ollama"])
    temperature = st.slider("Temperature", 0.0, 1.0, 0.0, 0.1)
    show_sql = st.checkbox("Show generated SQL", value=False)
    show_schema = st.checkbox("Show schema", value=False)
    max_rows = st.number_input("Max rows per query", min_value=10, max_value=1000, value=200, step=10)

# LLM selection
if provider == "OpenAI":
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.warning("OPENAI_API_KEY not found. Set it in your environment to use OpenAI.")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=temperature)
else:
    llm = ChatOllama(model="llama3.3", temperature=temperature)

# DB connect (SQLite file in working dir)
sqlite_uri = "sqlite:///./orders_testing.db"
try:
    db = SQLDatabase.from_uri(sqlite_uri)
except Exception as e:
    st.error(f"Database connection failed: {e}")
    st.stop()

# Cache schema for speed
@st.cache_data(show_spinner=False)
def get_schema(_db: SQLDatabase) -> str:
    return _db.get_table_info()

schema = get_schema(db)

if show_schema:
    with st.expander("Database schema", expanded=False):
        st.code(schema, language="sql")

# ---------------- Helpers ----------------
def history_to_text(history_pairs, max_turns=6):
    """Convert [(user, assistant), ...] → text, keep last N turns."""
    if not history_pairs:
        return "None"
    trimmed = history_pairs[-max_turns:]
    return "\n".join([f"User: {u}\nAssistant: {a}" for (u, a) in trimmed])

FENCE_RE = re.compile(r"```(?:sql)?\s*([\s\S]*?)```", flags=re.IGNORECASE)

def extract_sql_code(text: str) -> str:
    m = FENCE_RE.findall(text)
    cleaned = (m[0] if m else text).strip().strip("`").strip()
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1]
    return cleaned.strip()

MUTATING_RE = re.compile(r"^\s*(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE)\b", re.I)

def is_safe_select(sql: str) -> bool:
    return (not MUTATING_RE.search(sql)) and bool(re.match(r"^\s*SELECT\b", sql, re.I))

def enforce_limit(sql: str, max_rows: int) -> str:
    if re.search(r"\bLIMIT\b", sql, re.I):
        return sql
    return sql + f" LIMIT {int(max_rows)}"

def run_query_safe(sql: str):
    return db.run(sql)

# ---------------- Prompts/Chains ----------------
SQL_PROMPT = ChatPromptTemplate.from_template(
    "You are a SQL expert for SQLite.\n"
    "Write ONLY a single-line SELECT statement (no comments, no prose, no code fences, no mutating operations) "
    "that answers the question using the provided schema and conversation history.\n\n"
    "Schema:\n{schema}\n\n"
    "Conversation History:\n{history_text}\n\n"
    "Latest Question: {question}\n"
    "SQL:"
)

sql_chain = (SQL_PROMPT | llm.bind(stop=["\nUser:", "\nAssistant:", "Assistant:", "User:"]) | StrOutputParser())

NL_PROMPT = ChatPromptTemplate.from_template(
    "You are a helpful assistant. Using the user's question, the SQL query, and the SQL result, "
    "produce a concise, accurate answer grounded ONLY in the result (no speculation). "
    "If the result is empty, state that clearly and suggest a clarifying question.\n\n"
    "User Question: {question}\n"
    "SQL Query: {sql}\n"
    "SQL Result: {result}\n\n"
    "Answer:"
)
nl_chain = (NL_PROMPT | llm | StrOutputParser())

# ---------------- Session State ----------------
st.session_state.setdefault("chat_pairs", [])
st.session_state.setdefault("messages", [])
st.session_state.setdefault("last_sql", "")

# Render history
for m in st.session_state["messages"]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

cols = st.columns(2)
with cols[0]:
    if st.button("Clear chat"):
        st.session_state["chat_pairs"] = []
        st.session_state["messages"] = []
        st.session_state["last_sql"] = ""
        st.rerun()
with cols[1]:
    st.caption("Part 1 MVP: single-DB, read-only assistant (no MCP)")

# ---------------- Chat loop ----------------
user_q = st.chat_input("Ask a question about your orders (e.g., recent orders by state, top items, refunds)…")
if user_q:
    st.session_state["messages"].append({"role": "user", "content": user_q})
    with st.chat_message("user"):
        st.markdown(user_q)

    inputs = {
        "schema": schema,
        "history_text": history_to_text(st.session_state["chat_pairs"]),
        "question": user_q,
    }

    # 1) Generate SQL
    raw_sql = sql_chain.invoke(inputs)
    sql = extract_sql_code(raw_sql)

    # Guardrails
    if not is_safe_select(sql):
        guardrail_msg = (
            "⚠️ I generated a potentially unsafe SQL statement.\n\n"
            "For this MVP, I only run **read-only SELECT queries**. "
            "Please rephrase your request."
        )
        with st.chat_message("assistant"):
            st.error(guardrail_msg)  # red warning style
        st.session_state["messages"].append({"role": "assistant", "content": guardrail_msg})

        # Print to console for debugging
        print("----- GUARDRAIL BLOCKED -----")
        print("User Prompt:", user_q)
        print("Generated SQL (blocked):", sql)
        print("-----------------------------")
        st.stop()

    # Enforce LIMIT
    sql = enforce_limit(sql, max_rows)
    st.session_state["last_sql"] = sql

    # 2) Execute
    try:
        result = run_query_safe(sql)
    except Exception as e:
        result = f"Query execution error: {e}"

    # 3) Natural language response
    nl = nl_chain.invoke({"question": user_q, "sql": sql, "result": result})

    # 4) Render assistant message
    parts = []
    if show_sql:
        parts.append("**Generated SQL**\n```sql\n" + sql + "\n```")
    parts.append(nl)
    assistant_out = "\n\n".join(parts)

    with st.chat_message("assistant"):
        st.markdown(assistant_out)

    st.session_state["messages"].append({"role": "assistant", "content": assistant_out})
    st.session_state["chat_pairs"].append((user_q, f"SQL: {sql}\nResult: {str(result)[:500]}"))

    # ----- Console logging -----
    print("----- CHAT LOG -----")
    print("User Prompt:", user_q)
    print("Generated SQL:", sql)
    print("DB Output:", result)
    print("NLP Response:", nl)
    print("--------------------")
