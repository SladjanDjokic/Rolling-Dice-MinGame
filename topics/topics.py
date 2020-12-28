from confluent_kafka.admin import AdminClient, NewTopic


class BaseTopic:

    def __init__(self):
        pass

    @classmethod
    def create_topics(cls, client_config, topics):
        # Add Servie ip's
        a = AdminClient(client_config)

        new_topics = [NewTopic(topic, num_partitions=3, replication_factor=1) for topic in topics]
        # Note: In a multi-cluster production scenario, it is more typical to use a replication_factor of 3 for durability.

        # Call create_topics to asynchronously create topics. A dict
        # of <topic,future> is returned.
        fs = a.create_topics(new_topics)

        # Wait for each operation to finish.
        for topic, f in fs.items():
            try:
                f.result()  # The result itself is None
                print("Topic {} created".format(topic))
            except Exception as e:
                print("Failed to create topic {}: {}".format(topic, e))


# TODO This needs to be run probably in a kafka script rather than through python when running docker
# client_config = {'bootstrap.servers': 'localhost:29092'}
# topics = ["calls", "email", "chat", "sms", "calendar", "errors", "forgot_password"]
# BaseTopic().create_topics(client_config, topics)
