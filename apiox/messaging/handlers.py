import asyncio
import datetime
import json
import logging

import aiohttp
import base64
from aiohttp.web import Response
from aiohttp.web_exceptions import HTTPBadRequest, HTTPNoContent
import asynqp
from aiohttp.web_ws import WebSocketResponse
from sqlalchemy.orm.exc import NoResultFound

from apiox.core.handlers import BaseHandler
from apiox.core.db import Token
from apiox.core.response import JSONResponse
from apiox.core.token import hash_token
from apiox.messaging.db import MessagingCredentials

logger = logging.getLogger('apiox.messaging')

class IndexHandler(BaseHandler):
    @asyncio.coroutine
    def get(self, request):
        return JSONResponse(body={
            '_links': {
                'self': {'href': request.path},
            }
        })


class MessagingHandler(BaseHandler):
    @asyncio.coroutine
    def get_amqp_connection(self, request):
        yield from self.require_authentication(request, require_scopes=('/messaging/connect',))
        mc, secret = MessagingCredentials.create_from_token(request.app, request.session, request.token)
        request.session.commit()
        return (yield from asynqp.connect('localhost', 5672,
                                          username=mc.id,
                                          password=secret,
                                          loop=request.app.loop))


class WebSocketInterfaceHandler(MessagingHandler):
    @asyncio.coroutine
    def get(self, request):
        connection = yield from self.get_amqp_connection(request)
        ws = WebSocketResponse()
        yield from ws.prepare(request)

        channel = connection.open_channel()
        consumer = self.get_consumer(request, channel, ws)

        while not ws.closed:
            msg = yield from ws.receive()
            if msg.tp != aiohttp.MsgType.text:
                continue
            try:
                msg = json.loads(msg.data)
            except ValueError:
                ws.send_str(json.dumps({'error': 'invalid_json'}))
            try:
                id, action = msg['id'], msg['action']
            except KeyError:
                pass


    def get_consumer(self, request, channel, ws):
        def handler(msg):
            ws.send_bytes()


class GetFromQueueHandler(MessagingHandler):
    @asyncio.coroutine
    def get(self, request):
        connection = yield from self.get_amqp_connection(request)
        channel = yield from connection.open_channel()
        try:
            queue_name = request.GET['queue']
        except KeyError:
            return JSONResponse(body={'error': 'missing_parameter',
                                      'error_description': "Missing 'queue' parameter"},
                                base=HTTPBadRequest)
        try:
            count = int(request.GET.get('count', 512))
        except ValueError:
            return JSONResponse(body={'error': 'bad_parameter',
                                      'error_description': "Parameter 'count' must be an int, or missing"},
                                base=HTTPBadRequest)

        queue = yield from channel.declare_queue(queue_name, durable=False, auto_delete=True)
        messages = []
        for i in range(count):
            message = yield from queue.get()
            if not message:
                break
            message.ack()
            print(message.__dict__)
            body = message.body.decode(message.content_encoding)
            if message.content_type == 'application/json':
                try:
                    body = json.loads(body)
                except ValueError:
                    pass

            messages.append({'headers': message.headers,
                             'body': body,
                             'content_type': message.content_type,
                             'reply_to': message.reply_to,
                             'message_id': message.message_id,
                             'timestamp': message.timestamp.isoformat(),
                             'routing_key': message.routing_key,
                             'exchange_name': message.exchange_name})

        yield from channel.close()
        return JSONResponse(body=messages)


class PublishToExchangeHandler(MessagingHandler):
    @asyncio.coroutine
    def post(self, request):
        messages = yield from self.validated_json(request, 'messaging', 'messages')
        connection = yield from self.get_amqp_connection(request)
        channel = yield from connection.open_channel()
        try:
            exchange_name = request.GET['exchange']
        except KeyError:
            return JSONResponse(body={'error': 'missing_parameter',
                                      'error_description': "Missing 'exchange' parameter"},
                                base=HTTPBadRequest)
        exchange = yield from channel.get_exchange(exchange_name)

        for message in messages:
            routing_key = message.pop('routing_key')
            exchange.publish(routing_key=routing_key,
                             message=asynqp.Message(**message))
        yield from channel.close()
        return HTTPNoContent()

class RabbitMQAuthHandler(BaseHandler):
    @asyncio.coroutine
    def user(self, request):
        try:
            username, password = request.GET['username'], request.GET['password']
        except KeyError:
            raise HTTPBadRequest
        try:
            secret_hash = hash_token(request.app, password)
            mc = request.session.query(MessagingCredentials).filter_by(id=username, secret_hash=secret_hash).one()
        except NoResultFound:
            logger.info("Denying access for user %s (bad credentials)", username)
            return Response(body=b'deny', content_type='text/plain')
        if not any(scope.id == '/messaging/connect' for scope in mc.scopes):
            logger.info("Denying access for user %s (missing scope)", username)
            return Response(body=b'deny', content_type='text/plain')
        logger.info("Allowing access for user %s", username)
        return Response(body=b'allow administrator', content_type='text/plain')

    @asyncio.coroutine
    def vhost(self, request):
        try:
            body = b'allow' if request.GET['vhost'] == '/' else b'deny'
        except KeyError:
            raise HTTPBadRequest
        return Response(body=body, content_type='text/plain')

    @asyncio.coroutine
    def resource(self, request):
        return Response(body=b'allow', content_type='text/plain')


class CredentialsHandler(BaseHandler):
    @asyncio.coroutine
    def post(self, request):
        yield from self.require_authentication(request)
        mc, secret = MessagingCredentials.create_from_token(request.app, request.session, request.token)

        return JSONResponse(
            body={'username': mc.id, 'password': secret},
            headers={'Pragma': 'no-cache'},
        )
