# http_server.py

# Required imports
import os
import errno
import json
import sys
from flask import Flask, request, jsonify
# import your_firestore as y_f
import event_searcher as es

# Initialize Flask server
app = Flask(__name__)

process_collection = []

@app.route('/run-event-searcher', methods=['POST'])
def run_event_searcher():
    try:
        data = request.get_json()
        login = data.get('login', '')
        passwd = data.get('passwd', '')
        if passwd == '' or login == '':
            return jsonify({"Error ": "MISSING PASSWD and/or LOGIN"}), 400
        keyword = data.get('keyword', 'lgbt')
        location = data.get('location', 'paris')
        next_days = data.get('next_days', 16)
        event_searcher_process = es.EventSearcher(
            request.json['login'], request.json['passwd'], keyword, location, next_days)
        process_collection.append(event_searcher_process)
        event_searcher_process.start()
        return jsonify({"success": True}), 200
    except Exception as e:
        return f"An Error occured : {e}"

@app.route('/run-group-event-scraper', methods=['POST'])
def run_group_event_scraper():
    try:
        data = request.get_json()
        login = data.get('login', '')
        passwd = data.get('passwd', '')
        if passwd == '' or login == '':
            return jsonify({"Error ": "MISSING PASSWD and/or LOGIN"}), 400
        group_event_scraper_process = es.GroupEventScrapper(
            request.json['login'], request.json['passwd'])
        process_collection.append(group_event_scraper_process)
        group_event_scraper_process.start()
        return jsonify({"success": True}), 200
    except Exception as e:
        return f"An Error occured : {e}"


@app.route('/')
def ok_boomer():
    return "Ok Boomer!"

if __name__ == '__main__':
    port_number = 4200
    if sys.argv.__len__() > 2:
        try:
            arg_as_int = int(sys.argv[1])
            if arg_as_int > 1023 and arg_as_int < 65536:
                port_number = arg_as_int
            else:
                print( sys.argv[1] + ' is not a valid port number. Falling back to 4200')
        except ValueError:
            print('argument : '+ sys.argv[1] +'  is not a valid int')
    app.run(debug=True, port=port_number)
