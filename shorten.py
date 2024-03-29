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

default_page = 'Welcome to shortdy URL shortening service!<br/>\
Send an HTTP request to use shortUrl service<br/>\
The endpoints for the API are:<br/>\
/create-short-url<br/>\
POST<br/>\
Body: { "to" : destinationUrl } <br/>\
<br/>\
/create-custom-url<br/>\
POST<br/>\
Body: {<br/>\
"to" : destinationUrl <br/>\
"custom_path" : custom_path } <br/>\
<br/>\
/stats <br/>\
GET<br/>\
<br/>\
In addition, all GET requests for short urls generated by the service are routed by the service.\
'

mongo.db.systemInfo.update_one(
    {'descriptor' : 'startups'},
    {'$push': {'startup' : datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")}}, upsert=True)

@app.route('/')
def default():
    return default_page


# Body required
# Input: destination URL
# Output: short URL (or error)
@app.route('/create-short-url', methods=['POST'])
def create_short_url():
    request_data = request.get_json()
    destination = request_data['to']

    url = request.url_root + 'short/'

    existing_url = mongo.db['destinations'].find_one({"destination": destination})
    if (existing_url != None):
        print(existing_url)
        random_path = existing_url['random_path']
    else:
        random_path = None

        # Loop to make sure that you haven't generated a random path that already exists 
        # Note: This should almost always loop only once, but just in case there is a timeout
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
            'created': datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
            'visits': [],
            'visit_count': 0})
        mongo.db.destinations.insert({'random_path' : random_path, 'destination' : destination})

    url += random_path

    return url


# Body required
# Input: to: destination URL, custom_path: custom path
# Output: short URL (or error)
@app.route('/create-custom-url', methods=['POST'])
def create_custom_url():
    request_data = request.get_json()
    destination = request_data['to']
    custom_path = request_data['custom_path']
    accepted_characters = string.ascii_letters + string.digits + '-_'
    for c in custom_path:
        if (c not in accepted_characters):
            return c + ' is not an accepted character. Custom url endpoint accepts alphanumeric characters, -, and _'

    # Look to see if this custom url is already in use
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
                    'created': datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
                    'visits': [],
                    'visit_count': 0})
        mongo.db.destinations.update_one(
            {'destination' : destination},
            {'$push': {'custom_paths' : custom_path}}, upsert=True)

    url_root = request.url_root
    return url_root + 'short/' + custom_path


# Body required
# Input: short URL
# Output: Time Created, Total Visits, Number of unique visitors, and Histogram of Visits (or error)
@app.route('/stats', methods=['GET'])
def get_stats():
    request_data = request.get_json()
    url = request_data['url']
    path = url.split('/short/').pop()

    short_url = mongo.db.shortUrls.find_one_or_404({"path": path})
    stats = {}
    stats['Time Created'] = short_url['created']
    stats['Total Visits'] = short_url['visit_count']
    visits = short_url['visits']
    uniqueIps = []
    histogram = {}

    for visit in visits:
        visit_date = datetime.datetime.strptime(visit['time'], "%m/%d/%Y, %H:%M:%S")
        day = visit_date.strftime("%m/%d/%Y")
        if (histogram.get(day) == None):
            histogram[day] = 1
        else:
            histogram[day] += 1

        IP = visit['ip']
        if IP not in uniqueIps:
            uniqueIps.append(IP)

    stats['Number of unique visitors'] = len(uniqueIps)
    stats['Histogram of Visits (in UTC)'] = histogram

    stringResponse = str(stats)

    return stringResponse


# No body required
# Output: Most Visited Domain, Histogram of Visits per Domain, and Histogram of Visits per Day (or error)
@app.route('/global-stats', methods=['GET'])
def get_global_stats():
    visit_times = mongo.db.systemInfo.find_one({'descriptor' : 'visits'})
    if (visit_times == None or len(visit_times['visits']) == 0):
        return 'No URLs have been visited'

    all_visited_urls = list(mongo.db.shortUrls.find({'visit_count': {'$exists': True, '$ne': 0}}))
    
    dates_histogram = {}
    domains_histogram = {}
    for url in all_visited_urls:
        visits = url['visits']
        for visit in visits:
            visit_date = datetime.datetime.strptime(visit['time'], "%m/%d/%Y, %H:%M:%S")
            day = visit_date.strftime("%m/%d/%Y")
            if (dates_histogram.get(day) == None):
                dates_histogram[day] = 1
            else:
                dates_histogram[day] += 1

        destination = url['destination']
        parts = destination.split('//').pop().split('/')
        if (len(parts) > 0):
            domain = parts[0]
            if (domains_histogram.get(domain) == None):
                domains_histogram[domain] = url['visit_count']
            else:
                domains_histogram[domain] += url['visit_count']

    most_visited_domain = ''         
    if (domains_histogram != {}):
        most_visited_domain = str(max(domains_histogram, key=domains_histogram.get))

    global_stats = 'Global Stats:<br/>' + 'Most Visited Domain: '
    global_stats += most_visited_domain + ' <br/><br/>' + 'Visits per Domain:<br/>'
    global_stats += str(domains_histogram) + '<br/><br/>' + 'Visits per Day (in UTC):<br/>' + str(dates_histogram)

    return global_stats


# No body required
# Redirects short url
@app.route('/short/<path>', methods=['GET'])
def send_to_destination(path):
    short_url = mongo.db.shortUrls.find_one_or_404({'path': path})
    if (short_url):
        dest = short_url['destination']

        visitorIP = request.remote_addr
        mongo.db.shortUrls.update_one(
            {'path': path},
            {'$push': {'visits' : {
            'time': datetime.datetime.today().strftime("%m/%d/%Y, %H:%M:%S"),
            'ip': visitorIP}},
            '$inc': { 'visit_count': 1} })
        mongo.db.systemInfo.update_one(
            {'descriptor' : 'visits'},
            {'$push': {'visits' : datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")}},
            upsert=True)

        return redirect(dest)


if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)






