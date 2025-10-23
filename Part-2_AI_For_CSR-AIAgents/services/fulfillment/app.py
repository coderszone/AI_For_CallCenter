from fastapi_mcp import FastApiMCP
from fastapi import FastAPI, Depends, HTTPException, Query, Path
from typing import Optional
from .schemas import FulfillmentDetail, FulfillmentStatus
from .service import FulfillmentService

app = FastAPI(title="Fulfillment Service", version="1.0.0")


def get_service() -> FulfillmentService:
    return FulfillmentService()


@app.get("/healthz", include_in_schema=False)
def health():
    return {"status": "ok"}


# --- Primary, correctly spelled endpoint (exposed to OpenAPI/MCP) ---
@app.get(
    "/FulfillmentStatus/{order_id}",
    response_model=FulfillmentStatus,
    operation_id="get_fulfillment_status",
    summary="Get fulfillment status for an order",
    description=(
        "Return the synthesized fulfillment status for the given order_id. "
        "Raises 404 if the order has no fulfillment rows."
    ),
)
def get_fulfillment_status(
    order_id: str = Path(..., description="Order ID (e.g., 'ORD-010')."),
    svc: FulfillmentService = Depends(get_service),
):
    status = svc.get_fulfillment_status(order_id)
    if not status:
        raise HTTPException(status_code=404, detail="Fulfillment status not found")
    return status


# --- Backward-compat shim for the misspelled path (hidden from OpenAPI/MCP) ---
@app.get(
    "/FulffilmentStatus/{order_id}",
    response_model=FulfillmentStatus,
    include_in_schema=False,  # hide from MCP tool list
)
def get_fulfillment_status_compat(
    order_id: str,
    svc: FulfillmentService = Depends(get_service),
):
    status = svc.get_fulfillment_status(order_id)
    if not status:
        raise HTTPException(status_code=404, detail="Fulfillment status not found")
    return status


@app.put(
    "/FulfillmentStatus/{order_id}",
    response_model=bool,
    operation_id="update_fulfillment_status",
    summary="Update fulfillment status for an order",
    description=(
        "Update the fulfillment status for the given order_id. "
        "Returns true if an update occurred, otherwise 404."
    ),
)
def update_fulfillment_status(
    order_id: str = Path(..., description="Order ID (e.g., 'ORD-010')."),
    status: str = Query(
        ...,
        description="New status value (e.g., 'Created', 'In-Progress', 'Shipped', 'Cancelled').",
    ),
    svc: FulfillmentService = Depends(get_service),
):
    ok = svc.update_fulfillment_status(order_id, status)
    if not ok:
        raise HTTPException(status_code=404, detail="Fulfillment status not found")
    return ok


# Mount MCP (derives tools from OpenAPI: operation_id, summaries, param schemas)
mcp = FastApiMCP(app)
mcp.mount()  # serves at /mcp

