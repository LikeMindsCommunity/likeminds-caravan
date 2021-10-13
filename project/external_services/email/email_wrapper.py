from ..email.email_manager import MailManager
from django.core.mail import EmailMultiAlternatives
from celery import shared_task


class MailWrapper(MailManager):

    from_email = 'LikeMinds<hello@likeminds.community>'

    @staticmethod
    @shared_task
    def send_email(subject, template, to_mails_list, from_email=None, categories=None, reply_to=None):

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

        if categories is not None:
            email.categories = categories

        status = email.send(fail_silently)

        if status == 1:
            return True

        return False
