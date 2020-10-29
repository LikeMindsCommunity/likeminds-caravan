from utility.tasks import send_email
from django.template.loader import get_template
from django.http import HttpResponse
from django.template import loader
import logging
error_logger = logging.getLogger("error_logger")
info_logger = logging.getLogger("info_logger")


def handler404(request, exception=None):

    requested_path = exception.args[0].get('path')
    info_logger.info(f"404 Page Not Found exception ---->  {requested_path}")

    # subject = "404 Page Not Found exception in Main server"
    # template = "mails/exceptions/page_not_found_exception.html"
    # template = get_template(template).render({"exception": exception,
    #                                           'requested_path': requested_path,
    #                                           'subject': subject})
    # to_mails_list = ['mahesh61437mahe@gmail.com']
    #
    # if not requested_path[0:6] == 'static':
    #     send_email(subject, template, to_mails_list)
    # template = loader.get_template('__404__.html')
    #
    # return HttpResponse(template.render())



# def handler500(request, exception=None):
#     subject = "500 Server Error in Main server"
#     template = "mails/exceptions/server_error.html"
#     print(exception)
#     template = get_template(template).render({"exception": exception,
#                                               'subject': subject
#                                               })
#     to_mails_list = ['mahesh61437mahe@gmail.com']
#     send_email(subject, template, to_mails_list)
#
#     template = loader.get_template('500.html')
#     return HttpResponse(template.render())



