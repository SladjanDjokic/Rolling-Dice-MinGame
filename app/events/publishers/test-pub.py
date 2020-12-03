from app.events.publishers.publisher import BaseProducer

config = {'bootstrap.servers': 'localhost:29092'}
p = BaseProducer(config)
p.topic = 'sms'
p.produce([''])
