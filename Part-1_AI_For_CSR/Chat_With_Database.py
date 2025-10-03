from langchain_openai import ChatOpenAI # This is used to call the OpenAI LLM model
from langchain_ollama import ChatOllama # This is used to call the Ollama LLM model
from dotenv import load_dotenv
import os
from langchain_core.output_parsers import StrOutputParser
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
import re
import streamlit as st


# --- Setup ---
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# initiate the model. Uncomment this and comment the above two lines to use Ollama model
# llm = ChatOllama(
#     model="llama3.3",
#     temperature=0
# )

# connect to the database
sqlite_uri = 'sqlite:///./orders_testing.db'
db = SQLDatabase.from_uri(sqlite_uri)
schema = db.get_table_info()

# define the prompt template to generate SQL query
SQL_PROMPT = ChatPromptTemplate.from_template(
    (
        "You are a SQL expert. Based on the table schema and conversation history, write a SQL query that answers the latest question.\n"
        "Return ONLY the SQL query without explanations or extra text.\n\n"
        "Schema:\n{schema}\n\n"
        "Conversation History:\n{history_text}\n\n"
        "Latest Question: {question}\n"
        "SQL Query:"
    )
)

def history_to_text(history_pairs):
    """history_pairs is a list of tuples: [(user_q, assistant_a), ...]."""
    if not history_pairs:
        return "None"
    return "".join(f"User: {q}\nAssistant: {a}\n" for q, a in history_pairs)

def extract_sql_code(text: str) -> str:
    fenced = re.findall(r"```(?:sql)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    cleaned = fenced[0] if fenced else text
    return cleaned.strip().strip("`").strip()

def run_query(query: str):
    return db.run(query)

# --- State ---
if "chat_pairs" not in st.session_state:
    # store pairs specifically for the prompt context [(question, assistant_response)]
    st.session_state.chat_pairs = []
if "messages" not in st.session_state:
    # store UI messages for chat rendering: [{"role": "user"/"assistant", "content": "..."}]
    st.session_state.messages = []
if "last_sql_query" not in st.session_state:
    st.session_state.last_sql_query = ""

st.set_page_config(page_title="SQL Chatbot", page_icon="🗃️")
st.title("Chat with your Database 🗃️")

# --- Controls ---
cols = st.columns(2)
with cols[0]:
    clear = st.button("Clear chat")
with cols[1]:
    show_schema = st.checkbox("Show schema", value=False)

if clear:
    st.session_state.messages = []
    st.session_state.chat_pairs = []
    st.session_state.last_sql_query = ""
    st.rerun()

if show_schema:
    with st.expander("Database schema"):
        st.code(schema, language="sql")

# --- Render existing conversation every run ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- Chat input (submit triggers a rerun) ---
user_question = st.chat_input("Ask a question about your orders data…")
if user_question:
    # 1) Echo the user message immediately
    st.session_state.messages.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    # 2) Build inputs for SQL generation
    inputs = {
        "schema": schema,
        "history_text": history_to_text(st.session_state.chat_pairs),
        "question": user_question
    }

    # 3) Build chain: PROMPT -> LLM -> str
    sql_chain = (
        SQL_PROMPT
        | llm.bind(stop=["\nSQLResult:", "\nUser:", "User:", "Assistant:"])
        | StrOutputParser()
    )

    raw_sql = sql_chain.invoke(inputs)
    sql_query = extract_sql_code(raw_sql)

    # 4) Run query and prepare assistant reply
    try:
        result = run_query(sql_query)
    except Exception as e:
        result = f"Query execution error: {e}"

    assistant_response_md = (
        # "### Generated SQL Query\n"
        # f"```sql\n{sql_query}\n```\n\n"
        # "### Query Result\n"
        # f"{result}"
        f" "

    )

    # 4b) Generate natural language explanation using LLM
    nl_prompt = ChatPromptTemplate.from_template(
        (
            "You are a helpful assistant. Given the user's question, the generated SQL query, and the query result, provide the response to user in a natural language using the output from query.\n\n"
            "User Question: {question}\n"
            "SQL Query: {sql_query}\n"
            "Query Result: {result}\n\n"
            "Explanation:"
        )
    )
    nl_inputs = {
        "question": user_question,
        "sql_query": sql_query,
        "result": result
    }
    nl_chain = nl_prompt | llm | StrOutputParser()
    nl_response = nl_chain.invoke(nl_inputs)

    # assistant_response_md += f"\n\n### Explanation\n{nl_response}"
    assistant_response_md += f"\n{nl_response}"

    # 5) Show assistant reply in the chat and persist to state
    with st.chat_message("assistant"):
        st.markdown(assistant_response_md)

    st.session_state.messages.append({"role": "assistant", "content": assistant_response_md})
    st.session_state.chat_pairs.append((user_question, f"SQL Query:\n{sql_query}\n\nResult:\n{result}"))
    st.session_state.last_sql_query = sql_query

    print("Question asked by user: ", user_question)
    print("SQL Query generated: ", sql_query)
    print("Result from the query: ", result)
    print("Natural language response: ", nl_response)
