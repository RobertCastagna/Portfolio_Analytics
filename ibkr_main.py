#https://interactivebrokers.github.io/tws-api/
# .\env\Scripts\activate
import ibapi
from queue import Queue
from ibapi.client import EClient
from ibapi.common import BarData, TickerId
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract, ContractDetails
import threading
import time


class IBApi(EWrapper, EClient):
    def __init__(self, data_queue):
        EClient.__init__(self, self)
        self.data_queue = data_queue

    def headTimestamp(self, reqId: int, headTimestamp: str):
        print('Timestamp: ', headTimestamp)
        return headTimestamp

    def cancelHeadTimeStamp(self, reqId: int):
        return super().cancelHeadTimeStamp(reqId)

    def contractDetails(self, reqId: TickerId, contractDetails: ContractDetails):
        return super().contractDetails(reqId, contractDetails)
    
    def contractDetailsEnd(self, reqId: TickerId):
        return super().contractDetailsEnd(reqId)

    def historicalData(self, reqId: TickerId, bar: BarData):
        self.data_queue.put(bar)
        return super().historicalData(reqId, bar)
    
    def historicalDataEnd(self, reqId: TickerId, start: str, end: str):
        print("Historical data received for id: ", reqId)
        self.data_queue.put(None)
        return super().historicalDataEnd(reqId, start, end)
    
def run_loop(api_client):
    api_client.run()

def start_client(data_queue):
    api_client = IBApi(data_queue)
    api_client.connect('127.0.0.1', 7497, clientId=1)
    api_thread = threading.Thread(target=run_loop, args=(api_client,), daemon=True)
    api_thread.start()
    time.sleep(1)
    return api_client, api_thread

def close_client(api_client, data_queue, processing_thread, api_thread):
    data_queue.put(None)
    processing_thread.join()

    api_client.disconnect()
    api_thread.join()
    print("Safely Exited Connection.")

def data_processing_thread(data_queue):
    while True:
        data = data_queue.get()
        if data is None:
            break

        process_data(data)
        data_queue.task_done()

def process_data(data):
    # do whatever
    time.sleep(2)
    print("Data Processed.")
    
def create_contract(ticker):
    contract = Contract()
    contract.symbol = ticker
    contract.secType = 'STK'
    contract.exchange = 'SMART'
    contract.currency = 'USD'
    return contract

if __name__ == '__main__':
    try:
        # main program logic
        data_queue = Queue() 
        api_client, api_thread = start_client(data_queue)

        processing_thread = threading.Thread(target=data_processing_thread, args=(data_queue,))
        processing_thread.start()

        appl_contract = create_contract('AAPL')
        api_client.reqHeadTimeStamp(1, appl_contract, "TRADES", 1, 1)
        api_client.reqHistoricalData(1, appl_contract, '', '1 M', '1 day', 'MIDPOINT', 0, 1, False, [])
        
        while True:
            pass

    except KeyboardInterrupt:
        close_client(api_client, data_queue, processing_thread, api_thread)