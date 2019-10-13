import os
import requests
import datetime
import random
import string
from flask import Flask, request, redirect, render_template
from flask_pymongo import PyMongo

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb+srv://dylanjohnke:enjoy0your0rabbit@testcluster-sgdxe.mongodb.net/Development"
#app.config["MONGO_URI"] = "mongodb+srv://dylanjohnke:enjoy0your0rabbit@testcluster-sgdxe.mongodb.net/test?retryWrites=true&w=majority"

mongo = PyMongo(app)

url_list = []

mongo.db.systemInfo.update_one({'descriptor' : 'startups'}, {'$push': {'startup' : datetime.datetime.now()}}, upsert=True)

@app.route('/')
def search_form():
    return render_template('form.html')


@app.route('/create-short-url', methods=['POST'])
def create_short_url():
    request_data = request.get_json()
    destination = request_data['to']
    url = '/short/'

    existing_url = mongo.db['destinations'].find_one({"destination": destination})
    if (existing_url != None):
        print(existing_url)
        url += existing_url['random_path']
    else:
        random_path = None
        while (random_path == None):
            random_path = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(8)])

            found_existing = mongo.db.shortUrls.find_one({'path' : random_path})
            if (found_existing != None):
                random_path = None

        mongo.db.shortUrls.insert({'path' : random_path, 'destination' : destination})
        mongo.db.destinations.insert({'random_path' : random_path, 'destination' : destination})

        url += random_path

    return url


@app.route('/create-custom-url', methods=['POST'])
def create_custom_url():
    request_data = request.get_json()
    destination = request_data['to']
    custom_path = request_data['custom_path']

    found_existing = mongo.db.shortUrls.find_one({'path' : custom_path})
    if (found_existing != None):
        if (found_existing['destination'] == destination):
            error = 'This custom url already points to that destination'
        else:
            error = 'Sorry, this custom url has already been taken'
        return error
    else:
        mongo.db.shortUrls.insert({'path' : custom_path, 'destination' : destination})
        mongo.db.destinations.update_one({'destination' : destination}, {'$push': {'custom_paths' : custom_path}}, upsert=True)

    return '/short/' + custom_path


@app.route('/stats', methods=['GET'])
def get_stats():
    request_data = request.get_json()
    print(url_list)
    return "completed get request"


@app.route('/global-stats', methods=['GET'])
def get_global_stats():
    request_data = request.get_json()
    return "completed request"


@app.route('/short/<path>', methods=['GET'])
def send_to_destination(path):
    short_url = mongo.db.shortUrls.find_one_or_404({"path": path})
    dest = short_url['destination']
    return redirect(dest)


if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)