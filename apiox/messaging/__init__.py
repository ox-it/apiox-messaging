import asyncio

from apiox.core import API
from . import db
from .schemas import schemas

__version__ = '0.1'
api_id = 'messaging'
url_prefix = '/{}/'.format(api_id)


@asyncio.coroutine
def setup(app):
    from . import handlers

    app['schemas'][api_id] = schemas

    app.router.add_route('*', url_prefix,
                         handlers.IndexHandler(),
                         name='messaging:index')
    app.router.add_route('*', url_prefix + 'credentials',
                         handlers.CredentialsHandler(),
                         name='messaging:credentials')

    app.router.add_route('*', url_prefix + 'websocket',
                         handlers.WebSocketInterfaceHandler(),
                         name='messaging:websocket')

    app.router.add_route('GET', url_prefix +'get',
                         handlers.GetFromQueueHandler(),
                         name='messaging:get')
    app.router.add_route('POST', url_prefix +'publish',
                         handlers.PublishToExchangeHandler(),
                         name='messaging:publish')

    app.router.add_route('GET', '/rabbitmq-auth/user',
                         handlers.RabbitMQAuthHandler().user,
                         name='rabbitmq-auth:user')
    app.router.add_route('GET', '/rabbitmq-auth/vhost',
                         handlers.RabbitMQAuthHandler().vhost,
                         name='rabbitmq-auth:vhost')
    app.router.add_route('GET', '/rabbitmq-auth/resource',
                         handlers.RabbitMQAuthHandler().resource,
                         name='rabbitmq-auth:resource')


def declare_api(session):
    session.merge(API.from_json({
        'id': api_id,
        'title': 'Messaging API',
        'version': __version__,
        'scopes': [{
            'id': '/messaging/connect',
            'title': 'Connect to the message queue',
            'grantedToUser': True,
        }],
    }))