import logging
from waitress import serve
from modules.config import BaseConfig

def run_server(flask_app, app_env, app_debug):
    if app_env == "production":
        BaseConfig.validate_production_server()
        logging.info("Waitress server starting on %s:%s", BaseConfig.WAITRESS_HOST, BaseConfig.WAITRESS_PORT)
        serve(flask_app, host=BaseConfig.WAITRESS_HOST, port=BaseConfig.WAITRESS_PORT, threads=BaseConfig.WAITRESS_THREADS, backlog=BaseConfig.WAITRESS_BACKLOG, connection_limit=BaseConfig.WAITRESS_CONNECTION_LIMIT, channel_timeout=BaseConfig.WAITRESS_CHANNEL_TIMEOUT, trusted_proxy=BaseConfig.TRUSTED_PROXY, trusted_proxy_headers={"x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-forwarded-port"}, clear_untrusted_proxy_headers=True)
        return
    flask_app.run(host=BaseConfig.FLASK_HOST, port=BaseConfig.FLASK_PORT, debug=app_debug)