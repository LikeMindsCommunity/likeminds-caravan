"""
Params not in use currently are commented out
"""
CORALOGIX_CONSTS = {
    'PAYLOAD_SCHEMA': {
        'privateKey': '[YOUR CORALOGIX PRIVATE KEY] | MANDATORY',
        'applicationName': '[YOUR APPLICATION NAME] | MANDATORY',
        'subsystemName': '[YOUR APPLICATION SUB SYSTEM] | MANDATORY',
        # 'computerName': '[YOUR COMPUTER NAME] | OPTIONAL',
        'logEntries': '[LIST OF {log_entry_schema} ENTRIES] | MANDATORY',
    },
    'LOG_ENTRY_SCHEMA': {
        'timestamp': '[TIME IN MILLISECONDS] | MANDATORY',
        'severity': '[SEVERITY LEVEL] | MANDATORY',
        'text': '[LOG MESSAGE] | MANDATORY',
        # 'category': 'OPTIONAL',
        # 'className': 'OPTIONAL',
        # 'methodName': 'OPTIONAL',
        # 'threadId': 'OPTIONAL',
    },
    'LOGGING_API_URL': 'https://api.coralogix.com/api/v1/logs',
    'LOGGING_API_METHOD': 'POST',
    'LOG_LEVEL': {
        'Debug': 1,
        'Verbose': 2,
        'Info': 3,
        'Warn': 4,
        'Error': 5,
        'Critical': 6,
    },
}
