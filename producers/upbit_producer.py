import os
import sys
import logging
import websockets
import json
import redis
import time
import asyncio
from connection import connect_to_redis

class upbit_producer:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.q = self.ticker + '_q'
        self.uri = "wss://api.upbit.com/websocket/v1"
        self.subscribe_fmt = [
            {"ticket": "UNIQUE_TICKET"},
            {
                "type": "orderbook",
                "codes": ["KRW-" + self.ticker.upper() + ".5"],
                "isOnlyRealtime": True
            },
            {"format": "SIMPLE"}
        ]

        log_directory = "/CryptoStream/logs/producer"  
        log_filename = 'upbit_producer.log'  
        log_file_path = os.path.join(log_directory, log_filename)

        if not os.path.exists(log_directory):
            os.makedirs(log_directory)

        logging.basicConfig(
            level=logging.INFO,  
            format='%(asctime)s - %(levelname)s - %(message)s',  
            filename=log_file_path, 
            filemode='a' # a: append
        )

    async def up_ws_client(self):        
        redis_conn = connect_to_redis()

        websocket = await websockets.connect(self.uri, ping_interval=60)
        await websocket.send(json.dumps(self.subscribe_fmt))

        while True:
            if websocket.open:
                try:
                    data = await websocket.recv()
                    data = json.loads(data)

                    redis_conn.lpush(self.q, json.dumps(data))

                except (redis.ConnectionError, redis.TimeoutError) as e:
                    logging.error(f"Redis Connection failed: {e}")
                    redis_conn = connect_to_redis()

                except Exception as e:
                    logging.error(f"upbit producer error: {e}")

            else:
                try:
                    logging.error(f"upbit websocket is NOT connected. Reconnecting...")

                    websocket = await websockets.connect(self.uri, ping_interval=60)
                    await websocket.send(json.dumps(self.subscribe_fmt))

                    logging.error(f"upbit websocket is connected.")
                
                except Exception as e:
                    logging.error(f"upbit websocket Unable to reconnect: {e}")
                    time.sleep(5)

    async def up_connecter(self):
        await self.up_ws_client()

    def up_producer(self):
        asyncio.run(self.up_connecter())
    
    def run(self):
        self.up_producer()

if __name__ == '__main__':
    upbit_producer('BTC').run()