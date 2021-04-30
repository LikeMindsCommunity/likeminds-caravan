from prometheus_client import Histogram

request_duration_metric = Histogram(name='django_http_requests_latency_including_middlewares_seconds_by_view_method',
                                    documentation='request duration of api',
                                    labelnames=['method', 'view'],
                                    buckets=[0.1, 0.2, 0.5, 0.75, 1.0, 2.0, 5.0, 60.0]
                                    )
