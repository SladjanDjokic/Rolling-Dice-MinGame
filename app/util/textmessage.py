from app.clients.twilio import BaseTwilioClient


def send_sms(cell: str, message: str):
    """ Universal function to handle various clients and sms messages."""

    client = BaseTwilioClient()
    client.send_sms(cell, message)
