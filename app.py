import os
import datetime
from functools import wraps
from flask import Flask, request, render_template_string, make_response, redirect, url_for, jsonify

app = Flask(__name__)

# Production-safe Session Key: Strictly reads from environment variables.
# On Render, define "FLASK_SECRET_KEY" under your service's Environment tab.
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(24).hex()

# Private password to unlock the clipboard.
# On Render, define "APP_PASSWORD" under your service's Environment tab.
ACCESS_PASSWORD = os.environ.get("APP_PASSWORD", "kerempass")

# In-memory database to store your shared clipboard text
shared_data = {"text": "Welcome to your Cloud Clipboard! Paste text on your computer, view it instantly on your phone."}


def check_auth(token):
    # Lightweight session check using cookies
    return token == ACCESS_PASSWORD


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Read the login session cookie
        auth_cookie = request.cookies.get("clip_session")
        if not auth_cookie or not check_auth(auth_cookie):
            # If not authorized, redirect to the login page
            return redirect(url_for("login_route"))
        return f(*args, **kwargs)
    return decorated


HTML_LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Cloud Clipboard - Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, sans-serif; background: #f5f5f7; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .login-box { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; width: 100%; max-width: 320px; }
        input { width: 100%; padding: 12px; margin: 15px 0; border: 1px solid #ccc; border-radius: 8px; font-size: 16px; box-sizing: border-box; }
        button { background: #0071e3; color: white; border: none; padding: 12px; width: 100%; border-radius: 8px; font-size: 16px; cursor: pointer; font-weight: 500; }
        button:hover { background: #0077ed; }
        .error { color: #ff3b30; font-size: 14px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>Private Clipboard</h2>
        {% if error %}<p class="error">{{ error }}</p>{% endif %}
        <form method="POST">
            <input type="password" name="password" placeholder="Enter Password" autofocus required autocomplete="current-password">
            <button type="submit">Unlock</button>
        </form>
    </div>
</body>
</html>
"""

HTML_CLIPBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Cloud Clipboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, sans-serif; margin: 0; padding: 20px; background: #f5f5f7; color: #333; }
        .container { max-width: 600px; margin: 0 auto; }
        h2 { display: flex; justify-content: space-between; align-items: center; font-weight: 600; margin-bottom: 20px; }
        textarea { width: 100%; height: 150px; margin: 10px 0; padding: 12px; box-sizing: border-box; border-radius: 8px; border: 1px solid #ccc; font-size: 16px; outline: none; transition: border 0.2s; }
        textarea:focus { border-color: #0071e3; }
        button { background: #0071e3; color: white; border: none; padding: 10px 18px; border-radius: 8px; font-size: 15px; cursor: pointer; font-weight: 500; margin-right: 5px; }
        button:hover { background: #0077ed; }
        button.secondary { background: #8e8e93; }
        button.secondary:hover { background: #a2a2a7; }
        .box { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-top: 15px; }
        pre { white-space: pre-wrap; word-wrap: break-word; background: #f0f0f2; padding: 15px; border-radius: 6px; font-family: monospace; font-size: 14px; margin: 10px 0; }
        .btn-row { display: flex; justify-content: space-between; align-items: center; }
    </style>
</head>
<body>
    <div class="container">
        <h2>
            <span>Cloud Clipboard</span>
            <button class="secondary" onclick="window.location.href='/logout'" style="font-size: 13px; padding: 6px 12px;">Lock</button>
        </h2>
        <div class="box">
            <h3>Paste New Text</h3>
            <form method="POST" action="/update">
                <textarea name="content" placeholder="Paste your text or link here..."></textarea>
                <br>
                <button type="submit">Share to Clipboard</button>
            </form>
        </div>
        <div class="box">
            <h3>Shared Text</h3>
            <pre id="shared-content">{{ current_text }}</pre>
            <div class="btn-row">
                <button onclick="copyToClipboard()">Copy to Clipboard</button>
                <button class="secondary" onclick="window.location.reload()">Refresh</button>
            </div>
        </div>
    </div>
  
    <script>
        function copyToClipboard() {
            const text = document.getElementById("shared-content").innerText;
            navigator.clipboard.writeText(text).then(() => {
                alert("Copied to clipboard!");
            }).catch(err => {
                alert("Failed to copy automatically. Please select and copy manually.");
            });
        }
    </script>
</body>
</html>
"""


@app.route("/login", methods=["GET", "POST"])
def login_route():
    if request.method == "POST":
        password = request.form.get("password")
        if password == ACCESS_PASSWORD:
            # Set authorization cookie that expires in 30 days
            resp = make_response(redirect(url_for("index")))
            expires = datetime.datetime.now() + datetime.timedelta(days=30)
            resp.set_cookie("clip_session", ACCESS_PASSWORD, expires=expires, httponly=True, samesite="Lax")
            return resp
        return render_template_string(HTML_LOGIN_TEMPLATE, error="Incorrect Password!")
    return render_template_string(HTML_LOGIN_TEMPLATE, error=None)


@app.route("/logout")
def logout():
    resp = make_response(redirect(url_for("login_route")))
    resp.set_cookie("clip_session", "", expires=0)  # Expire the cookie immediately
    return resp


@app.route("/")
@requires_auth
def index():
    return render_template_string(HTML_CLIPBOARD_TEMPLATE, current_text=shared_data["text"])


@app.route("/update", methods=["POST"])
@requires_auth
def update():
    shared_data["text"] = request.form.get("content", "")
    return redirect(url_for("index"))


# API endpoints to let you read/write from Python terminal scripts or command line
@app.route("/api/text", methods=["GET"])
@requires_auth
def get_text_api():
    return jsonify({"text": shared_data["text"]})


@app.route("/api/text", methods=["POST"])
@requires_auth
def update_text_api():
    body = request.get_json(silent=True) or {}
    shared_data["text"] = body.get("text", request.form.get("content", ""))
    return jsonify({"status": "ok", "text": shared_data["text"]})


# Fallback development server runner
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
