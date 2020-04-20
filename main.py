from flask import Flask, Response, redirect
import flask
import json

import userData
import garageData
import checkinData
import carData
import spaceData

from google.oauth2 import id_token
from google.auth.transport import requests

from user import User
from car import Car
from garage import Garage
from checkin import Checkin
from space import Space


SIGN_IN_CLIENT_ID = '552110144556-qef3jf1sukp03o4khvjtcsu8kvs108tr.apps.googleusercontent.com'

app = flask.Flask(__name__)
app.secret_key = b'@U\xb0\xadf\x92f\xe8\x10\xee\xdf\x81O\x92\xb7\xe5\xca\x10rE&=\xd0\x7f'
# secret key is needed for flask sessions

def log(msg):
    """Log a simple message."""
    # Look at: https://console.cloud.google.com/logs to see your logs.
    # Make sure you have "stdout" selected.
    print('main: %s' % msg)



@app.route('/')
def root():
    return flask.redirect("/static/index.html", code=302)

@app.route('/userLoggedIn', methods=['GET'])
def userLoggedIn():
    log("enter userLoggedIn")
    json_result = {}
    json_result['user_id'] = flask.session['user_id']
    log(json_result)
    return flask.Response(json.dumps(json_result), mimetype='application/json')


@app.route('/add-garage', methods=['POST'])
def addGarage():
    log('Called addGarage') 
    garageName = flask.request.form['garageName']
    numSpots = flask.request.form['numSpots']
    numHandicapSpots = flask.request.form['numHandicapSpots']
    address = flask.request.form['address']
    phone = flask.request.form['phone']
    ownerDL = flask.request.form['ownerDL']
    log('About to create JSON')
    json_result = {}
    log('About to try')

    try:
        log('In try')
        garageData.createGarage(Garage(garageName, numSpots, numHandicapSpots, address, phone, ownerDL)) #First argument is gID, will use as key somehow, passing phone for now
        log('finished create garage')
        json_result['ok'] = True
        log('after json result')
    except Exception as exc:
        log('EXCEPTION')
        log(str(exc))
        json_result['error'] = str(exc)
    return flask.Response(json.dumps(json_result), mimetype='application/json')

@app.route('/load-garage', methods=['POST'])
def load_garage():
    gName = flask.request.form['garage_name']
    garageObj = garageData.load_garage(gName)
    g = garageObj.toDict()
    log(g)
    return flask.Response(json.dumps(g), mimetype='application/json')

@app.route('/populate-spots', methods=['POST'])
def populate_spots():
    available_spots = []
    list_to_return = []
    garageName = flask.request.form['garageName']
    checkinTime = flask.request.form['checkinTime']
    checkoutTime = flask.request.form['checkoutTime']
    handicap = flask.request.form['handicap']
    log('the value of handicap:')
    log(handicap)
    allSpotsInGarage = spaceData.load_all_spots(garageName)
    log(allSpotsInGarage)
    for spot in allSpotsInGarage:
        spotIsAvailable = True
        spot_id = spot.key.id_or_name
        log(spot_id)
        allCheckinsForSpot = checkinData.load_all_checkins(spot_id)
        log(allCheckinsForSpot)
        for checkin in allCheckinsForSpot:
            if checkin['time_in'] >= checkoutTime:
                continue
            if checkin['time_out'] <= checkinTime:
                continue
            spotIsAvailable = False
        if spotIsAvailable:
            available_spots.append(spot)
    for spot in available_spots:
        log('handicap?')
        log(spot['handicap'])
        if (spot['handicap'] and handicap) or (not spot['handicap'] and not handicap):
            s = spaceData._space_from_entity(spot)
            list_to_return.append(s.toDict())
    log('list to return:')
    log(list_to_return)
    return flask.Response(json.dumps(list_to_return), mimetype='application/json')
    
@app.route('/load-all-garages', methods=['POST'])
def load_all_garages():
    garage_list = garageData.load_all_garages()
    list_to_return = []
    for garage in garage_list:
        g = garageData._garage_from_entity(garage)
        list_to_return.append(g.toDict())
    log(list_to_return)
    return flask.Response(json.dumps(list_to_return), mimetype='application/json')


@app.route('/add-user', methods=['POST'])
def add_user():
    username = flask.request.form['username']
    phone = flask.request.form['phone']
    dl_no = flask.request.form['dl_no']
    json_result = {}
    try:
        log('Creating new user and adding to database')
        user_id = flask.session['user_id']
        userData.create_user(User(uid=user_id, username=username, phone=phone, dl_no=dl_no))
        json_result['ok'] = True
    except Exception as exc:
        log(str(exc))
        json_result['error'] = str(exc)
    return flask.Response(json.dumps(json_result), mimetype='application/json')

@app.route('/reserve-spot', methods=['POST'])
def reserve_spot():
    user_id = flask.session['user_id']
    time_in = flask.request.form['time_in']
    time_out = flask.request.form['time_out']
    garage_name = flask.request.form['garage_name']
    space_id = flask.request.form['spot_selected']
    checkin = Checkin(user_id, time_in, time_out, space_id, garage_name)
    json_result = {}
    try:
        checkinData.add_checkin(checkin)
        json_result['ok'] = True
    except:
        json_result['error'] = 'There was an error reserving this parking spot. Please try again.'
    return flask.Response(json.dumps(json_result), mimetype='application/json')


@app.route('/get-user', methods=['POST', 'GET'])
def get_user():
    user_id = flask.session['user_id']
    if user_id:
        user = userData.get_user(user_id)
        u = user.to_dict()
    return flask.Response(json.dumps(u), mimetype='application/json')

@app.route('/login', methods=['POST'])
def login():
    jd = JsonData()
    user_token = flask.request.form['id_token']
    email = flask.request.form['email']
    user_id = None
    validate_user(user_token, jd)
    if len(jd.errors) != 0:
        log('there were errors logging the user in')
        return show_json(jd)
    else:
        user_id = jd.data['user_id']
        flask.session['user_id'] = user_id # store the user_id in the session to use later
        if userData.get_user(user_id):
            jd.set_data({
                    'user_in_db' : "true",
                    'user_id' : user_id,
                })
            return show_json(jd)
        else:
            jd.set_data({
                    'user_in_db' : "false",
                    'user_id' : user_id,
                })
            return show_json(jd)

@app.route('/dologout', methods=['GET'])
def dologout():
    flask.session['user_id'] = None
    return flask.redirect('/')


# takes the token_id given by google and returns the user id for that token
# if the token is valid
def validate_user(user_token, jsonData):
    log('validating user')
    try:
        idinfo = id_token.verify_oauth2_token(user_token, requests.Request(), SIGN_IN_CLIENT_ID)

        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            jsonData.errors.append('Unable to authenticate the user token')
            jsonData.errors.append('Please try logging in again')

        # ID token is valid. Get the user's Google Account ID from the decoded token.
        user_id = idinfo['sub']
        jsonData.set_data({
                'user_id' : user_id
            })
    except ValueError:
        # Invalid token
        jsonData.errors.append('There was an error validating the user')


class PageData(object):
    def __init__(self, title):
        self.title = title
        self.errors = []
        self.p = {}

    def add_error(self, error):
        self.errors.append(error)

    def set_param(self, key, value):
        self.p[key] = value

class JsonData(object):
    def __init__(self):
        self.errors = []
        self.status = []

    def add_error(self, error):
        self.errors.append(error)

    def add_status(self, status):
        self.status.append(status)

    def set_data(self, data):
        self.data = data

def show_json(json_data):
    response_dict = {
        'errors': json_data.errors,
        'status': json_data.status,
        'data': json_data.data,
    }
    responseJson = json.dumps(response_dict)
    log('responseJson: ' + responseJson)
    return flask.Response(responseJson, mimetype='application/json')

@app.route('/add-car', methods=['POST'])
def addCar():
    make = flask.Flask.request.form['make']
    model = flask.Flask.request.form['model']
    plate_num = flask.Flask.request.form['plate_num']
    json_result = {}
    try:
        log('Creating a new Car and adding it to db')
        carData.createCar(Car(None, make, model, plate_num))
        json_result['ok'] = True
    except Exception as exc:
        log(str(exc))
        json_result['error'] = str(exc)
    return flask.Response(json.dumps(json_result), mimetype='application/json')

# this is for testing if it works, probably don't need
@app.route('/load-car')
def loadCarTest(plate_num):
        log('loading Car.')
        carObj = carData.load_car(plate_num)
        car = carObj.toDict()
        json_list = []
        for key in car:
            json_list.append(car[key])

        responseJson = json.dumps(json_list)
        return flask.Response(responseJson, mimetype='application/json')

@app.route('/add-space', methods=['POST'])
def addSpace():
    space_id = flask.request.form['space_id']
    floor = flask.request.form['floor']
    taken = flask.request.form['taken']
    json_result = {}
    try:
        log('Creating new space and adding to database')
        spaceData.createSpace(Space(None, id, floor, taken))
        json_result['ok'] = True
    except Exception as exc:
        log(str(exc))
        json_result['error'] = str(exc)
    return flask.Response(json.dumps(json_result), mimetype='application/json')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
