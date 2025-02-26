import json
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.config import Config
from starlette.requests import Request
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from authlib.integrations.starlette_client import OAuth, OAuthError

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="!secret")

config = Config(".env")
oauth = OAuth(config)

CONF_URL = "https://accounts.google.com/.well-known/openid-configuration"
oauth.register(
    name="google",
    server_metadata_url=CONF_URL,
    client_kwargs={"scope": "openid email profile"},
)

# Serve static files from the directory containing chat-demo.html
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def homepage(request: Request):
    user = request.session.get("user")
    if user:
        data = json.dumps(user)
        html = f"<pre>{data}</pre>" '<a href="/logout">logout</a>'
        return HTMLResponse(html)
    return HTMLResponse('<a href="/login">login</a>')


@app.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth")
async def auth(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        return HTMLResponse(f"<h1>{error.error}</h1>")

    user = token.get("userinfo")
    if user:
        request.session["user"] = dict(user)

    # Save the tokens in local storage via JavaScript
    id_token = token["id_token"]
    auth_token = token["access_token"]

    html_content = f"""
    <script>
        localStorage.setItem('idToken', '{id_token}');
        localStorage.setItem('authToken', '{auth_token}');
        window.location.href = '/static/chat-demo.html';
    </script>
    """

    return HTMLResponse(html_content)


@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=9000)
