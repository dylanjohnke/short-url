import os
import requests
import datetime
import random
import string
from flask import Flask, request, redirect, render_template
from flask_pymongo import PyMongo

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb+srv://dylanjohnke:e1Ws5CfwVzRjZxpV@testcluster-sgdxe.mongodb.net/Development"

mongo = PyMongo(app)

url_list = []

mongo.db.systemInfo.update_one({'descriptor' : 'startups'}, {'$push': {'startup' : datetime.datetime.now()}}, upsert=True)

@app.route('/')
def default():
    return 'Send an HTTP request to use shortUrl service'


@app.route('/create-short-url', methods=['POST'])
def create_short_url():
    request_data = request.get_json()
    destination = request_data['to']
    url = '/short/'

    existing_url = mongo.db['destinations'].find_one({"destination": destination})
    if (existing_url != None):
        print(existing_url)
        random_path = existing_url['random_path']
    else:
        random_path = None

        #Loop to make sure that you haven't generated a random path that already exists 
        #Note: This should almost always loop only once, but just in case there is a timeout
        timeout = 0
        while (random_path == None):
            random_path = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(8)])

            found_existing = mongo.db.shortUrls.find_one({'path' : random_path})
            if (found_existing != None):
                random_path = None
                timeout += 1
            if timeout > 100:
                return 'Timeout error'

        mongo.db.shortUrls.insert({
            'path' : random_path, 
            'destination' : destination, 
            'created': datetime.datetime.now(),
            'visits': [],
            'visited_count': 0})
        mongo.db.destinations.insert({'random_path' : random_path, 'destination' : destination})

    url += random_path

    return url


@app.route('/create-custom-url', methods=['POST'])
def create_custom_url():
    request_data = request.get_json()
    destination = request_data['to']
    custom_path = request_data['custom_path']

    #Look to see if this custom url is already in use
    found_existing = mongo.db.shortUrls.find_one({'path' : custom_path})
    if (found_existing != None):
        if (found_existing['destination'] == destination):
            error = 'This custom url already points to that destination'
        else:
            error = 'Sorry, this custom url has already been taken'
        return error
    else:
        mongo.db.shortUrls.insert({
                    'path' : custom_path, 
                    'destination' : destination, 
                    'created': datetime.datetime.now(),
                    'visits': [],
                    'visited_count': 0})
        mongo.db.destinations.update_one({'destination' : destination}, {'$push': {'custom_paths' : custom_path}}, upsert=True)

    return '/short/' + custom_path


@app.route('/stats', methods=['GET'])
def get_stats():
    request_data = request.get_json()
    url = request_data['url']
    path = url.split('/short/').pop()

    short_url = mongo.db.shortUrls.find_one_or_404({"path": path})
    stats = {}
    stats['Time Created'] = short_url['created']
    stats['Total Visits'] = short_url['visited_count']
    visits = short_url['visits']
    uniqueIps = []
    histogram = {}

    for visit in visits:
        day = visit.time.date()
        if (histogram.get(day) == None):
            histogram[day] = 1
        else:
            histogram[day] += 1

        IP = visit.ip
        if IP not in uniqueIps:
            uniqueIps.append(IP)

    stats['Number of unique visitors'] = len(uniqueIps)
    stats['Histogram of Visits'] = histogram

    stringResponse = string(stats)

    return stringResponse


@app.route('/global-stats', methods=['GET'])
def get_global_stats():
    request_data = request.get_json()
    return "completed request"


@app.route('/short/<path>', methods=['GET'])
def send_to_destination(path):
    short_url = mongo.db.shortUrls.find_one_or_404({"path": path})
    if (short_url):
        dest = short_url['destination']
        total_visits = 1
        if (short_url['visited_count']):
            total_visits += short_url['visited_count']

        request_data = request.get_json()
        visitorIP = request_data.remote_addr
        mongo.db.shortUrls.update_one(
            {'path' : path},
            {'$push': {'visited' : {
            'time': datetime.datetime.today(),
            'ip': visitorIP}},
            'visited_count' : total_visits})
        mongo.db.systemInfo.update_one({'descriptor' : 'visits'}, {'$push': {'visits' : datetime.datetime.now()}}, upsert=True)

        return redirect(dest)


if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)






