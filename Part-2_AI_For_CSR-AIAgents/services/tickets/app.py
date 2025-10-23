from fastapi import FastAPI, Depends, HTTPException, Query, Path
from fastapi_mcp import FastApiMCP
from typing import Optional, List
from .schemas import TicketOut, TicketCreate, TicketUpdate
from .service import TicketService
from datetime import datetime, timezone

app = FastAPI(title="Tickets Service", version="1.0.0")

def get_service() -> TicketService:
    return TicketService()

@app.get("/healthz", include_in_schema=False)
def health():
    return {"status": "ok"}

@app.get(
    "/fetchticket/",
    response_model=List[TicketOut],
    operation_id="get_customer_tickets",  # ← tool name
    summary="List tickets for a customer/order",
    description=(
        "Return tickets filtered by customer_email and/or order_id. "
        "At least one filter should be provided for efficient queries."
    ),
)
def list_tickets(
    customer_email: Optional[str] = Query(None, description="Customer email to filter by."),
    order_id: Optional[str] = Query(None, description="Order ID to filter by."),
    svc: TicketService = Depends(get_service),
):
    try:
        return svc.get_customer_tickets(customer_email, order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get(
    "/getticket/{ticket_id}",
    response_model=TicketOut,
    operation_id="get_ticket_details",  # ← tool name
    summary="Get a ticket by ID",
    description="Return the detailed ticket record for the given Ticket_ID.",
)
def get_ticket(
    ticket_id: int = Path(..., ge=1, description="Numeric Ticket_ID."),
    svc: TicketService = Depends(get_service),
):
    t = svc.get_ticket_details(ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return t

@app.post(
    "/addticket/",
    response_model=int,
    status_code=201,
    operation_id="add_ticket",  # ← tool name
    summary="Create a new ticket",
    description="Create a new ticket for a customer with optional order_id and CSR name. Returns the new Ticket_ID.",
)
def create_ticket(payload: TicketCreate, svc: TicketService = Depends(get_service)):
    call_timestamp = payload.call_timestamp_iso or datetime.now(timezone.utc).isoformat()
    return svc.add_ticket(
        customer_email=payload.customer_email,
        order_id=payload.order_id,
        issue_description=payload.issue_description,
        csr_name=payload.csr_name,
        call_timestamp_iso=call_timestamp,
    )

@app.post(
    "/update/{ticket_id}",
    status_code=204,
    operation_id="update_ticket",  # ← tool name
    summary="Append an update to a ticket",
    description="Append text to Ticket_Notes for the given Ticket_ID.",
)
def update_ticket(
    ticket_id: int = Path(..., ge=1, description="Numeric Ticket_ID."),
    payload: TicketUpdate = ...,
    svc: TicketService = Depends(get_service),
):
    try:
        svc.update_ticket(ticket_id, payload.update_description)
    except ValueError:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return

# Mount MCP from your FastAPI app’s OpenAPI
# mcp = FastApiMCP(app, path="/mcp")
# mcp.mount()

mcp = FastApiMCP(app)
mcp.mount()              # mounts at default "/mcp"
