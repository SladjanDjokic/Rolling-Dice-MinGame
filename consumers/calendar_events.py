import asyncio

from aiokafka import AIOKafkaConsumer
from app.util.config import settings
from consumers.main import decode_message

loop = asyncio.get_event_loop()


async def consume_calendar_events():

    # Prints all settings from Vyper as read from all static files
    # print(f"ALL SETTINGS: {pformat(settings.all_settings(True), indent=2, width=260)}")

    # Prints all environ variables from the runtime
    # print(f"ALL ENV: {pformat(os.environ.__dict__, indent=2, width=260)}")

    # Get the most recent value, environment variable trumps most
    topic = settings.get('kafka.calendar_topic')
    server = settings.get('kafka.server')
    # Prints the `topic` from kafka.sms_topic in Vyper
    # Definition of this key is defined by TOML or by a pre-configured key
    print(f"CONSUMING {topic} TOPIC")
    # TODO add consumer group config! May need multiple consumers consuming this topic to process messages twice?
    consumer = AIOKafkaConsumer(
        "calendar",
        loop=loop, bootstrap_servers="localhost:29092",
    )
    # Get cluster layout and join group `my-group`
    await consumer.start()
    try:
        # Consume messages
        async for msg in consumer:
            # TODO if an error happens here - we lose the message I think!
            # print("consumed: ", msg.topic, msg.partition, msg.offset,
            #       msg.key, msg.value, msg.timestamp)
            print(f"consumed {decode_message(msg)}")
    finally:
        # Will leave consumer group; perform autocommit if enabled.
        await consumer.stop()

loop.run_until_complete(consume_calendar_events())
