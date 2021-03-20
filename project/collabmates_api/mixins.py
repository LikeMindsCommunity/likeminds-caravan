from django.db import transaction


class TransactionMixin(object):
    def dispatch(self, request, *args, **kwargs):
        with transaction.atomic():
            return super(TransactionMixin, self).dispatch(request, *args, **kwargs)
