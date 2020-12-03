import os

from confluent_kafka import Producer
from app.config import settings
import logging
logger = logging.getLogger(__name__)


class BaseProducer:

    def __init__(self, config=None):
        if config:
            self.p = Producer(config)
        else:
            self.p = Producer({'bootstrap.servers': 'kafka:9092'})
            self.topic = ''

    @staticmethod
    def delivery_report(err, msg):
        """ Called once for each message produced to indicate delivery result.
            Triggered by poll() or flush(). """
        if err is not None:
            logger.debug('Message delivery failed: {}'.format(err))
        else:
            logger.debug('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))

    def produce(self, data_source):
        for data in data_source:
            # Poll will trigger the callback self.deliver_report which indicates if the message has
            # successfully been delivered. Not sure if this means a consumer has read it or its been succesfully
            # been delivered to a client
            self.p.poll(0)

            # Asynchronously produce a message, the delivery report callback
            # will be triggered from poll() above, or flush() below, when the message has
            # been successfully delivered or failed permanently.
            try:
                self.p.produce(self.topic, value=data.encode('utf-8'), callback=self.delivery_report)
            except Exception as exc:
                logger.exception(exc, exc_info=True)

        # Wait for any outstanding messages to be delivered and delivery report
        # callbacks to be triggered.
        self.p.flush()


# TODO There may be no need to have separate producers. Just add the topic to base class when instantiating
class SMSProducer(BaseProducer):
    def __init__(self):
        super().__init__()
        self.topic = settings.get('kafka.sms_topic')


class EmailProducer(BaseProducer):
    def __init__(self):
        super().__init__()
        self.topic = settings.get('kafka.email_topic')


class ChatProducer(BaseProducer):
    def __init__(self):
        super().__init__()
        self.topic = settings.get('kafka.chat_topic')


class CallingProducer(BaseProducer):
    def __init__(self):
        super().__init__()
        print("TOPIC ###")
        self.topic = settings.get('kafka.calls_topic')


