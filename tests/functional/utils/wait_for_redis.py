import redis
from settings.config import configuration
from utils import backoff


@backoff()
def check():
    r = redis.Redis(host=configuration.REDIS_HOST, port=configuration.REDIS_PORT)
    r.ping()


if __name__ == '__main__':
    check()
