import json
import typing
from fastapi import FastAPI
from fastapi import WebSocket
from loguru import logger
from starlette.endpoints import WebSocketEndpoint
from starlette.middleware.cors import CORSMiddleware


from pydantic import BaseModel


PROJECT_NAME = "amera-websocket-consumers"
KAFKA_INSTANCE = "localhost:29092"

# Global to hold notification data before its sent to client
MESSAGES = {}


app = FastAPI(title=PROJECT_NAME)
app.add_middleware(CORSMiddleware, allow_origins=["*"])

USERS = dict() # users connected to WS


# User model for reading request data
class CallNotification(BaseModel):
    type: str
    call_id: str
    call_url: str
    participants: list
    caller_id: str
    caller_name: str
    callee_id: str


@app.post("/consumer/notify")
async def consumer_call_ws(notification: CallNotification):
    """
    Kafka Consumer posts notification here to let WS users know they are getting a call.
    IF user is online, data will be sent over their ws connection.
    """
    user_id = int(notification.callee_id)
    logger.debug(type(USERS.get(1)))
    ws = USERS.get(user_id)
    logger.debug(USERS)
    if ws:
        logger.debug("### SENDING CALL NOTIFICATION TO USER")
        data = notification.dict()
        # TODO break out to make async?
        logger.debug(data)
        await ws.send_json(data)
        return {"data": "success"}
    return {"data": "user unavailable"}


@app.websocket_route("/consumer/calls")
class WebsocketConsumer(WebSocketEndpoint):
    """

    """
    async def on_connect(self, websocket: WebSocket) -> None:

        await websocket.accept()
        await websocket.send_json({"Message: ": "connected"})
        # Register user id and connection id

    async def on_disconnect(self, websocket: WebSocket, close_code: int) -> None:
        logger.info("disconnected")
        logger.info("consumer stopped")

    async def on_receive(self, websocket: WebSocket, data: typing.Any) -> None:
        """
        When connected. Save their connection data to a global dict so we know who is connected
        so we can route notification to the correct users
        """
        logger.info("RECEIVED")
        logger.info(json.loads(data))
        # TODO FE needs to send some unique info here
        data = json.loads(data)
        if data.get('user_id'):
            USERS[data.get('user_id')] = websocket
            logger.debug("Added user to websocket dict")
        await websocket.send_json({"Message: ": data})