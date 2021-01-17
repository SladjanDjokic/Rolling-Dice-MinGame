from app import configure
from consumers.calling import consume_calls
from consumers.emailconsumer import consume_email
from consumers.texting import consume_sms
import asyncio
from app.config import parser, settings
import logging

logger = logging.getLogger(__name__)

loop = asyncio.get_event_loop()


if __name__ == '__main__':
    c = parser.add_argument_group('consumers')
    c.add_argument("--consumer-name", type=str, default='calls',
                   help="Define consumer to run in container")
    args = vars(parser.parse_args())
    configure(**args)
    consumer = settings.get('consumer_name')
    logger.debug(consumer)
    logger.debug(settings)
    if consumer == "calls":
        loop.run_until_complete(consume_calls())
    elif consumer == "email":
        loop.run_until_complete(consume_email())
    elif consumer == "sms":
        loop.run_until_complete(consume_sms())