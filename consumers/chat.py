import asyncio

from aiokafka import AIOKafkaConsumer

from consumers.main import decode_message

import logging
from app import settings

logger = logging.getLogger(__name__)

loop = asyncio.get_event_loop()


async def consume_chat():

    # Prints all settings from Vyper as read from all static files
    # print(f"ALL SETTINGS: {pformat(settings.all_settings(True), indent=2, width=260)}")

    # Prints all environ variables from the runtime
    # print(f"ALL ENV: {pformat(os.environ.__dict__, indent=2, width=260)}")

    # Get the most recent value, environment variable trumps most
    topic = settings.get('kafka.chat_topic')
    server = settings.get('kafka.server')

    # Prints the `topic` from kafka.sms_topic in Vyper
    # Definition of this key is defined by TOML or by a pre-configured key
    print(f"CONSUMING {topic} TOPIC")
    consumer = AIOKafkaConsumer(
        topic,
        loop=loop, bootstrap_servers=server,
    )

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
            msg = str(decode_message(msg))

    finally:
        # Will leave consumer group; perform autocommit if enabled.
        await consumer.stop()


loop.run_until_complete(consume_chat())
