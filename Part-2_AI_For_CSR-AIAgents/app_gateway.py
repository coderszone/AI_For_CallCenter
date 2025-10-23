from fastapi import FastAPI
from services.tickets.app import app as tickets_app
from services.orders.app import app as orders_app
from services.fulfillment.app import app as fulfillment_app

gateway = FastAPI(title="CSR Assist Gateway (Mounted Apps)", version="1.0.0")

gateway.mount("/tickets", tickets_app)
gateway.mount("/orders", orders_app)
gateway.mount("/fulfillment", fulfillment_app)
