from api import init_api
from flask import Flask
from flask_marshmallow import Marshmallow
from settings.config import configuration
from settings.database import init_db
from settings.datastore import init_datastore, init_datastore_commands
from settings.jwt import init_jwt


app = Flask(__name__)
app.config.from_object(configuration)

init_db(app)
init_datastore(app)
init_datastore_commands(app)
init_api(app)
init_jwt(app)

ma = Marshmallow(app)

app.app_context().push()


if __name__ == '__main__':
    app.run(debug=True)
