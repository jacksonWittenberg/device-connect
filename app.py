from ast import Return
import logger
import os
import base64
import requests
import pandas as pd
import pandas_gbq
from datetime import date, datetime, timedelta, time
from functools import wraps
from flask import (
    Flask,
    abort,
    render_template,
    request,
    jsonify,
    redirect,
    session,
)
import firebase_admin
from firebase_admin import firestore
from requests_oauthlib import OAuth2Session
from skimpy import clean_columns
import config


app = Flask(__name__)

app.config.update(SECRET_KEY=os.urandom(24))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/jacksonwittenberg/Desktop/secrets/starterkit-service-account.json"
os.environ["GOOGLE_CLOUD_PROJECT "] = "starterkit-344119"

#
# Initialize Firestore
#
firebase_admin.initialize_app()
db = firestore.client()
global service_configs
userdb = db.collection("users")

##### FITBIT APP CREDS ######
client_id = '2389RK'
client_secret = '99f3d9cbf54c9d9d807d57f3fd6a6c4b'
redirect_uri = 'https://device-connect.org/token'
app_creds = "Basic " + str(base64.b64encode(bytes(client_id + ':' +
                                                 client_secret, encoding='utf8')))\
    .replace("b", "").replace("'", "")

@app.route("/query")
def query():
    return("Query Printed")



@app.route("/")
def home():
    app_name = request.host_url
    return render_template("login.html", app_name=app_name)


@app.route("/link")
def link():
    app_name = request.host_url
    print(app_name)
    return render_template("home.html")


@app.route("/emailcheck", methods=["GET", "POST"])
def emailcheck():
    data = request.get_json()
    email_ref = userdb.get()
    password = 'password'
    email_list = []
    for doc in email_ref:
        email = doc.get('email')
        email_list.append(email)
    if data['email'] in email_list and data['password'] == password:
        return jsonify('true')
    if data['email'] in email_list and data['password'] != password:
        return jsonify('password')
    if data['email'] not in email_list and data['password'] == password:
        return jsonify('email')
    else:
        return jsonify('false')

@app.route("/accept", methods=['POST'])
def accept():
    data = request.get_json()
    email = data['email']
    sig = data['sig']
    name = data['name']
    date = data['date']
    doc_ref = userdb.document(email)
    doc_ref.set({
        u'name': name,
        u'signature': sig,
        u'date': date,
        u'email': email,
        u'Disclaimer-text': 'Enter Text',
        u'credentials':'patient'

    })
    return jsonify('/link')

# 
# FITBIT AUTHORIZATION AND TOKEN COLLECTION ROUTE
#
@app.route("/token", methods=['GET'])
def redirect():
    code = 'e3b0957ebcb9cd970ed6a533b2a952ff30ee9ec6'
    print("Token Route")
    print(code)
    print(redirect_uri)
    print(app_creds)
    refresh_token = []
    access_token = []
    code = request.args.get('code')
    headers = {
        'Authorization': {app_creds},
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = {
        'clientId': [client_id],
        'grant_type': 'authorization_code',
        'redirect_uri': {redirect_uri},
        'code': {code}
    }
    response = requests.post('https://api.fitbit.com/oauth2/token', headers=headers, data=data)
    print(response)
    response_json = response.json()
    refresh_token = response_json['fitbit_refresh_token']
    access_token = response_json['fitbit_access_token']
    user_id = response_json['fitbit_user_id']

#
# LOAD TOKENS TO FIRESTORE
#
    userdb.set({
        u'access_token': access_token,  
        u'refresh_token': refresh_token,
        u'fitbit_user_id': user_id
    })

#TODO: Add fitbit profile after token pull
    return render_template("token.html")



@app.route("/update_tokens")
def update_tokens():
    try:
        users_ref = userdb.get()
        for doc in users_ref:
            #### REFRESH TOKENS #####
            rtoken = []
            refresh_token = []
            access_token = []
            rtoken = doc.get('refresh_token')
            print(rtoken)
            url = "https://api.fitbit.com/oauth2/token"
            payload = f'grant_type=refresh_token&refresh_token={rtoken}'
            headers = {
            'Authorization': app_creds,
            'Content-Type': 'application/x-www-form-urlencoded',
            }
            response = requests.request("POST", url, headers=headers, data=payload)
            response_json = response.json()
            print(response_json)
            refresh_token = response_json['refresh_token']
            access_token = response_json['access_token']
            user_id = response_json['user_id']
        #### UPLOAD REFRESHED TOKENS TO FIRESTORE #####
            doc_ref = userdb.document(user_id)
            doc_ref.set({
            u'fitbit_access_token': access_token,
            u'fitbit_refresh_token': refresh_token
            })
        return ("Token update successful")
    except KeyError:
        return("A token as failed")

#
# BATCH LOAD FITBIT DATA INTO BIGQUERY
#
# TODO: should we archive user records in GCS bucket folders 
# @app.route("/batch_fitbit_data")
# def batch_fitbit_data():
#     #### GENERAL FUNCTIONS ########
#     def normalize_response(df, column_list):
#         for col in column_list:
#             if col not in df.columns:
#                 df[col] = None
#         df = df.reindex(columns=column_list)
#         df.insert(0, 'id', email)
#         df.insert(1, 'date', date_pulled)
#         df = clean_columns(df)
#         return(df)
    
# #### DAILY USERS' DATA PULL ########
#     pd.set_option( "display.max_columns", 500)
#     #### CREATE AN EMPTY LIST TO HOLD USER DATA AS THE PROCESS ITERATES THROUGH USERS #####
#     # Activty Endpoint
#     activities_list = []
#     activity_summary_list = []
#     activity_goals_list = []

#     # Sleep Endpoint
#     sleep_list = []
#     sleep_summary_list = []
#     sleep_minutes_list = []

#     # Body Weight
#     body_weight_df_list = []

#     # Nutrition
#     nutrition_summary_list = []
#     nutrition_logs_list = []
#     nutrition_goals_list = []

#     # Heart Rate Zones
#     hr_zones_list = []
#     intraday_hr_list = []

#     # Badges
#     badges_list = []

#     # #### ITERATE THROUGH ALL USERS STORED IN FIRESTORE #####
#     users_ref = db.collection(u'users').get()

#     for doc in users_ref:
#         access_token = doc.get('fitbit_access_token')

#         ############### SET THE DATE PULLED #################
#         date_pulled = date.today() - timedelta(days=4)
#         date_pulled = date_pulled.strftime('%Y-%m-%d')

#         ############### SET HEADERS #################
#         api_call_headers = {'Authorization': 'Bearer ' + access_token,
#                         'Accept-Language': 'en_US',
#                         'Content-Type': 'application/x-www-form-urlencoded'}

#         user_url = 'https://api.fitbit.com/1/user/-/profile.json'
#         user_response = requests.get(user_url, headers=api_call_headers).json()
#         user_id = user_response['user']['encodedId']
#         email_ref = db.collection(u'users').where('fitbit_user_id', '==', '9H9SKK')
#         docs = []
#         for doc in email_ref.get():   
#             formattedData = doc.to_dict()
#             email = formattedData['email']

#         ############### CONNECT TO ACTIVITY ENDPOINT #################
#         activity_url = 'https://api.fitbit.com/1/user/-/activities/date/'+date_pulled+'.json'
#         activity_response = requests.get(activity_url, headers=api_call_headers).json()

#         # subset response for activites, summary, and goals
#         activities = activity_response['activities']
#         activity_summary = activity_response['summary']
#         activity_goals = activity_response['goals']

#         # Normalize the response into a dataframe
#         activities_df = pd.json_normalize(activities)
#         activity_summary_df = pd.json_normalize(activity_summary)
#         activity_summary_df = activity_summary_df.drop(['distances', 'heartRateZones'], axis=1)
#         activity_goals_df = pd.json_normalize(activity_goals)

#         # Define all possible columns that could come through the endpoint
#         activites_columns = ['activityId', 'activityParentId', 'activityParentName', 'calories',
#        'description', 'duration', 'hasActiveZoneMinutes', 'hasStartTime',
#        'isFavorite', 'lastModified', 'logId', 'name', 'startDate', 'startTime',
#        'steps']
#         activity_summary_columns = ['activeScore', 'activityCalories', 'caloriesBMR', 'caloriesOut',
#        'elevation', 'fairlyActiveMinutes', 'floors',
#        'lightlyActiveMinutes', 'marginalCalories',
#        'restingHeartRate', 'sedentaryMinutes', 'steps', 'veryActiveMinutes']
#         activity_goals_columns = ['activeMinutes', 'caloriesOut', 'distance', 'floors', 'steps']

#         # Normalize and clean response
#         activities_df = normalize_response(activities_df, activites_columns)
#         activity_summary_df = normalize_response(activity_summary_df, activity_summary_columns)
#         activity_goals_df = normalize_response(activity_goals_df, activity_goals_columns)

#         # Append dfs to df list
#         activities_list.append(activities_df)
#         activity_summary_list.append(activity_summary_df)
#         activity_goals_list.append(activity_goals_df)

#     ############## CONNECT TO SLEEP ENDPOINT #################
#         sleep_url = 'https://api.fitbit.com/1/user/-/sleep/date/' + date_pulled + '.json'
#         sleep_response = requests.get(sleep_url, headers=api_call_headers).json()
#         sleep = sleep_response['sleep']
    
#         try:
#             sleep_minutes = sleep_response['sleep'][0]['minuteData']
#             sleep_minutes_df = pd.json_normalize(sleep_minutes)
#         except Exception as err:
#             print(err)
    
#         sleep_summary = sleep_response['summary']
    
#         sleep_df = pd.json_normalize(sleep)
#         sleep_summary_df = pd.json_normalize(sleep_summary)

    
#         # Drop nested columns
#         try:
#             sleep_df = sleep_df.drop(['minuteData'], axis =1)
#         except Exception as err:
#             print(err)
#             pass
    
#         sleep_columns = ['awakeCount', 'awakeDuration', 'awakeningsCount', 'dateOfSleep',
#            'duration', 'efficiency', 'endTime', 'isMainSleep', 'logId',
#            'minutesAfterWakeup', 'minutesAsleep', 'minutesAwake',
#            'minutesToFallAsleep', 'restlessCount', 'restlessDuration', 'startTime',
#            'timeInBed']
#         sleep_minutes_columns = ['dateTime', 'value']
#         sleep_summary_columns = ['totalMinutesAsleep', 'totalSleepRecords', 'totalTimeInBed',
#            'stages.deep', 'stages.light', 'stages.rem', 'stages.wake']
    
#         # Fill missing columns
#         sleep_df = normalize_response(sleep_df, sleep_columns)
#         sleep_minutes_df = normalize_response(sleep_minutes_df, sleep_minutes_columns)
#         sleep_minutes_df['date_time'] = str(date_pulled) + ' ' + sleep_minutes_df['date_time']
#         sleep_summary_df = normalize_response(sleep_summary_df, sleep_summary_columns)
    
#         # Append dfs to df list
#         sleep_list.append(sleep_df)
#         sleep_summary_list.append(sleep_summary_df)
#         sleep_minutes_list.append(sleep_minutes_df)
    
#     ############## CONNECT TO BODY WEIGHT ENDPOINT #################
#         weight_url = 'https://api.fitbit.com/1/user/-/body/log/weight/date/' + date_pulled + '.json'
#         weight_response = requests.get(weight_url, headers=api_call_headers).json()
#         body_weight = weight_response['weight']
#         body_weight_df = pd.json_normalize(body_weight)
#         try:
#             body_weight_df = body_weight_df.drop(['date', 'time'], axis=1)
#         except Exception as err:
#             pass
#             print(err)
    
#         body_weight_columns = ['bmi', 'fat', 'logId', 'source', 'weight']
#         body_weight_df = normalize_response(body_weight_df, body_weight_columns)
#         body_weight_df_list.append(body_weight_df)



#     ############# CONNECT TO NUTRITION ENDPOINT #################
#         nutrition_url = 'https://api.fitbit.com/1/user/-/foods/log/date/' + date_pulled + '.json'
#         nutrition_response = requests.get(nutrition_url, headers=api_call_headers).json()
    
#         nutrition_summary = nutrition_response['summary']
#         nutrition_logs = nutrition_response['foods']
    
#         nutrition_summary_df = pd.json_normalize(nutrition_summary)
#         nutrition_logs_df = pd.json_normalize(nutrition_logs)
    
#         try:
#             nutrition_logs_df = nutrition_logs_df.drop(['loggedFood.creatorEncodedId', 'loggedFood.unit.id', 'loggedFood.units'], axis=1)
#         except Exception as err:
#             print(err)
    
#         nutrition_summary_columns = ['calories', 'carbs', 'fat', 'fiber', 'protein', 'sodium', 'water']
#         nutrition_logs_columns = ['isFavorite', 'logDate', 'logId', 'loggedFood.accessLevel', 'loggedFood.amount', 'loggedFood.brand', 'loggedFood.calories',
#                           'loggedFood.foodId', 'loggedFood.mealTypeId', 'loggedFood.name', 'loggedFood.unit.name', 'loggedFood.unit.plural',
#                           'nutritionalValues.calories', 'nutritionalValues.carbs', 'nutritionalValues.fat', 'nutritionalValues.fiber', 'nutritionalValues.protein',
#                           'nutritionalValues.sodium', 'loggedFood.locale']
    
#         nutrition_summary_df = normalize_response(nutrition_summary_df, nutrition_summary_columns)
#         nutrition_logs_df = normalize_response(nutrition_logs_df, nutrition_logs_columns)
    
#         nutrition_summary_list.append(nutrition_summary_df)
#         nutrition_logs_list.append(nutrition_logs_df)
     
#         nutrition_goal_url = 'https://api.fitbit.com/1/user/-/foods/log/goal.json'
#         nutrition_goal_response = requests.get(nutrition_goal_url, headers=api_call_headers).json()
#         nutrition_goal = nutrition_goal_response['goals']
#         nutrition_goal_df = pd.json_normalize(nutrition_goal_response)
#         nutrition_goal_columns = ['calories']
#         nutrition_goal_df = normalize_response(nutrition_goal_df, nutrition_goal_columns)
#         nutrition_goals_list.append(nutrition_goal_df)
    
#         ############# CONNECT TO HEARTRATE ZONES ENDPOINT #################

#         hr_zones_url = 'https://api.fitbit.com/1/user/-/activities/heart/date/' + date_pulled + '/1d.json'
#         hr_zones_response = requests.get(hr_zones_url, headers=api_call_headers).json()
#         hr_zones = hr_zones_response['activities-heart'][0]['value']
#         zone_list = ['Out of Range', 'Fat Burn', 'Cardio', 'Peak']
#         hr_zones_columns = ['out_of_range_calories_out' , 'out_of_range_minutes' , 'out_of_range_min_hr' ,'out_of_range_max_hr' , 'fat_burn_calories_out','fat_burn_minutes','fat_burn_min_hr',
#             'fat_burn_max_hr','cardio_calories_out','cardio_minutes','cardio_min_hr','cardio_max_hr','peak_calories_out','peak_minutes','peak_min_hr','peak_max_hr']
#         hr_zones_df = pd.json_normalize(hr_zones)
#         try:
#             user_activity_zone = pd.DataFrame({
#                 hr_zones['heartRateZones'][0]['name'].replace(' ', '_').lower() + '_calories_out': hr_zones['heartRateZones'][0]['caloriesOut'],
#                 hr_zones['heartRateZones'][0]['name'].replace(' ', '_').lower() + '_minutes':hr_zones['heartRateZones'][0]['minutes'],
#                 hr_zones['heartRateZones'][0]['name'].replace(' ', '_').lower() + '_min_hr': hr_zones['heartRateZones'][0]['min'],
#                 hr_zones['heartRateZones'][0]['name'].replace(' ', '_').lower() + '_max_hr': hr_zones['heartRateZones'][0]['max'],
#                 hr_zones['heartRateZones'][1]['name'].replace(' ', '_').lower() + '_calories_out': hr_zones['heartRateZones'][1]['caloriesOut'],
#                 hr_zones['heartRateZones'][1]['name'].replace(' ', '_').lower() + '_minutes': hr_zones['heartRateZones'][1]['minutes'],
#                 hr_zones['heartRateZones'][1]['name'].replace(' ', '_').lower() + '_min_hr': hr_zones['heartRateZones'][1]['min'],
#                 hr_zones['heartRateZones'][1]['name'].replace(' ', '_').lower() + '_max_hr': hr_zones['heartRateZones'][1]['max'],
#                 hr_zones['heartRateZones'][2]['name'].replace(' ', '_').lower() + '_calories_out': hr_zones['heartRateZones'][2]['caloriesOut'],
#                 hr_zones['heartRateZones'][2]['name'].replace(' ', '_').lower() + '_minutes': hr_zones['heartRateZones'][2]['minutes'],
#                 hr_zones['heartRateZones'][2]['name'].replace(' ', '_').lower() + '_min_hr': hr_zones['heartRateZones'][2]['min'],
#                 hr_zones['heartRateZones'][2]['name'].replace(' ', '_').lower() + '_max_hr': hr_zones['heartRateZones'][2]['max'],
#                 hr_zones['heartRateZones'][3]['name'].replace(' ', '_').lower() + '_calories_out': hr_zones['heartRateZones'][3]['caloriesOut'],
#                 hr_zones['heartRateZones'][3]['name'].replace(' ', '_').lower() + '_minutes': hr_zones['heartRateZones'][3]['minutes'],
#                 hr_zones['heartRateZones'][3]['name'].replace(' ', '_').lower() + '_min_hr': hr_zones['heartRateZones'][3]['min'],
#                 hr_zones['heartRateZones'][3]['name'].replace(' ', '_').lower() + '_max_hr': hr_zones['heartRateZones'][3]['max'],
#                 }, index=[0])
#         except Exception as err:
#             print(err)
#             user_activity_zone = pd.DataFrame({'out_of_range_calories_out' : None,
#                                             'out_of_range_minutes': None,
#                                             'out_of_range_min_hr': None,
#                                             'out_of_range_max_hr': None,
#                                             'fat_burn_calories_out': None,
#                                             'fat_burn_minutes': None,
#                                             'fat_burn_min_hr': None,
#                                             'fat_burn_max_hr': None,
#                                             'cardio_calories_out': None,
#                                             'cardio_minutes': None,
#                                             'cardio_min_hr': None,
#                                             'cardio_max_hr': None,
#                                             'peak_calories_out': None,
#                                             'peak_minutes': None,
#                                             'peak_min_hr': None,
#                                             'peak_max_hr': None}, index=[0])
#         user_activity_zone.insert(1, 'id', email)
#         user_activity_zone.insert(1, 'date', date_pulled)
#         hr_zones_list.append(user_activity_zone)


#         # hr_url = 'https://api.fitbit.com/1/user/-/activities/heart/date/' + date_pulled + '/1d.json'
#         # hr_response = requests.get(hr_url, headers=api_call_headers).json()
#         # print(hr_response)
    
#         # hr_intraday = hr_zones_response['activities-heart-intraday']['dataset']
#         # hr_intraday_columns = ['time', 'value']
#         # hr_intraday_df = pd.json_normalize(hr_intraday)
#         # hr_intraday_df = normalize_response(hr_intraday_df, hr_intraday_columns)
#         # intraday_hr_list.append(hr_intraday_df)

    
#     ############## CONNECT TO BADGES ENDPOINT #################
#         badges_url = 'https://api.fitbit.com/1/user/-/badges.json'
#         badges_response = requests.get(badges_url, headers=api_call_headers).json()
#         badges = badges_response['badges']
#         badges_df = pd.json_normalize(badges)
#         badges_columns = ['badgeGradientEndColor', 'badgeGradientStartColor', 'badgeType', 'category', 'cheers', 'dateTime', 'description',
#                           'earnedMessage', 'encodedId', 'image100px', 'image125px', 'image300px', 'image50px', 'image75px', 'marketingDescription',
#                           'mobileDescription', 'name', 'shareImage640px', 'shareText', 'shortDescription', 'shortName', 'timesAchieved', 'value',
#                           'unit']
#         badges_df = normalize_response(badges_df, badges_columns)
#         badges_list.append(badges_df)


#     #### CONCAT DATAFRAMES INTO BULK DF ####
#     bulk_activities_df = pd.concat(activities_list, axis=0)
#     bulk_activity_summary_df = pd.concat(activity_summary_list, axis=0)
#     bulk_activity_goals_df = pd.concat(activity_goals_list, axis=0)
#     bulk_sleep_df = pd.concat(sleep_list, axis=0)
#     bulk_sleep_minutes_df = pd.concat(sleep_summary_list, axis=0)
#     bulk_sleep_summary_df = pd.concat(sleep_minutes_list, axis=0)
#     bulk_body_weight_df = pd.concat(body_weight_df_list, axis=0)
#     bulk_nutrition_summary_df = pd.concat(nutrition_summary_list, axis=0)
#     bulk_nutrition_logs_df = pd.concat(nutrition_logs_list, axis=0)
#     bulk_nutrition_goal_df = pd.concat(nutrition_goals_list, axis=0)
#     bulk_hr_zones_df = pd.concat(hr_zones_list, axis=0)
#     #bulk_hr_intraday_df = pd.concat(intraday_hr_list, axis=0)
#     bulk_badges_df = pd.concat(badges_list, axis=0)


    
# ####### LOAD DATA INTO BIGQUERY #########
#     project_id = "starterkit-344119"
    ##### ACTIVITY DATAFRAMES #######
    # TODO: Is distance missing?
    # pandas_gbq.to_gbq(dataframe=bulk_activities_df, destination_table='fitbit.activity_logs',
    #                   project_id=project_id, if_exists='append',
    #                   table_schema=[{'name': 'id', 'type': 'STRING', 'description':'Primary Key'},
    #                                 {'name': 'date', 'type': 'DATE', 'description':'The date values were extracted'},
    #                                 {'name': 'activity_id', 'type': 'INTEGER', 'description':'The ID of the activity.'},
    #                                 {'name': 'activity_parent_id', 'type': 'INTEGER', 'description':'The ID of the top level ("parent") activity.'},
    #                                 {'name': 'activity_parent_name', 'type': 'STRING', 'description':'The name of the top level ("parent") activity.'},
    #                                 {'name': 'calories', 'type': 'INTEGER', 'description':'Number of calories burned during the exercise.'},
    #                                 {'name': 'description', 'type': 'STRING', 'description':'The description of the recorded exercise.'},
    #                                 {'name': 'duration', 'type': 'INTEGER', 'description':'The activeDuration (milliseconds) + any pauses that occurred during the activity recording.'},
    #                                 {'name': 'has_active_zone_minutes', 'type': 'BOOLEAN', 'description':'True | False' },
    #                                 {'name': 'has_start_time', 'type': 'BOOLEAN', 'description':'True | False'},
    #                                 {'name': 'is_favorite', 'type': 'BOOLEAN', 'description':'True | False'},
    #                                 {'name': 'last_modified', 'type': 'TIMESTAMP', 'description':'Timestamp the exercise was last modified.'},
    #                                 {'name': 'log_id', 'type': 'INTEGER', 'description':'The activity log identifier for the exercise.'},
    #                                 {'name': 'name', 'type': 'STRING', 'description':'Name of the recorded exercise.'},
    #                                 {'name': 'start_date', 'type': 'DATE', 'description':'The start date of the recorded exercise.'},
    #                                 {'name': 'start_time', 'type': 'STRING', 'description':'The start time of the recorded exercise.'},
    #                                 {'name': 'steps', 'type': 'INTEGER', 'description':'User defined goal for daily step count.'}]
    #                   )


    # pandas_gbq.to_gbq(dataframe=bulk_activity_summary_df, destination_table='fitbit.activity_summary',
    #                   project_id=project_id, if_exists='append',
    #                   table_schema=[{'name': 'id', 'type': 'STRING', 'mode':'REQUIRED', 'description':'Primary Key'},
    #                                 {'name': 'date', 'type': 'DATE', 'mode':'REQUIRED', 'description':'The date values were extracted'},
    #                                 {'name': 'activity_score', 'type': 'INTEGER', 'description':'No Description'},
    #                                 {'name': 'activity_calories', 'type': 'INTEGER', 'description':'The number of calories burned for the day during periods the user was active above sedentary level. This includes both activity burned calories and BMR.'},
    #                                 {'name': 'calories_bmr', 'type': 'INTEGER', 'description':'Total BMR calories burned for the day.'},
    #                                 {'name': 'calories_out', 'type': 'INTEGER', 'description':'Total calories burned for the day (daily timeseries total).'},
    #                                 {'name': 'elevation', 'type': 'INTEGER', 'description':'The elevation traveled for the day.'},
    #                                 {'name': 'fairly_active_minutes', 'type': 'INTEGER', 'description': 'Total minutes the user was fairly/moderately active.'},
    #                                 {'name': 'floors', 'type': 'INTEGER', 'description':'The equivalent floors climbed for the day.'},
    #                                 {'name': 'lightly_active_minutes', 'type': 'INTEGER', 'description':'	Total minutes the user was lightly active.'},
    #                                 {'name': 'marginal_calories', 'type': 'INTEGER', 'description': 'Total marginal estimated calories burned for the day.'},
    #                                 {'name': 'resting_heart_rate', 'type': 'INTEGER', 'description':'The resting heart rate for the day'},
    #                                 {'name': 'sedentary_minutes', 'type': 'INTEGER', 'description':'Total minutes the user was sedentary.'},
    #                                 {'name': 'very_active_minutes', 'type': 'INTEGER', 'description': 'Total minutes the user was very active.'}, 
    #                                 {'name': 'steps', 'type': 'INTEGER', 'description':'Total steps taken for the day.'}]
    #                   )

    #TODO: Fix pandas_gbq.exceptions.ConversionError: Could not convert DataFrame to Parquet.
    # pandas_gbq.to_gbq(dataframe=bulk_activity_goals_df, destination_table='fitbit.activity_goals',
    #                   project_id=project_id, if_exists='append',
    #                   table_schema=[{'name': 'id', 'type': 'STRING', 'mode':'REQUIRED', 'description':'Primary Key'},
    #                                 {'name': 'date', 'type': 'DATE', 'mode':'REQUIRED', 'description':'The date values were extracted'},
    #                                 {'name': 'active_minutes', 'type': 'INTEGER', 'description':'User defined goal for daily active minutes.'},
    #                                 {'name': 'calories_out', 'type': 'INTEGER', 'description':'User defined goal for daily calories burned.'},
    #                                 {'name': 'distance', 'type': 'INTEGER', 'description':'User defined goal for daily distance traveled.'},
    #                                 {'name': 'floors', 'type': 'FLOAT', 'description':'User defined goal for daily floor count.'},
    #                                 {'name': 'steps', 'type': 'INTEGER', 'description':'User defined goal for daily step count.'}]
    #                   )

    # TODO: Fix FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/pk/f434v_hx28v2_r0fl_gbrbvw0000gn/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/jacksonwittenberg/Desktop/device-connect']
    # pandas_gbq.to_gbq(dataframe=bulk_sleep_df, destination_table='fitbit.sleep',
    #                   project_id=project_id, if_exists='append',
    #                   table_schema=[{'name': 'id', 'type': 'STRING', 'mode':'REQUIRED', 'description':'Primary Key'},
    #                                 {'name': 'date', 'type': 'DATE', 'mode':'REQUIRED', 'description':'The date values were extracted'},
    #                                 {'name': 'awake_count', 'type': 'INTEGER', 'description':'Number of times woken up'},
    #                                 {'name': 'awake_duration', 'type':'INTEGER', 'description':'Amount of time the user was awake'},
    #                                 {'name': 'awakenings_count', 'type':'INTEGER', 'description':'Number of times woken up'},
    #                                 {'name': 'date_of_sleep', 'type': 'DATE', 'description':'The date the user fell asleep'},
    #                                 {'name': 'duration', 'type': 'INTEGER', 'description':'Length of the sleep in milliseconds.'},
    #                                 {'name': 'efficiency', 'type': 'INTEGER', 'description':'Calculated sleep efficiency score. This is not the sleep score available in the mobile application.'},
    #                                 {'name': 'end_time', 'type':'TIMESTAMP', 'description':'Time the sleep log ended.'},
    #                                 {'name': 'main_sleep', 'type': 'BOOLEAN', 'decription':'True | False'},
    #                                 {'name': 'log_id', 'type': 'INTEGER', 'description':'Sleep log ID.'},
    #                                 {'name': 'minutes_after_wakeup', 'type': 'INTEGER', 'description':'The total number of minutes after the user woke up.'},
    #                                 {'name': 'minutes_asleep', 'type': 'INTEGER', 'description':'The total number of minutes the user was asleep.'},
    #                                 {'name': 'minutes_awake', 'type': 'INTEGER', 'description':'The total number of minutes the user was awake.'},
    #                                 {'name': 'minutes_to_fall_asleep', 'type': 'FLOAT', 'decription':'The total number of minutes before the user falls asleep. This value is generally 0 for autosleep created sleep logs.'},
    #                                 {'name': 'restless_count', 'type': 'INTEGER', 'decription':'The total number of times the user was restless'},
    #                                 {'name': 'restless_duration', 'type': 'INTEGER', 'decription':'The total amount of time the user was restless'},
    #                                 {'name': 'start_time', 'type':'TIMESTAMP', 'description':'Time the sleep log begins.'},
    #                                 {'name': 'time_in_bed', 'type': 'INTEGER', 'description':'Total number of minutes the user was in bed.'}]
    #                   )

    # pandas_gbq.to_gbq(dataframe=bulk_sleep_df, destination_table='fitbit.sleep_minutes',
    #                   project_id=project_id, if_exists='append',
    #                   table_schema=[{'name': 'id', 'type': 'STRING', 'mode':'REQUIRED', 'description':'Primary Key'},
    #                                 {'name': 'date', 'type': 'DATE', 'mode':'REQUIRED', 'description':'The date values were extracted'},
    #                                 {'name': 'total_minutes_asleep', 'type': 'INTEGER', 'description':'Total number of minutes the user was asleep across all sleep records in the sleep log.'},
    #                                 {'name': 'total_sleep_records', 'type':'INTEGER', 'description':'The number of sleep records within the sleep log.'},
    #                                 {'name': 'total_time_in_bed', 'type':'INTEGER', 'description':'Total number of minutes the user was in bed across all records in the sleep log.'},
    #                                 {'name': 'stages_deep', 'type': 'DATE', 'description':'Total time of deep sleep'},
    #                                 {'name': 'stages_light', 'type': 'INTEGER', 'description':'Total time of light sleep'},
    #                                 {'name': 'stages_rem', 'type': 'INTEGER', 'description':'Total time of REM sleep'},
    #                                 {'name': 'stages_wake', 'type':'TIMESTAMP', 'description':'Total time awake'}]
    #                   )

    # print(bulk_sleep_minutes_df)
    # print(bulk_sleep_minutes_df.columns)



    return("Fitbit Data Pulled")
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=config.PORT, debug=config.DEBUG_MODE)
