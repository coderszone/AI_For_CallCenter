from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class TicketOut(BaseModel):
    Ticket_ID: int
    Cust_Email: EmailStr
    Order_ID: str
    Call_Timestamp: str
    CSR_Name: str
    Ticket_Notes: str

class TicketCreate(BaseModel):
    customer_email: EmailStr = Field(..., description="Customer email")
    order_id: Optional[str] = Field(None, description="Order ID (optional)")
    issue_description: str = Field(..., description="Ticket details or issue notes")
    csr_name: str = Field("N/A", description="CSR handling the ticket")
    call_timestamp_iso: Optional[str] = Field(
        None, description="ISO 'YYYY-MM-DD HH:MM:SS'"
    )

class TicketUpdate(BaseModel):
    update_description: str
