from typing import List
from fastapi import FastAPI, Depends, HTTPException, Query, Path
from fastapi_mcp import FastApiMCP  # NEW
from .schemas import (
    OrderOut,
    OrderStatusOut,
    ReturnCreate,
)
from .service import OrderService

app = FastAPI(title="Orders Service", version="1.0.0")


def get_service() -> OrderService:
    return OrderService()


@app.get("/healthz", include_in_schema=False)
def health():
    return {"status": "ok"}


@app.get(
    "/orders/{order_id}/exists",
    response_model=bool,
    operation_id="get_check_order",
    summary="Check if an order exists",
    description="Return true if the order exists; otherwise false.",
)
def get_check_order(
    order_id: str = Path(..., description="Order ID (e.g., 'ORD-010')."),
    svc: OrderService = Depends(get_service),
):
    return svc.order_exists(order_id)


@app.get(
    "/orders/{order_id}/status",
    response_model=OrderStatusOut,
    operation_id="get_order_status",
    summary="Get current order status",
    description=(
        "Return the synthesized status for an order_id. "
        "Priority: Shipped > Sent To Fulfillment > Cancelled > Created."
    ),
)
def get_order_status(
    order_id: str = Path(..., description="Order ID (e.g., 'ORD-010')."),
    svc: OrderService = Depends(get_service),
):
    status = svc.get_order_status(order_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"order_id": order_id, "status": status}


@app.get(
    "/orders/{order_id}",
    response_model=List[OrderOut],
    operation_id="get_order_details",
    summary="Get full order details",
    description="Return all order lines (full detail) for the given order_id.",
)
def get_order_details(
    order_id: str = Path(..., description="Order ID (e.g., 'ORD-010')."),
    svc: OrderService = Depends(get_service),
):
    lines = svc.get_order_lines(order_id)
    if not lines:
        raise HTTPException(status_code=404, detail="Order not found")
    return lines


@app.post(
    "/orders/{order_id}/cancel",
    status_code=204,
    operation_id="cancel_order",
    summary="Cancel an order",
    description=(
        "Cancel the order if **all** lines are cancellable (not Shipped/Cancelled). "
        "Returns 204 on success, 400 if not cancellable, or 404 if not found."
    ),
)
def cancel_order(
    order_id: str = Path(..., description="Order ID (e.g., 'ORD-006')."),
    svc: OrderService = Depends(get_service),
):
    try:
        ok = svc.cancel_order(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Order not found or not cancellable")
    return


@app.post(
    "/orders/{order_id}/lines/{line_item_id}/cancel",
    status_code=204,
    operation_id="cancel_order_line",
    summary="Cancel a specific order line",
    description=(
        "Cancel a single line by **item_id** if it is cancellable (not Shipped/Cancelled). "
        "Returns 204 on success, 400 if not cancellable, or 404 if not found."
    ),
)
def cancel_order_line(
    order_id: str = Path(..., description="Order ID (e.g., 'ORD-010')."),
    line_item_id: str = Path(..., description="Line item identifier (item_id)."),
    svc: OrderService = Depends(get_service),
):
    try:
        ok = svc.cancel_order_line(order_id, line_item_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Order line not found or not cancellable")
    return


@app.post(
    "/orders/{order_id}/returns",
    response_model=List[OrderOut],
    operation_id="return_order_create",
    summary="Create a return for an order",
    description=(
        "Initiate a return on shipped lines. If line_item_id is omitted, the service will "
        "evaluate eligible lines. Updates Returned_qty and Refund_Amount."
    ),
)
def return_order_create(
    order_id: str = Path(..., description="Order ID (e.g., 'ORD-010')."),
    payload: ReturnCreate = ...,
    svc: OrderService = Depends(get_service),
):
    try:
        updated_lines = svc.create_return(
            order_id=order_id,
            line_item_id=payload.line_item_id,
            return_qty=payload.return_qty or 1,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated_lines:
        raise HTTPException(status_code=404, detail="Order/line not found or not returnable")
    return updated_lines


# Add the current_datetime function as a tool
@app.get(
    "/current_datetime",
    response_model=str,
    operation_id="get_current_datetime",
    summary="Get the current date and time",
    description="Return the current date and time in ISO 8601 format.",
)
def get_current_datetime(svc: OrderService = Depends(get_service)):
    return svc.current_datetime()


# Mount MCP so your routes become tools (names from operation_id, help from summaries/descriptions)
mcp = FastApiMCP(app)  # NEW
mcp.mount()            # Exposes `/mcp` endpoint automatically  # NEW

