import sys
from confluent_kafka import KafkaError
from confluent_kafka.admin import AdminClient, NewTopic
from app.config import settings


def create_topic(topic):
    """
        Create a topic if needed
        Examples of additional admin API functionality:
        https://github.com/confluentinc/confluent-kafka-python/blob/master/examples/adminapi.py
    """
    print("### Admin")
    # a = AdminClient({
    #     'bootstrap.servers': settings.get('kafka.bootstrap_servers'),
    #     'sasl.mechanisms': settings.get('kafka.sasl.mechanisms'),
    #     'security.protocol': settings.get('kafka.security.protocol'),
    #     'sasl.username': settings.get('kafka.sasl.username'),
    #     'sasl.password': settings.get('kafka.sasl.password'),
    # })
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

    a = AdminClient(kafka_conf)
    fs = a.create_topics([NewTopic(
        topic,
        num_partitions=1,
        replication_factor=3
    )])
    for topic, f in fs.items():
        try:
            f.result()  # The result itself is None
            print("Topic {} created".format(topic))
        except Exception as e:
            # Continue if error code TOPIC_ALREADY_EXISTS, which may be true
            # Otherwise fail fast
            if e.args[0].code() != KafkaError.TOPIC_ALREADY_EXISTS:
                print("Failed to create topic {}: {}".format(topic, e))
                sys.exit(1)
