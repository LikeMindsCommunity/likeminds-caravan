from django_prometheus.middleware import PrometheusBeforeMiddleware
from django_prometheus.utils import TimeSince

from external_services.logging.metrics import request_duration_metric


class CustomPrometheusBeforeMiddleware(PrometheusBeforeMiddleware):

    def _method(self, request):
        m = request.method
        if m not in (
            "GET",
            "HEAD",
            "POST",
            "PUT",
            "DELETE",
            "TRACE",
            "OPTIONS",
            "CONNECT",
            "PATCH",
        ):
            return "<invalid method>"
        return m

    def _get_view_name(self, request):
        view_name = "<unnamed view>"
        if hasattr(request, "resolver_match"):
            if request.resolver_match is not None:
                if request.resolver_match.view_name is not None:
                    view_name = request.resolver_match.view_name
        return view_name

    def process_response(self, request, response):

        self.metrics.responses_total.inc()
        if hasattr(request, "prometheus_before_middleware_event"):

            time_since = TimeSince(request.prometheus_before_middleware_event)

            self.metrics.requests_latency_before.observe(time_since)

            request_duration_metric.labels(
                method=self._method(request),
                view=self._get_view_name(request)
            ).observe(time_since)

        else:
            self.metrics.requests_unknown_latency_before.inc()
        return response
