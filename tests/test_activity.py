from confluent_kafka.cimpl import Producer
from falcon import testing
from app import create_app, KafkaProducerMiddleware
from app import configure
from app import settings

from mock import patch, Mock

# TODO Create a test db that create_app() will connect to instead?
# TODO How to test kafka? Capture the message and compare. Don't actually produce
# TODO


class MyTestCase(testing.TestCase):
    def setUp(self):
        super(MyTestCase, self).setUp()

        # Assume the hypothetical `myapp` package has a
        # function called `create()` to initialize and
        # return a `falcon.API` instance.
        self.app = create_app()
        configure()


class TestActivity(MyTestCase):

    @patch.object(Producer, 'produce')
    def test_change_password(self, mock_kafka):
        doc = {'health': 1.0, 'status': 'OK'}
        # TODO Need to somehow captrue kafka message without pushing to kafka
        result = self.simulate_post('/member/change-password')
        self.assertEqual(result.json, doc)
