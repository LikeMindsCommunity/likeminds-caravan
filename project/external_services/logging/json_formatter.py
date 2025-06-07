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
        }

        # Get the message and try to parse it if it's JSON
        message = record.getMessage()
        try:
            message_dict = json.loads(message)
            # Instead of putting the JSON string in 'message', expand it into the log_data
            log_data.update(message_dict)
        except json.JSONDecodeError:
            # If message is not JSON, store it as is
            log_data['message'] = message

        # Rest of the HTTP request parsing logic for django.server
        if record.name == 'django.server':
            try:
                if '"' in message:
                    parts = message.split('"')
                    request_part = parts[1]
                    method = request_part.split()[0]
                    full_uri = request_part.split()[1]
                    url = full_uri.split('?')[0]
                    
                    status_code = int(parts[-1].strip().split()[0])
                    response_time = int(parts[-1].strip().split()[1])
                    
                    log_data.update({
                        'method': method,
                        'url': url,
                        'status_code': status_code,
                        'response_time': response_time
                    })
            except (IndexError, ValueError):
                pass

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
