import os

import sendgrid
from django.conf import settings
from sendgrid import Email
from sendgrid.helpers.mail import Mail, Personalization, Content, Category

from rest_framework import status as status_codes

from collabmates_api.notifications.constants import SENDER_NAME_FOR_EMAIL_COMMS
from utility.mail_category_constants import MAIL_CATEGORY_BETA, MAIL_CATEGORY_PROD
from ..email.email_manager import MailManager
from django.core.mail import EmailMultiAlternatives
from celery import shared_task

from ..logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class MailWrapper(MailManager):
    from_email = 'LikeMinds<hello@likeminds.community>'
    from_email_id = 'hello@likeminds.community'

    @staticmethod
    @shared_task
    def send_email(subject, template, to_mails_list, attachments=[], from_email=None, categories=None, reply_to=None):

        if not from_email:
            from_email = MailWrapper.from_email

        if not reply_to:
            reply_to = [from_email]

        fail_silently = False
        email = EmailMultiAlternatives(
            subject,
            template,
            from_email,
            to_mails_list,
            reply_to=reply_to
        )
        email.attach_alternative(template, "text/html")

        for file_path in attachments:
            email.attach_file(file_path, mimetype='application/octet-stream')

        if categories is not None:
            email.categories = categories

        status = email.send(fail_silently)

        if status == 1:
            return True

        return False

    @staticmethod
    @shared_task
    def send_email_with_custom_from_email(subject, template, to_mails_list, from_email=None, reply_to=None,
                                          categories=None, from_name=SENDER_NAME_FOR_EMAIL_COMMS):

        if not from_email:
            from_email = MailWrapper.from_email_id

        if not reply_to:
            reply_to = MailWrapper.from_email_id

        mail = Mail()

        for to_email in to_mails_list:
            personalization = Personalization()
            personalization.add_to(Email(to_email))
            mail.add_personalization(personalization)

        mail.from_email = Email(name=from_name, email=from_email)

        mail.subject = subject

        if reply_to:
            mail.reply_to = Email(email=reply_to)

        if categories:
            for category in categories:
                mail.add_category(Category(category))

        mail.add_content(Content('text/html', template))

        sendgrid_api_client = sendgrid.SendGridAPIClient(apikey=os.environ.get('SENDGRID_API_KEY'))

        try:
            response = sendgrid_api_client.client.mail.send.post(request_body=mail.get())

            if response.status_code == status_codes.HTTP_202_ACCEPTED:
                info_logger.info(f'Mail Successfully Sent | Subject = {subject}')
                info_logger.info(f'headers = {response.headers}')
                return True

        except Exception as e:
            error_logger.error(e.__dict__)

        return False


class MailHelper:

    @staticmethod
    def get_email_category_list_using_category_subcategory(category, subcategory):
        categories = []
        environment = MAIL_CATEGORY_BETA if settings.IS_BETA else MAIL_CATEGORY_PROD
        categories.append(environment)
        categories.append(f'{environment} - {category}')
        categories.append(f'{environment} - {category} - {subcategory}')
        return categories
