import asyncio
import json

from aiokafka import AIOKafkaConsumer

from app.da import GroupDA
from app.da.member import MemberInfoDA, MemberNotificationsSettingDA
from consumers.main import decode_message
from app.util.email import send_mail, EmailAuthError
from app.util.crypto import get_totp
import logging

from app.config import settings

logger = logging.getLogger(__name__)

loop = asyncio.get_event_loop()


async def accept_group_join(event):
    status = event.get('kafka_group_status')
    # group = GroupDA.get_group(int(event.get('kafka_group_id')))
    # group_name = group.get('group_name')
    # inviter = MemberInfoDA().get_member_info(int(group.get('group_leader_id')))
    group_name = event.get('kafka_group_name')
    inviter = MemberInfoDA().get_member_info(int(event.get('kafka_group_leader_id')))
    invitee = MemberInfoDA().get_member_info(int(event.get('member_id')))
    email = get_email_info(inviter)
    print(f"### {email}")
    # print(get_email_info(invitee))
    if status == 'active':
        template = 'accept_group_invite'
        subject = "Group Invite Accepted"
    else:
        template = "decline_group_invite"
        subject = "Group Invite Declined"
    if email and template:
        try:
            send_mail(to_email=email,
                      subject=subject,
                      template=template,
                      data={"first_name": invitee.get('first_name').capitalize(),
                       "group_name": group_name.capitalize()}
                      )
        except EmailAuthError:
            logger.exception('Deleting invite due to unable \
                                                   to auth to email system')


async def invite_to_group(event):
    invitee = MemberInfoDA().get_member_info(int(event.get('kafka_invitee_id')))
    inviter = MemberInfoDA().get_member_info(int(event.get('member_id')))
    email = get_email_info(invitee)
    print(f"derp{email}")
    template = 'send_group_invite'
    subject = "You have been invited to join a group on AMERA Share"
    if email and template:
        # email = 'austin.nicholas255@gmail.com'
        print("SENDING EMAIL INVITE")
        try:
            send_mail(to_email=email,
                      subject=subject,
                      template=template,
                      data={"first_name": inviter.get('first_name').capitalize(),
                            "group_name": event.get('kafka_group_name').capitalize()}
                      )
        except EmailAuthError:
            logger.exception('Deleting invite due to unable \
                                                   to auth to email system')


async def request_contact(event):
    email = None
    template = None
    subject = None
    contact_sender = None
    members_list = event.get('kafka_contact_id_list')
    # Loop through list and see if they need an sms notification
    if members_list:
        for m in members_list:
            m = int(m)
            member_profile = MemberNotificationsSettingDA.get_notifications_setting(
                memberId=m)
            if member_profile:
                notification_settings = member_profile.get('data')
                if notification_settings:
                    # Check notificaiton settings for requestee
                    email_notification = notification_settings.get('email').get("RequestContact")
                    if email_notification:
                        # Get contact info for contact_requestee
                        contactee_info = MemberInfoDA().get_member_info(str(m))
                        email = get_email_info(contactee_info)
                        print(f"## {email}")
                        if email:
                            # Get first and last name for requester
                            contact_sender_id = int(event.get('member_id'))
                            contact_sender = MemberInfoDA().get_member_info(contact_sender_id)
                            template = 'send_contact_request'
                            subject = "Your Contact Info Has Been Requested in AMERA Share"
                            if email and template and contact_sender:
                                # email = 'austin.nicholas255@gmail.com'
                                try:
                                    send_mail(to_email=email,
                                              subject=subject,
                                              template=template,
                                              data={"first_name": contact_sender.get('first_name').capitalize(),
                                                    "last_name": contact_sender.get('last_name').capitalize()}
                                              )
                                except EmailAuthError:
                                    logger.exception('Deleting invite due to unable \
                                                                           to auth to email system')


async def respond_contact_request(event):
    status = event.get('kafka_contact_request_status')
    contacter = MemberInfoDA().get_member_info(int(event.get('kafka_contacter_id')))
    contactee = MemberInfoDA().get_member_info(int(event.get('member_id')))
    if status == 'active':
        email = get_email_info(contacter)
        template = 'accept_contact_request'
        subject = "Your contact request has been accepted"
    else:
        email = get_email_info(contacter)
        template = 'decline_contact_request'
        subject = "Your contact request has been declined"
    if email and template and contactee:
        # email = 'austin.nicholas255@gmail.com'
        try:
            send_mail(to_email=email,
                      subject=subject,
                      template=template,
                      data={"first_name": contactee.get('first_name').capitalize(),
                            "last_name": contactee.get('last_name').capitalize()}
                      )
        except EmailAuthError:
            logger.exception('Deleting invite due to unable \
                                                   to auth to email system')


def get_email_info(member):
    if member.get('contact_information'):
        for c in member.get('contact_information'):
            if c.get('device_type') == 'email':
                if c.get('enabled') and c.get('device_confirm_date') is not None:
                    email = c.get('device')
                    return email
    # elif member.get('email'):
    #     return member.get('email')
    raise Exception("No contact data found")


async def consume_email():

    # Prints all settings from Vyper as read from all static files
    # print(f"ALL SETTINGS: {pformat(settings.all_settings(True), indent=2, width=260)}")

    # Prints all environ variables from the runtime
    # print(f"ALL ENV: {pformat(os.environ.__dict__, indent=2, width=260)}")

    # Get the most recent value, environment variable trumps most
    topic = settings.get('kafka.email_topic')
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
            handler = EMAIL_EVENT_TYPE_HANDLERS.get(event.get('event_type'))
            if handler:
                logger.debug("### HANDLING")
                await handler(event)
    finally:
        # Will leave consumer group; perform autocommit if enabled.
        await consumer.stop()

EMAIL_EVENT_TYPE_HANDLERS = {"group_membership_response": accept_group_join,
                             "add_member_group": invite_to_group,
                             "create_contact": request_contact,
                             "contact_request_response": respond_contact_request
                             }
