# Part-2 AI FOR CSR - USING AGENTS

In this section, we will look into how can we use Agents to assist CSR in performing their activity.

## Overview
Following are the components that we will configure to showcase the capability:
1. Ticket Service - This is the service which holds information about the calls which customer has done. It will have the following API's.
    get_customer_tickets(customer_email or order_id) - This will return the list of tickets and summary of the details of the tickets.
    get_ticket_details(ticket_id) - This will return the detailed information about the ticket.
    add_ticket(customer_email, order_id(optional), issue_description) - This will create a new ticket for the customer.
    update_ticket(ticket_id, update_description) - This will update the ticket with the new information
2. RAG service - This is the service which will be used to get the relevant information from the knowledge base. It will have the following documents that are passed tot he RAG service.
    a. FAQ - This will have the frequently asked questions and their answers.
    b. Company Policies - This will have the company policies that are relevant to the customer service.
3. Order Service - This is the critical service which will have the information about the orders that are placed by the customers. It will have the following API's.
    get_check_order(order_id) - This will return a bollean to indicate if the order exists or not.
    get_order_status(order_id) - This will return the current status of the order ie. Order_Status field
    get_order_details(order_id) - This will return the details of the order. This will include the Order_ID	Cust_Email	Fulfillment_Order_ID	Created_Timestamp	Item_ID	Item_Name	Quantity	Order_Status	Tracking_Nbr	Ship_Date	Item_Price	Shipping_price	Discount_Applied	Total_Price	Appeasement_Applied	Returned_qty	Refund_Amount
    cancel_order(order_id) - This will cancel the order if it is in a cancellable state. Check to ensure order is not in Shipped or Cancelled Order_Status
    cancel_order_line(order_id, line_item_id) - This will cancel the specific line item in the order if it is in a cancellable state. i.e. order_status should not be in Shipped or Cancelled for the line
    return_order_create(order_id) - This will initiate the return process for the order if it is in a returnable state. Check to ensure the Order_Status is in Shipped status. Also, Returned_qty should be less than Quantity. If the conditions match, update the Returned_qty and Refund_Amount fields (Refund_Amount = Refund_Amount + (Item_Price * Returned_qty) - (Appeasement_Applied/Quantity))
    get_current_date_time() - This will return the current date and time. This will be used to check the return window for the order as LLMs do not have the current date and time information.
4. Fulfillment Service - This service will handle the fulfillment of orders, including shipping and delivery. It will have the following API's.
    get_fulfillment_status(fulfillment_source_order_id) - This will return the current fulfillment status of the order.
    update_fulfillment_status(fulfillment_source_order_id, new_status) - This will update the fulfillment status of the order to the new status provided.

## Setup
The services listed above will be exposed to the agent as a Tool via MCP. The RAG service will be exposed as a separate tool.
There will be a streamlit UI which will be used by the CSR to interact with the agent.
We will use n8n for workflow automation and orchestration. The n8n agent will be used to call the tools and get the information from the services. The workflow of n8n will be triggered when a message is received from the streamlit UI. Session_ID is the unique identifier for the conversation between the CSR and the agent. It will be used to maintain the context of the conversation. The session_ID will be generated when the CSR starts a new conversation and will be passed in every message to the agent. The agent will use this session_ID to fetch the previous messages in the conversation and maintain the context.
The services will be created using FastAPI and will be running locally. The RAG service will use a vector database to store the documents and we will use n8n to create the RAG service. We will use OpenAI embeddings to create the vector database and use it to fetch the relevant documents based on the query.

### Clone the repository
git clone <repository_url>

### Navigate to the cloned repository
create a .env file in the root folder of the cloned repository and add the following environment variables
OPENAI_API_KEY=<your_openai_api_key>

### Create Conda Environment
conda create -n <environment_name>>
conda activate <environment_name>
### Install dependencies
pip install -r requirements.txt
#### Install UVicorn
pip install uvicorn[standard]

### Go intto the parent folder of the cloned repository and execute the following commands to run the services
uvicorn services.tickets.app:app --port 8001 --reload
uvicorn services.fulfillment.app:app --port 8002 --reload
uvicorn services.orders.app:app --port 8003 --reload

### Validate if the services are running
Open the following URLs in the browser to check if the services are running
http://localhost:8001/docs
http://localhost:8002/docs
http://localhost:8003/docs

### Validate if the MCP is running
Open the following URL in the browser to check if the MCP is running
http://localhost:8001/mcp
http://localhost:8002/mcp
http://localhost:8003/mcp
### Validate if the OpenAPI specs are accessible. These are the tool definitions that will be used by the agent.
http://127.0.0.1:8001/openapi.json
http://127.0.0.1:8002/openapi.json
http://127.0.0.1:8003/openapi.json

### Install and Run n8n
npm install n8n -g
#### Export the OPEN_API_KEY environment variable
export OPENAI_API_KEY=<your_openai_api_key>
n8n start
Create an account and login to n8n. Import the workflow from the workflows folder in the repository.
Click on the Execute Workflow button for RAG and upload the documents present in the Documents folder in the repository. This will create the vector database for RAG.
Click on the Tools to ensure that they are able to connect to the services running locally. The will display the endpoints and the methods available in the services.

### Run the Streamlit UI
streamlit run streamlit_app.py
Open the following URL in the browser to access the UI
http://localhost:8501
Change the URL in the UI to point to your webhool URL of n8n instance. This URL can be fuond in the webhook node of the n8n workflow.
Start interacting with the agent via the UI.
