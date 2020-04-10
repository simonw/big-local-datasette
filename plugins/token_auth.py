from datasette import hookimpl
import secrets


class TokenAuth:
    def __init__(
        self, app, secret, auth,
    ):
        self.app = app
        self.secret = secret
        self.auth = auth

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)

        authorization = dict(scope.get("headers") or {}).get(b"authorization") or b""
        expected = "Bearer {}".format(self.secret).encode("utf8")

        if secrets.compare_digest(authorization, expected):
            scope = dict(scope, auth=self.auth)

        return await self.app(scope, receive, send)


@hookimpl(trylast=True)
def asgi_wrapper(datasette):
    config = datasette.plugin_config("token-auth") or {}
    secret = config.get("secret")
    auth = config.get("auth")

    def wrap_with_asgi_auth(app):
        return TokenAuth(app, secret=secret, auth=auth,)

    return wrap_with_asgi_auth
