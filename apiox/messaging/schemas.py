MESSAGES = 'messages'
PERSON_LIST = 'person-list'

_messages_schema = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'routing_key': {'type': 'string'},
            'body': {'type': ['string', 'object']},
            'headers': {'type': 'object', 'additionalProperties': {'type': 'string'}},
        }
    },
    'minItems': 1,
}

schemas = {
    MESSAGES: _messages_schema,
}
