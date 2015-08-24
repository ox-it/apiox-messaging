import datetime

from aiohttp.web import Response
from aiohttp.web_exceptions import HTTPBadRequest

from apiox.core.handlers import BaseHandler
from apiox.core.models import Token
from apiox.core.token import hash_token

class IndexHandler(BaseHandler):
    def __call__(self, request):
        pass

class RabbitMQAuthHandler(BaseHandler):
    def user(self, request):
        try:
            username, password = request.GET['username'], request.GET['password']
        except KeyError:
            raise HTTPBadRequest
        access_token_hash = hash_token(request.app, password)
        try:
            token = Token.objects.get(id=username,
                                      access_token_hash=access_token_hash)
        except Token.DoesNotExist:
            return Response(body=b'deny', content_type='text/plain')
        if token.refresh_at and token.refresh_at <= datetime.datetime.utcnow():
            return Response(body=b'deny', content_type='text/plain')
        return Response(body=b'allow', content_type='text/plain')

    def vhost(self, request):
        try:
            body = b'allow' if request.GET['vhost'] == '/' else b'deny'
        except KeyError:
            raise HTTPBadRequest
        return Response(body=body, content_type='text/plain')

    def resource(self, request):
        pass