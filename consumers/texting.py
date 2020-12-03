import os
from pprint import pformat
import asyncio

from aiokafka import AIOKafkaConsumer

from app.util.textmessage import send_sms

from consumers.main import decode_message
from app import settings


loop = asyncio.get_event_loop()


# TODO can I make this a class? Probably


async def consume_sms():

    # Prints all settings from Vyper as read from all static files
    # print(f"ALL SETTINGS: {pformat(settings.all_settings(True), indent=2, width=260)}")

    # Prints all environ variables from the runtime
    # print(f"ALL ENV: {pformat(os.environ.__dict__, indent=2, width=260)}")
    
    # Get the most recent value, environment variable trumps most
    topic = settings.get('kafka.sms_topic')
    server = settings.get('kafka.server')

    # Prints the `topic` from kafka.sms_topic in Vyper
    # Definition of this key is defined by TOML or by a pre-configured key 
    print(f"CONSUMING {topic} TOPIC")
    consumer = AIOKafkaConsumer(
        topic,
        loop=loop, bootstrap_servers=server,
        )
    # Get cluster layout and join group `my-group`
    await consumer.start()
    try:
        # Consume messages
        async for msg in consumer:
            print("consumed: ", msg.topic, msg.partition, msg.offset,
                  msg.key, msg.value, msg.timestamp)
            number = str(decode_message(msg))
            # TODO How to handle various messages. We need meta data to know what message is needed
            message = settings.get('services.twilio.text_verification_message')
            response = send_sms(number, message)
            # TODO Handle response? Retries?
    finally:
        # Will leave consumer group; perform autocommit if enabled.
        await consumer.stop()
