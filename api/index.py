from flask import Flask, request
from werkzeug.wrappers import Response

# Tera original app import kar
from app import app  # agar tera main file app.py hai

def handler(event, context):
    # Vercel event ko Flask request mein convert
    req = request.get_json() if request.is_json else request.form.to_dict()
    # Simple handler: Flask app ko call kar
    response = app(event, context)
    return Response(response, status=200)

# Local testing ke liye
if __name__ == '__main__':
    app.run(debug=True)