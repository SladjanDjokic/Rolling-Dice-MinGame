import json
import asyncio

from aiokafka import AIOKafkaConsumer

from app.da import GroupDA
from app.da.member import MemberContactDA, MemberInfoDA, MemberNotificationsSettingDA
from app.util.textmessage import send_sms

from consumers.main import decode_message
from app import settings
import logging
logger = logging.getLogger(__name__)

loop = asyncio.get_event_loop()

CONTACT_REQUEST_SMS_TEMPLATE = "{} {} has requested you as a contact"
ACCEPT_GROUP_REQUEST_TEMPLATE = "{} has accepted your request to join {}."
DECLINE_GROUP_REQUEST_TEMPLATE = "{} has declined your request to join {}."
INVITE_USER_TO_GROUP_TEMPLATE = "{} has invited you to their group {}."
ACCEPT_CONTACT_REQUEST_TEMPLATE = "{} {} has accepted your contact request."
DECLINE_CONTACT_REQUEST_TEMPLATE = "{} {} has declined your contact request."


async def accept_group_join(event):
    status = event.get('kafka_group_status')
    # group = GroupDA.get_group(int(event.get('kafka_group_id')))
    # group_name = group.get('group_name')
    # inviter = MemberInfoDA().get_member_info(int(group.get('group_leader_id')))
    # invitee = MemberInfoDA().get_member_info(int(event.get('member_id')))
    group_name = event.get('kafka_group_name')
    inviter = MemberInfoDA().get_member_info(
        int(event.get('kafka_group_leader_id')))
    invitee = MemberInfoDA().get_member_info(int(event.get('member_id')))
    if status == 'active':
        number = MemberContactDA().get_member_cell(inviter)
        message = ACCEPT_GROUP_REQUEST_TEMPLATE
        message = message.format(invitee.get(
            'first_name').capitalize(), group_name.capitalize())
    else:
        number = MemberContactDA().get_member_cell(inviter)
        message = DECLINE_GROUP_REQUEST_TEMPLATE
        message = message.format(invitee.get(
            'first_name').capitalize(), group_name.capitalize())
    if number:
        # number = "6463151374"
        response = send_sms(number, message)


async def invite_to_group(event):
    invitee = MemberInfoDA().get_member_info(int(event.get('kafka_invitee_id')))
    inviter = MemberInfoDA().get_member_info(int(event.get('member_id')))
    number = MemberContactDA().get_member_cell(invitee)
    message = INVITE_USER_TO_GROUP_TEMPLATE
    message = message.format(inviter.get('first_name').capitalize(
    ), event.get('kafka_group_name').capitalize())
    if number:
        print("SENDING SMS INVITE")
        # number = "6463151374"
        response = send_sms(number, message)


async def request_contact(event):
    number = None
    message = None
    members_list = event.get('kafka_contact_id_list')
    # Loop through list and see if they need an sms notification
    #
    if members_list:
        for m in members_list:
            m = int(m)
            member_profile = MemberNotificationsSettingDA.get_notifications_setting(
                memberId=int(m))
            if member_profile:
                notification_settings = member_profile.get('data')
                if notification_settings:
                    # Check notificaiton settings for requestee
                    sms_notificaiton = notification_settings.get(
                        'sms').get("RequestContact")
                    if sms_notificaiton:
                        # Get contact info for contact_requestee
                        number = MemberContactDA().get_member_cell(m)
                        print(number)
                        # number = "16463151374"
                        if number:
                            # Get first and last name for requester
                            contact_sender_id = int(event.get('member_id'))
                            contact_sender = MemberInfoDA().get_member_info(contact_sender_id)
                            message = CONTACT_REQUEST_SMS_TEMPLATE.format(contact_sender.get('first_name').capitalize(),
                                                                          contact_sender.get('last_name').capitalize())
                            if number and message:
                                # number = "16463151374"
                                response = send_sms(number, message)

                else:
                    print('No notification settings found')


async def respond_contact_request(event):
    status = event.get('kafka_contact_request_status')
    print(status)
    contacter = MemberInfoDA().get_member_info(
        int(event.get('kafka_contacter_id')))
    contactee = MemberInfoDA().get_member_info(int(event.get('member_id')))
    if status == 'active':
        number = MemberContactDA().get_member_cell(contacter)
        # number = "19729032190"
        message = ACCEPT_CONTACT_REQUEST_TEMPLATE
        message = message.format(contactee.get(
            'first_name').capitalize(), contactee.get('last_name').capitalize())
        print(f"#### {message}")
    else:
        number = MemberContactDA().get_member_cell(contacter)
        message = DECLINE_CONTACT_REQUEST_TEMPLATE
        message = message.format(contactee.get(
            'first_name').capitalize(), contactee.get('last_name').capitalize())
        print(f"### {message}")
    if number:
        # number = "16463151374"
        response = send_sms(number, message)


def get_cell_info(member):
    for c in member.get('contact_information'):
        if c.get('device_type') == 'cell':
            if c.get('enabled') and c.get('device_confirm_date') is not None:
                number = c.get('device')
                return number
    raise Exception("No contact data found")


async def consume_sms():

    # Prints all settings from Vyper as read from all static files
    # print(f"ALL SETTINGS: {pformat(settings.all_settings(True), indent=2, width=260)}")

    # Prints all environ variables from the runtime
    # print(f"ALL ENV: {pformat(os.environ.__dict__, indent=2, width=260)}")

    # Get the most recent value, environment variable trumps most
    topic = settings.get('kafka.sms_topic')
    server = settings.get('kafka.server')

    # Prints the `topic` from kafka.sms_topic in Vyper
    # Definition of this key is defined by TOML or by a pre-configured key
    print(f"CONSUMING {topic} TOPIC")
    consumer = AIOKafkaConsumer(
        topic,
        loop=loop, bootstrap_servers=server,
    )
    # Get cluster layout and join group `my-group`
    await consumer.start()
    try:
        # Consume messages
        async for msg in consumer:
            print("consumed: ", msg.topic, msg.partition, msg.offset,
                  msg.key, msg.value, msg.timestamp)
            event = json.loads(decode_message(msg))
            handler = SMS_EVENT_TYPE_HANDLERS.get(event.get('event_type'))
            if handler:
                logger.debug("### HANDLING")
                await handler(event)
    finally:
        # Will leave consumer group; perform autocommit if enabled.
        await consumer.stop()

SMS_EVENT_TYPE_HANDLERS = {"group_membership_response": accept_group_join,
                           "add_member_group": invite_to_group,
                           "create_contact": request_contact,
                           "contact_request_response": respond_contact_request
                           }
