from confluent_kafka import Consumer, KafkaError
import logging

logger = logging.getLogger(__name__)


local_config = {
          'bootstrap.servers': 'localhost:29092',
          'group.id': 'default',
          'default.topic.config':
              {
                'auto.offset.reset': 'smallest'
              }
         }


local_config_sms = {
          'bootstrap.servers': 'localhost',
          'group.id': 'sms.py',
          'default.topic.config':
              {
                'auto.offset.reset': 'smallest'
              }
         }

local_config_email = {
          'bootstrap.servers': 'localhost',
          'group.id': 'sms.py',
          'default.topic.config':
              {
                'auto.offset.reset': 'smallest'
              }
         }


def decode_message(msg):
    message = msg.value.decode('utf-8')
    return message


class BaseConsumer:

    def __init__(self, kafka_config=None):
        if not kafka_config:
            self.c = Consumer(local_config)
        else:
            self.c = Consumer(kafka_config)