from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class OrderOut(BaseModel):
    unique_id: int
    Order_ID: str
    Cust_Email: EmailStr
    Fulfillment_Order_ID: Optional[str] = None
    Created_Timestamp: str
    Item_ID: str
    Item_Name: str
    Quantity: int
    Order_Status: str
    Tracking_Nbr: Optional[str] = None
    Ship_Date: Optional[str] = None
    Item_Price: int
    Shipping_price: int
    Discount_Applied: int
    Total_Price: int
    Appeasement_Applied: int
    Returned_qty: int
    Refund_Amount: int


class OrderStatusOut(BaseModel):
    order_id: str
    status: str


class ReturnCreate(BaseModel):
    line_item_id: str = Field(None, description="item_id of a specific line to return")
    return_qty: int = Field(1, ge=1, description="Units to return (default 1)")
