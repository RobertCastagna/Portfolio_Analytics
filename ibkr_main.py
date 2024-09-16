#https://interactivebrokers.github.io/tws-api/
# .\env\Scripts\activate

import asyncio
from ibapi.client import EClient
from ibapi.wrapper import EWrapper

class AsyncIBWrapper(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.requests = {}

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        print(f"Connected. Next valid order ID: {orderId}")
        self.start_requests()

    def start_requests(self):
        pass  # Override this method to start your requests

    def error(self, reqId, errorCode, errorString):
        print(f"Error {errorCode}: {errorString}")

    def create_future(self, reqId):
        future = asyncio.Future()
        self.requests[reqId] = future
        return future

    def complete_future(self, reqId):
        if reqId in self.requests:
            self.requests[reqId].set_result(True)