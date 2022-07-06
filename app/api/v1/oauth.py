from http.client import NOT_FOUND, OK
from urllib import parse
from urllib.parse import urlencode

from flask import jsonify
from flask_restx import Namespace, fields, abort, Resource

from core.api.yandex.client import ApiRestClient
from core.api.yandex.router import APIRouter
from core.consts import YANDEX_SERVICE
from helpers.parsers import callback_code_parser
from models import OauthServices

api = Namespace('connect', description='OAuth')

yandex_link_schema = api.model('OAuthLink', {
    'oauth_link': fields.String(readonly=True, description='Link for OAuth identifications.')
})


@api.route('/yandex/')
class YandexOauth(Resource):
    @api.doc(description='Get Yandex OAuth link')
    @api.marshal_with(yandex_link_schema, code=OK)
    def get(self):
        yandex_settings = OauthServices.query.filter_by(service='yandex').first()

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
    @api.doc(description='Callback secret code.')
    @api.expect(callback_code_parser)
    def get(self):
        data = callback_code_parser.parse_args()
        router = APIRouter(service=YANDEX_SERVICE)
        client = ApiRestClient(router)
        credentials = client.get_credentials(secret_code=str(data.get('code')))

        user_info = client.get_user_info(access_token=credentials.get('access_token'))
        return jsonify(user_info)
