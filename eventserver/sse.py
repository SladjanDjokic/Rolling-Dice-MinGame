import json
import time
from app.config import settings
from app import configure

from loguru import logger
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from starlette.routing import Route

from vyper import v


def init_app():
    v.add_config_path('../config')
    # Get the configuration values from runtime/env/parameters
    # Essentially puts them in the settings variable
    configure()
    logger.debug(settings.get('database'))
    return


# Global to hold notification data before its sent to client
CALL_NOTIFICATIONS = {}


async def consumer_call_event(request):
    """ API endpoint for consumer call notifications to be posted to MESSAGES"""
    data = await request.json()
    logger.debug(f"Received call data {data}")

    call_type = data.get('type')
    reply_type = data.get('reply_type')
    if call_type == "person":
        if reply_type is None:
            # Incoming call to single user. Route call to callee connected to sse
            logger.debug("INCOMING CALL")
            member_id = int(data.get('callee_id'))
            CALL_NOTIFICATIONS[member_id] = data
        elif reply_type == 'decline':
            logger.debug("DECLINE PERSON")
            # Decline notification. Route to caller_id
            member_id = int(data.get('caller_id'))
            CALL_NOTIFICATIONS[member_id] = data
    elif call_type == 'group':
        if reply_type == 'decline':
            logger.debug("DECLINE GROUP")
            # Decline group call notification. Route to caller_id
            member_id = int(data.get('caller_id'))
            CALL_NOTIFICATIONS[member_id] = data
        elif reply_type is None:
            logger.debug("SENDING GROUP CALL")
            member_id = data.get('callee_id')
            CALL_NOTIFICATIONS[int(member_id)] = data

    response = {"data": "call notification message stored"}
    return JSONResponse(response, status_code=201)


async def calls_sse(request: Request):
    """ SSE Endpoint to subscribe to call notifications"""
    member_id = request.path_params['member_id']
    logger.debug(f"CONNECTED {member_id}")

    # TODO Throttle status checks so its not 10000 a second
    call_data_gen = status_event_generator(request, int(member_id))
    return EventSourceResponse(call_data_gen)


async def check_health(request: Request):
    response = {'status': 'OK', 'health': 1.0}
    return JSONResponse(response, status_code=204)


async def status_event_generator(request, member_id):
    """
        Call Notification Generator. Only pushes event when a message is found. How to stop this from always looking
        is another story. Maybe after a few retries, just give up? Don't want it to keep looking up the message if it
        doesn't exist

    """
    # 1. One client subscribes. Waiting for NOTIFY event
    # 2. Status generator keeps searching for a NOTIFY event in MESSAGES based on their user_id.
    # 3. Consumer POSTS call data to /consumer/call_notification to save call data to MESSAGES
    # 4. Once status generator finds message, this event is yielded to SSE endpoint and pushed to client

    previous_status = dict()
    try:
        while True:
            if await request.is_disconnected():
                logger.debug('Request disconnected')
                break

            if previous_status and previous_status == 'call_delivered':
                logger.debug('Request completed. Disconnecting now')
                # yield {
                #     "event": "end",
                #     "data": ''
                # }
                break
            data = None
            if CALL_NOTIFICATIONS.get(member_id):
                data = CALL_NOTIFICATIONS.pop(int(member_id))

            if data:
                payload = {"data": json.dumps(data), "event": "NOTIFY"}
                yield payload
                previous_status = 'call_delivered'

            time.sleep(1)
    except Exception as exc:
        logger.debug(exc)

routes = [
    Route("/consumer/call-notifications", consumer_call_event, methods=["POST"]),
    Route('/healthz', check_health, methods=["GET"]),
    Route('/subscribe/{member_id}', calls_sse, methods=["GET"])
]

init_app()
app = Starlette(debug=True, routes=routes)
