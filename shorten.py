import os
import requests
from flask import Flask, request, render_template

app = Flask(__name__)

url_list = []

@app.route('/')
def search_form():
    return render_template('form.html')


@app.route('/create-short-url', methods=['POST'])
def create_short_url():
    request_data = request.get_json()
    url = request_data['url']
    url_list.append(url)

    print(url_list)
    return "completed create request"


@app.route('/create-custom-url', methods=['POST'])
def create_custom_url():
    request_data = request.get_json()
    return "completed request"


@app.route('/stats', methods=['GET'])
def get_stats():
    request_data = request.get_json()
    print(url_list)
    return "completed get request"


@app.route('/global-stats', methods=['GET'])
def get_global_stats():
    request_data = request.get_json()
    return "completed request"

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)