import json
import logging
import traceback
from datetime import datetime, timezone, timedelta

class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after gathering all the log record attributes
    """
    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs
        self.ist = timezone(timedelta(hours=5, minutes=30))

    def format(self, record):
        """
        Format the log record into a JSON string
        """
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created, tz=self.ist).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }

        # Parse HTTP request information if it's a server log
        if record.name == 'django.server':
            message = log_data['message']
            try:
                # Extract method and URI from messages like: "GET /api/sdk/mau_overview?no_of_months=3 HTTP/1.1" 200 392
                if '"' in message:
                    parts = message.split('"')  # Split by quotes
                    request_part = parts[1]  # Get the part between quotes
                    method = request_part.split()[0]  # First word is the method
                    full_uri = request_part.split()[1]  # Second part is the URI
                    url = full_uri.split('?')[0]  # Remove query parameters
                    
                    # Extract status code and response time from the end
                    status_code = int(parts[-1].strip().split()[0])  # First number after the quoted part
                    response_time = int(parts[-1].strip().split()[1])  # Second number after the quoted part
                    
                    log_data.update({
                        'method': method,
                        'url': url,
                        'status_code': status_code,
                        'response_time': response_time
                    })
            except (IndexError, ValueError):
                pass  # If parsing fails, we just won't add these fields

        # Add any extra attributes from the record
        if hasattr(record, 'props'):
            log_data.update(record.props)

        # Include exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': str(record.exc_info[0].__name__),
                'message': str(record.exc_info[1]),
                'traceback': ''.join(traceback.format_tb(record.exc_info[2])),
            }

        # Add any custom fields specified in kwargs
        if self.kwargs:
            log_data.update(self.kwargs)

        return json.dumps(log_data)
