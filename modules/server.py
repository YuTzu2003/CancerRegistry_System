import logging

from waitress import serve

from modules.config import get_env, get_int_env


def run_server(app, app_env, app_debug):
    if app_env == "production":
        waitress_host = get_env("WAITRESS_HOST")
        waitress_port = get_int_env("WAITRESS_PORT")
        logging.info("Waitress server starting on %s:%s", waitress_host, waitress_port)
        serve(app, host=waitress_host, port=waitress_port, threads=get_int_env("WAITRESS_THREADS"), backlog=get_int_env("WAITRESS_BACKLOG"), connection_limit=get_int_env("WAITRESS_CONNECTION_LIMIT"), channel_timeout=get_int_env("WAITRESS_CHANNEL_TIMEOUT"), trusted_proxy=get_env("TRUSTED_PROXY"), trusted_proxy_headers={"x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-forwarded-port"}, clear_untrusted_proxy_headers=True)
        return

    flask_port = get_int_env("FLASK_PORT")
    flask_host = get_env("FLASK_HOST")
    app.run(host=flask_host, port=flask_port, debug=app_debug)
