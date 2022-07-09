from datetime import datetime, timedelta
from http.client import NOT_FOUND, OK
from urllib import parse
from urllib.parse import urlencode

from core.api.yandex.client import ApiRestClient
from core.api.yandex.router import APIRouter
from core.consts import YANDEX_SERVICE
from flask import request
from flask_restx import Namespace, Resource, abort, fields
from helpers.parsers import callback_code_parser
from helpers.utility import (
    create_new_user,
    create_or_update_user_service,
    generate_password,
    get_user_device_type,
)
from models import OauthServices, User, UserSessions


api = Namespace('connect', description='OAuth')

yandex_link_schema = api.model('OAuthLink', {
    'oauth_link': fields.String(readonly=True, description='Link for OAuth identifications.')
})
oauth_schema = api.model('Tokens', {
    'access_token': fields.String(readonly=True, description='Access token'),
    'refresh_token': fields.String(readonly=True, description='Refresh token'),
    'temporary_password': fields.String(
        readonly=True, description='Temporary password')
})


@api.route('/yandex/')
class YandexOauth(Resource):
    @api.doc(description='Get Yandex OAuth link')
    @api.marshal_with(yandex_link_schema, code=OK)
    def get(self):
        yandex_settings = OauthServices.get_service(service=YANDEX_SERVICE)

        if not yandex_settings:
            abort(NOT_FOUND, errors=['Настройки сервиса не найдены!'])

        url = f'{yandex_settings.host}/authorize'
        params = dict(
            response_type='code',
            client_id=yandex_settings.client_id
        )
        url_parts = list(parse.urlparse(url))
        query = dict(parse.parse_qsl(url_parts[4]))
        query.update(params)
        url_parts[4] = urlencode(query)
        return dict(oauth_link=parse.urlunparse(url_parts))


@api.route('/yandex/code/')
class Code(Resource):
    @api.doc(description='Authorization with Yandex service.')
    @api.expect(callback_code_parser)
    @api.marshal_with(oauth_schema, code=OK)
    def get(self):
        temporary_password = None
        args = callback_code_parser.parse_args()
        router = APIRouter(service=YANDEX_SERVICE)
        client = ApiRestClient(router)

        credentials = client.get_credentials(secret_code=str(args.get('code')))
        user_info = client.get_user_info(access_token=credentials.get('access_token'))
        user = User.query.filter_by(email=user_info.get('default_email')).first()

        # Создаем пользователя, если ранее не был зарегистрирован.
        if not user:
            temporary_password = generate_password()
            data = dict(
                email=user_info.get('default_email'),
                password=temporary_password,
                first_name=user_info.get('first_name', None),
                last_name=user_info.get('last_name', None),
            )
            user = create_new_user(data)

        oauth_service = dict(
            user_id=user.pk,
            service=YANDEX_SERVICE,
            access_token=credentials.get('access_token'),
            refresh_token=credentials.get('refresh_token'),
            token_type=credentials.get('token_type'),
            access_token_expires=datetime.utcnow() + timedelta(
                seconds=credentials.get('expires_in')),
            refresh_token_expires=datetime.utcnow() + timedelta(
                seconds=credentials.get('expires_in'))
        )
        # Создаем, либо обновляем OAuth сервис пользователя
        create_or_update_user_service(oauth_service)
        # Создаем новую сессию
        new_session = UserSessions(
            user_id=user.pk,
            user_agent=request.headers.get('User-Agent'),
            last_login=datetime.utcnow(),
            user_device_type=get_user_device_type(request.headers.get('User-Agent'))
        )
        new_session.save()
        response = user.get_jwt_token()
        response.update(dict(temporary_password=temporary_password))
        return response
