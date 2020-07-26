# Import smtplib for the actual sending function
import smtplib
import pathlib
import logging

# Import the email modules we'll need
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from jinja2 import Environment, FileSystemLoader

from app.config import settings

logger = logging.getLogger(__name__)

filepath = pathlib.Path(__file__).parent
parentpath = filepath.parent
template_folder = parentpath.joinpath("templates")
template_loader = FileSystemLoader(template_folder)
template_env = Environment(loader=template_loader)


class EmailAuthError (Exception):
    pass


def get_rendered_template(template, data):

    # Open the plain text file whose name is in textfile for reading.
    logger.debug("Template: {}".format(template))
    logger.debug("Template Data: {}".format(data))

    template = template_env.get_template(template)
    return template.render(data)


def send_mail(to_email, subject, template,
              data, from_email=None):
    logger.debug("Template Folder: {}".format(template_folder))

    logger.debug("To_email: {}".format(to_email))
    logger.debug("From_email: {}".format(from_email))
    logger.debug("Subject: {}".format(subject))
    logger.debug("Template: {}".format(template))
    logger.debug("Data: {}".format(data))

    if not from_email:
        from_email = settings.get("smtp.email_from")
        logger.debug("No FROM EMAIL passed, using settings")
        logger.debug("From_email: {}".format(from_email))

    message = MIMEMultipart()
    message["Subject"] = subject
    message["From"] = from_email
    message["To"] = to_email

    data.update({
        "product_name": "AMERA Share"
    })

    text_content = get_rendered_template("{}.txt".format(template), data)
    logger.debug("Text Email: {}".format(text_content))

    html_content = get_rendered_template("{}.html".format(template), data)
    logger.debug("HTML Email: {}".format(html_content))

    message.attach(MIMEText(text_content, "plain"))
    # message.attach(MIMEText(html_content, "html"))

    msgBody = message.as_string()

    logger.debug("SMTP_SERVER: {}".format(settings.get("smtp.server")))
    logger.debug("SMTP_PORT: {}".format(settings.get("smtp.port")))
    logger.debug("SMTP_USER: {}".format(settings.get("smtp.user")))
    logger.debug("SMTP_PASSWORD: {}".format(settings.get("smtp.password")))

    # # Create a secure SSL context
    # context = ssl.create_default_context()

    try:
        server = smtplib.SMTP_SSL(settings.get("smtp.server"))
        server.login(settings.get("smtp.user"), settings.get("smtp.password"))
        # server = smtplib.SMTP("localhost")
        server.sendmail(from_email, to_email, msgBody)
    except AttributeError:
        logger.exception("Unable to authenticate with SMTP server, "
                         "most likely PASSWORD is Empty in config and "
                         "was not passed as environment variable")
        raise EmailAuthError()
    except smtplib.SMTPAuthenticationError:
        logger.exception("Unable to authenticate with SMTP server "
                         "using provided credentials")
        raise EmailAuthError()
    finally:
        server.quit()
