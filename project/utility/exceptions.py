from utility.tasks import send_email
from django.shortcuts import render,render_to_response
from django.template.loader import get_template


def handler404(request, exception, template_name="__404__.html"):

    subject = "404 Page Not Found exception in Main server"
    template = "mails/exceptions/page_not_found_exception.html"
    requested_path = exception.args[0].get('path')
    template = get_template(template).render({"exception": exception,
                                              'requested_path':requested_path,
                                                                  'subject': subject
                                                                  })
    to_mails_list = ['mahesh61437mahe@gmail.com', 'rastogi.fresh88@gmail.com']
    send_email.delay(subject, template, to_mails_list)
    response = render_to_response("__404__.html")
    response.status_code = 404
    return response


def handler500(request, exception, template_name="500.html"):
    subject = "500 Server Error in Main server"
    template = "mails/exceptions/server_error.html"
    template = get_template(template).render({"exception": exception,
                                              'subject': subject
                                              })
    to_mails_list = ['mahesh61437mahe@gmail.com', 'rastogi.fresh88@gmail.com']
    send_email.delay(subject, template, to_mails_list)
    response = render_to_response("500.html")
    response.status_code = 500
    return response



