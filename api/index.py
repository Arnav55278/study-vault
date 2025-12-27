from flask import Flask
from app import app  # yeh tera original app.py se import kar raha hai

# Vercel ke liye handler (yeh important hai)
def handler(event, context):
    # Vercel event ko Flask ke request mein convert karta hai
    from werkzeug.wrappers import Request
    from werkzeug.serving import run_wsgi_app

    # Simple way: direct Flask app call
    return app(event, context)

# Local testing ke liye (ignore kar Vercel pe)
if __name__ == '__main__':
    app.run(debug=True)