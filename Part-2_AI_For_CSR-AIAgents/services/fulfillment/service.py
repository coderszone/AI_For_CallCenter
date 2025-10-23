import sqlite3
from typing import Dict, Optional

DB_PATH = "./services/fulfillment/Storage/fulfillment.db"

class FulfillmentService:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _connect(self):
        return sqlite3.connect(self.db_path)

    # Get the fulfillment status by using order_id
    def get_fulfillment_status(self, order_id: str) -> Optional[Dict]:
        query = """
            SELECT distinct Fulfillment_Order_Status
            FROM fulfillment where order_id = ?
            LIMIT 1
            """
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query, (order_id,))
            row = cur.fetchone()
        if not row:
            return None
        return {
            "Fulfillment_Order_Status": row[0],
        }
    
    # Update the status of the fulfillment order by using order_id
    def update_fulfillment_status(self, order_id: str, status: str) -> bool:
        query = """
            UPDATE fulfillment
            SET Fulfillment_Order_Status = ?
            WHERE order_id = ?
            """
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query, (status, order_id))
            conn.commit()
            return cur.rowcount > 0
        
    # Get the fulfillment details by using order_id
    def get_fulfillment_details(self, order_id: str) -> Optional[Dict]:
        query = """
            SELECT order_id, Item_Name	Quantity	Fulfillment_Order_Status	Tracking_Nbr	Ship_Date
            FROM fulfillment where order_id = ?
            """
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query, (order_id,))
            rows = cur.fetchall()
        if not rows:
            return None
        return [
            {
                "order_id": r[0],
                "Item_Name": r[1],
                "Quantity": r[2],
                "Fulfillment_Order_Status": r[3],
                "Tracking_Nbr": r[4],
                "Ship_Date": r[5],
            }
            for r in rows
        ]