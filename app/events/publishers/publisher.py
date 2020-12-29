from app.config import settings
import logging
from confluent_kafka import Producer
from app.events.conf_admin import create_topic

logger = logging.getLogger(__name__)

# Key for calendar topic


class BaseProducer:

    def __init__(self, config=None):
        kafka_conf = {
            'bootstrap.servers': settings.get('kafka.bootstrap_servers')
        }

        if settings.get('kafka.sasl.username'):
            kafka_conf.update({
                'sasl.mechanisms': settings.get('kafka.sasl.mechanisms'),
                'security.protocol': settings.get('kafka.security.protocol'),
                'sasl.username': settings.get('kafka.sasl.username'),
                'sasl.password': settings.get('kafka.sasl.password'),
            })

        if config:
            # self.p = Producer({'bootstrap.servers': 'kafka:9092'})
            kafka_conf = config

        self.p = Producer(kafka_conf)
        if not config:
            self.topic = ''

    @staticmethod
    def delivery_report(err, msg):
        """ Called once for each message produced to indicate delivery result.
            Triggered by poll() or flush(). """
        if err is not None:
            logger.debug('Message delivery failed: {}'.format(err))
        else:
            logger.debug('Message delivered to {} [{}] {}'.format(msg.topic(), msg.partition(), msg.value()))

    def produce(self, data_source):
        # create_topic(self.topic)
        for data in data_source:
            # Poll will trigger the callback self.deliver_report which indicates if the message has
            # successfully been delivered. Not sure if this means a consumer has read it or its been successfully
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
