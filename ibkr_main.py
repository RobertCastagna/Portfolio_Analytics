#https://interactivebrokers.github.io/tws-api/
# .\env\Scripts\activate

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from threading import Condition
import threading
import time


class IBapi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.positions = {}
        self.positions_received = Condition()

    def position(self, account, contract, pos, avgCost):
        super().position(account, contract, pos, avgCost)
        key = contract.symbol + contract.currency
        self.positions[key] = pos

    def positionEnd(self):
        super().positionEnd()
        with self.positions_received:
            self.positions_received.notify_all()

    def get_positions(self):
        with self.positions_received:
            self.positions_received.wait()
        return self.positions

def main():
    app = IBapi()
    app.connect('127.0.0.1', 7497, 123)

    # Request current positions
    app.reqPositions()

    # Start a separate thread for the event loop
    threading.Thread(target=app.run).start()

    # Wait for a short time to allow the position updates to be processed
    time.sleep(1)

    # Print the current positions
    print(app.get_positions())

if __name__ == "__main__":
    main()