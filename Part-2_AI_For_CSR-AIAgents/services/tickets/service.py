import sqlite3
from typing import List, Dict, Optional

DB_PATH = "./services/tickets/Storage/support_tickets.db"

class TicketService:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def get_customer_tickets(self, customer_email=None, order_id=None):
        if not customer_email and not order_id:
            raise ValueError("Please pass either a customer_email or order_id.")

        query = """
            SELECT Ticket_ID, Cust_Email, Order_ID, Call_Timestamp, CSR_Name, Ticket_Notes
            FROM tickets WHERE 1=1
        """
        params = []
        if customer_email:
            query += " AND Cust_Email = ?"
            params.append(customer_email)
        if order_id:
            query += " AND Order_ID = ?"
            params.append(order_id)
        query += " ORDER BY Ticket_ID"

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()

        return [
            {
                "Ticket_ID": r[0],
                "Cust_Email": r[1],
                "Order_ID": r[2],
                "Call_Timestamp": r[3],
                "CSR_Name": r[4],
                "Ticket_Notes": r[5],
            }
            for r in rows
        ]

    def get_ticket_details(self, ticket_id: int) -> Optional[Dict]:
        query = """
            SELECT Ticket_ID, Cust_Email, Order_ID, Call_Timestamp, CSR_Name, Ticket_Notes
            FROM tickets WHERE Ticket_ID = ?
        """
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query, (ticket_id,))
            row = cur.fetchone()
        if not row:
            return None
        return {
            "Ticket_ID": row[0],
            "Cust_Email": row[1],
            "Order_ID": row[2],
            "Call_Timestamp": row[3],
            "CSR_Name": row[4],
            "Ticket_Notes": row[5],
        }

    def add_ticket(
        self,
        customer_email: str,
        order_id: Optional[str],
        issue_description: str,
        csr_name: str = "N/A",
        call_timestamp_iso: Optional[str] = None,
    ) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            if call_timestamp_iso:
                cur.execute(
                    """
                    INSERT INTO tickets (Cust_Email, Order_ID, Call_Timestamp, CSR_Name, Ticket_Notes)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (customer_email, order_id or "", call_timestamp_iso, csr_name, issue_description),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO tickets (Cust_Email, Order_ID, Call_Timestamp, CSR_Name, Ticket_Notes)
                    VALUES (?, ?, strftime('%Y-%m-%d %H:%M:%S','now'), ?, ?)
                    """,
                    (customer_email, order_id or "", csr_name, issue_description),
                )
            conn.commit()
            return int(cur.lastrowid)

    def update_ticket(self, ticket_id: int, update_description: str) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT Ticket_Notes FROM tickets WHERE Ticket_ID = ?", (ticket_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("Ticket not found")
            updated_notes = (row[0] or "") + ("\n" if row[0] else "") + update_description
            cur.execute(
                "UPDATE tickets SET Ticket_Notes = ? WHERE Ticket_ID = ?",
                (updated_notes, ticket_id),
            )
            conn.commit()
