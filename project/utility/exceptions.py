from utility.tasks import send_email
from django.shortcuts import render
from django.template.loader import get_template
from django.http import HttpResponse, HttpResponseServerError, HttpResponseNotFound


def handler404(request, exception=None):

    subject = "404 Page Not Found exception in Main server"
    template = "mails/exceptions/page_not_found_exception.html"
    requested_path = exception.args[0].get('path')
    template = get_template(template).render({"exception": exception,
                                              'requested_path':requested_path,
                                                                  'subject': subject
                                                                  })
    to_mails_list = ['mahesh61437mahe@gmail.com']

    if not requested_path[0:6] == 'static':
        send_email.delay(subject, template, to_mails_list)

    template_404 = get_template('__404__.html')

    return HttpResponseNotFound(template_404)


def handler500(request, exception=None):
    subject = "500 Server Error in Main server"
    template = "mails/exceptions/server_error.html"
    template = get_template(template).render({"exception": exception,
                                              'subject': subject
                                              })
    to_mails_list = ['mahesh61437mahe@gmail.com']
    send_email.delay(subject, template, to_mails_list)

    template_500 = get_template("500.html")
    return HttpResponseNotFound(template_500)



