import datetime

from sqlalchemy import Column, String, ForeignKey, Table, Boolean, DateTime, Index
from sqlalchemy.orm import relationship

from apiox.core.db import Base, Token
from apiox.core.token import TOKEN_HASH_LENGTH, TOKEN_LENGTH, generate_token, hash_token, TOKEN_LIFETIME

messaging_credentials_scope = Table('messaging_credentials_scope', Base.metadata,
    Column('scope_id', String, ForeignKey('scope.id'), primary_key=True),
    Column('token_id', String(TOKEN_LENGTH), ForeignKey('messaging_credentials.id'), primary_key=True),
)

_default = object()

class MessagingCredentials(Base):
    __tablename__ = 'messaging_credentials'

    id = Column(String(TOKEN_LENGTH), primary_key=True)
    secret_hash = Column(String(TOKEN_HASH_LENGTH))

    account_id = Column(String(TOKEN_LENGTH), ForeignKey('principal.id'))
    client_id = Column(String(TOKEN_LENGTH), ForeignKey('principal.id'))
    token_id = Column(String(TOKEN_LENGTH), ForeignKey('token.id'), nullable=True)

    created_at = Column(DateTime)
    expire_at = Column(DateTime, nullable=True)

    scopes = relationship('Scope', secondary=messaging_credentials_scope, backref='messaging_credentials')

    multi_use = Column(Boolean)
    used = Column(Boolean)

    __table_args__ = (
        Index('messaging_credentials_with_token_idx',
              'account_id', 'client_id', 'token_id',
              postgresql_where=(token_id == None)),
        Index('messaging_credentials_without_token_idx',
              'account_id', 'client_id',
              postgresql_where=(token_id != None)),
    )

    @classmethod
    def create_from_token(cls, app, session, token, multi_use=False, expire_at=_default,
                          require_scope=True):
        secret = generate_token()
        if expire_at is _default:
            expire_at = datetime.datetime.utcnow() + datetime.timedelta(0, TOKEN_LIFETIME)
        if require_scope and not any(scope.id == '/messaging/connect' for scope in token.scopes):
            raise cls.MissingScope
        mc = MessagingCredentials(id=generate_token(),
                                  secret_hash=hash_token(app, secret),
                                  account_id=token.account_id,
                                  client_id=token.client_id,
                                  token_id=token.id if isinstance(token, Token) else None,
                                  created_at=datetime.datetime.utcnow(),
                                  expire_at=expire_at,
                                  scopes=token.scopes,
                                  multi_use=multi_use,
                                  used=False)
        session.add(mc)
        return mc, secret
