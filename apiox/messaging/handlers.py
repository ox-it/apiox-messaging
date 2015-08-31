import asyncio
import datetime

from aiohttp.web import Response
from aiohttp.web_exceptions import HTTPBadRequest

from apiox.core.handlers import BaseHandler
from apiox.core.db import Token
from apiox.core.token import hash_token

class IndexHandler(BaseHandler):
    def __call__(self, request):
        pass

class RabbitMQAuthHandler(BaseHandler):
    @asyncio.coroutine
    def user(self, request):
        try:
            username, password = request.GET['username'], request.GET['password']
        except KeyError:
            raise HTTPBadRequest
        access_token_hash = hash_token(request.app, password)
        token = yield from Token.get(id=username,
                                     access_token_hash=access_token_hash)
        if not token:
            return Response(body=b'deny', content_type='text/plain')
        if token.refresh_at and token.refresh_at <= datetime.datetime.utcnow():
            return Response(body=b'deny', content_type='text/plain')
        return Response(body=b'allow', content_type='text/plain')

    @asyncio.coroutine
    def vhost(self, request):
        try:
            body = b'allow' if request.GET['vhost'] == '/' else b'deny'
        except KeyError:
            raise HTTPBadRequest
        return Response(body=body, content_type='text/plain')

    @asyncio.coroutine
    def resource(self, request):
        pass
