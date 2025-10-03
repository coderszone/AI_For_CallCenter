# AI_For_CallCenter

The code in the following Repo, performs the following action. The user can interact with the 

### Files in the Repo
Chat_With_Database.py - This is the working version. 
    LLM : Open AI 
    UI: Streamlit
    Database: SQLite
orders_testing.db - This is a SQLite Database. It has tables of Orders, Order_Lines, Customers for testing purpose. If you delete values in this database, either make inserts or replace the file from Database folder.

### Setup
Clone the github repo with git clone <Repo_URL>
Create a new Conda environment
    conda create -n env_csr
    conda activate env_csr
    pip install -r requirements.txt

Create a .env file and provide a key called as OPENAI_API_KEY. Input the API Key of your account in the "" shown below. The value provided here is for reference and its a dummy value.

OPENAI_API_KEY="abcdfdasjfkdsajfkdsjafkldsja3232fjfkdjsakjf"

### Run
To execute the code:
    conda activate env_csr
    streamlit run Chat_With_Database.py
