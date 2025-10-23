from pydantic import BaseModel
from typing import Optional

class FulfillmentDetail(BaseModel):
    order_id: str
    Item_Name: str
    Quantity: int
    Fulfillment_Order_Status: str
    Tracking_Nbr: Optional[str]
    Ship_Date: Optional[str]

class FulfillmentStatus(BaseModel):
    Fulfillment_Order_Status: str