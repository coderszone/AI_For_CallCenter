import sqlite3
from typing import Dict, List, Optional

DB_PATH = "./services/orders/Storage/orders.db"


class OrderService:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _connect(self):
        return sqlite3.connect(self.db_path)

    @staticmethod
    def _row_to_dict(r) -> Dict:
        return {
            "unique_id": r[0],
            "Order_ID": r[1],
            "Cust_Email": r[2],
            "Fulfillment_Order_ID": r[3],
            "Created_Timestamp": r[4],
            "Item_ID": r[5],
            "Item_Name": r[6],
            "Quantity": r[7],
            "Order_Status": r[8],
            "Tracking_Nbr": r[9],
            "Ship_Date": r[10],
            "Item_Price": r[11],
            "Shipping_price": r[12],
            "Discount_Applied": r[13],
            "Total_Price": r[14],
            "Appeasement_Applied": r[15],
            "Returned_qty": r[16],
            "Refund_Amount": r[17],
        }

    def _fetch_lines(self, cur, order_id: str) -> List[Dict]:
        cur.execute(
            """
            SELECT
              unique_id, Order_ID, Cust_Email, Fulfillment_Order_ID, Created_Timestamp,
              Item_ID, Item_Name, Quantity, Order_Status, Tracking_Nbr, Ship_Date,
              Item_Price, Shipping_price, Discount_Applied, Total_Price,
              Appeasement_Applied, Returned_qty, Refund_Amount
            FROM orders
            WHERE Order_ID = ?
            ORDER BY unique_id
            """,
            (order_id,),
        )
        return [self._row_to_dict(r) for r in cur.fetchall()]

    def order_exists(self, order_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM orders WHERE Order_ID = ? LIMIT 1", (order_id,))
            return cur.fetchone() is not None

    def get_order_status(self, order_id: str) -> Optional[str]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT Order_Status FROM orders WHERE Order_ID = ? LIMIT 1", (order_id,))
            statuses = [r[0] for r in cur.fetchall()]
        if not statuses:
            return None
        has_shipped = any(s == "Shipped" for s in statuses)
        has_stf = any(s == "Sent To Fulfillment" for s in statuses)
        all_cancel = all(s == "Cancelled" for s in statuses)
        all_created = all(s == "Created" for s in statuses)
        if has_shipped:
            return "Shipped"
        if has_stf:
            return "Sent To Fulfillment"
        if all_cancel:
            return "Cancelled"
        if all_created:
            return "Created"
        return statuses[0]

    def get_order_lines(self, order_id: str) -> List[Dict]:
        with self._connect() as conn:
            cur = conn.cursor()
            return self._fetch_lines(cur, order_id)

    def cancel_order(self, order_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.cursor()
            lines = self._fetch_lines(cur, order_id)
            if not lines:
                return False
            if any(l["Order_Status"] in ("Shipped", "Cancelled") for l in lines):
                raise ValueError("Order has Shipped/Cancelled lines and cannot be cancelled.")
            cur.execute("UPDATE orders SET Order_Status = 'Cancelled' WHERE Order_ID = ?", (order_id,))
            conn.commit()
            return cur.rowcount > 0

    def cancel_order_line(self, order_id: str, line_item_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT Order_Status FROM orders WHERE Order_ID = ? AND item_id = ?",
                (order_id, line_item_id),
            )
            row = cur.fetchone()
            if not row:
                return False
            status = row[0]
            if status in ("Shipped", "Cancelled"):
                raise ValueError("Line is not in a cancellable state.")
            cur.execute(
                "UPDATE orders SET Order_Status = 'Cancelled' WHERE Order_ID = ? AND item_id = ?",
                (order_id, line_item_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def create_return(self, order_id: str, line_item_id: str, return_qty: int = 1) -> List[Dict]:
        print("Processing return for order_id:", order_id, "line_item_id:", line_item_id, "return_qty:", return_qty )
        if return_qty < 1:
            print("Invalid return quantity:", return_qty)
            raise ValueError("return_qty must be >= 1")
        with self._connect() as conn:
            cur = conn.cursor()
            print("Fetching order lines for return processing...")
            if line_item_id is not None:
                print("Fetching specific line item for return processing...")
                cur.execute(
                    "SELECT unique_id, item_id, Quantity, Returned_qty, Item_Price, Appeasement_Applied, Order_Status FROM orders WHERE Order_ID = ? AND item_id = ?",
                    (order_id, line_item_id,),
                )
                rows = cur.fetchall()
            else:
                print("Fetching all line items for return processing...")
                cur.execute(
                    "SELECT unique_id, item_id, Quantity, Returned_qty, Item_Price, Appeasement_Applied, Order_Status FROM orders WHERE Order_ID = ? ORDER BY unique_id",
                    (order_id,),
                )
                rows = cur.fetchall()
            if not rows:
                print("No order lines found for order_id:", order_id)
                return []
            requested_rtn_qty = return_qty
            any_updated = False
            print("Processing rows for return...")
            for unique_id, item_id, qty, ret_qty, price, appease, status in rows:
                print("Evaluating unique_id:", unique_id, "item_id:", item_id, "qty:", qty, "ret_qty:", ret_qty, "status:", status)
                remaining = qty - ret_qty
                # Check if there are any remaining units to return or status is not Shipped
                if remaining <= 0 or status != "Shipped":
                    print("Skipping unique_id:", unique_id, "remaining:", remaining, "status:", status)
                    continue
                if requested_rtn_qty > remaining:
                    print("Requesting more units to be returned than available. Adjusting the quantity.")
                    requested_rtn_qty = remaining
                units = min(remaining, requested_rtn_qty)
                appease_per_unit = (appease / qty) if qty > 0 else 0
                refund_increment = int((price * units) - (appease_per_unit * units))
                print("Updating unique_id:", unique_id, "units to return:", units, "refund_increment:", refund_increment)
                cur.execute(
                    "UPDATE orders SET Returned_qty = Returned_qty + ?, Refund_Amount = Refund_Amount + ? WHERE unique_id = ?",
                    (units, refund_increment, unique_id),
                )
                remaining -= units
                any_updated = True
            if not any_updated:
                print("No returnable quantity found for order_id:", order_id)
                raise ValueError("No returnable quantity found on this order/line.")
            conn.commit()
            print("Committing changes for return processing...")
            return self._fetch_lines(cur, order_id)

    
    # Create a function to return current datetime
    def current_datetime(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()