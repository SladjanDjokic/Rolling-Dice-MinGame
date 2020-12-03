import json
from loguru import logger
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from starlette.routing import Route

# Global to hold notification data before its sent to client
MESSAGES = {}


async def consumer_call_event(request):
    """ API endpoint for consumer call notifications to be posted to MESSAGES"""
    data = await request.json()
    member_id = int(data.get('callee_id'))
    MESSAGES[member_id] = data
    logger.debug(MESSAGES)
    response = {"data": "call notification messages stored"}
    # TODO Can I make request and response await? Not working right now with uvicorn bug
    return JSONResponse(response, status_code=201)


async def calls_sse(request: Request):
    """ SSE Endpoint to subscribe to call notifications"""
    member_id = request.path_params['member_id']
    logger.debug(f"CONNECTED {member_id}")

    # TODO Throttle status checks so its not 10000 a second
    call_data_gen = status_event_generator(request, int(member_id))
    return EventSourceResponse(call_data_gen)


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
            if MESSAGES.get(member_id):
                data = MESSAGES.pop(int(member_id))
                if data:
                    payload = {"data": json.dumps(data), "event": "NOTIFY"}
                    yield payload
                    previous_status = 'call_delivered'
                    logger.debug('Current status :%s', 'call_delivered')
                else:
                    logger.debug('No change in status...')
    except Exception as exc:
        logger.debug(exc)

routes = [
    Route("/consumer/call-notifications", consumer_call_event, methods=["POST"]),
    Route('/subscribe/{member_id}', calls_sse, methods=["GET"])
]

app = Starlette(debug=True, routes=routes)
