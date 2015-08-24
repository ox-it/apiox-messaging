from . import __version__
from . import handlers

prefix = 'messaging'
url_prefix = '/{}'.format(prefix)

#def register_amqp_bind_auth_handler(*, pattern, token, ):

def register_services(app):
    app['register_amqp_bind_auth_handler'] = register_amqp_bind_auth_handler

def hook_in(app):
    app['definitions'][prefix] = {'title': 'Messaging API',
                                  'version': __version__}

    app.router.add_route('GET', url_prefix,
                         handlers.IndexHandler(),
                         name='messaging:index')
    
    app.router.add_route('GET', '/rabbitmq-auth/user',
                         handlers.RabbitMQAuthHandler().user,
                         name='rabbitmq-auth:user')
    app.router.add_route('GET', '/rabbitmq-auth/vhost',
                         handlers.RabbitMQAuthHandler().vhost,
                         name='rabbitmq-auth:vhost')
    app.router.add_route('GET', '/rabbitmq-auth/resource',
                         handlers.RabbitMQAuthHandler().resource,
                         name='rabbitmq-auth:resource')
