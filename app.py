from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from openai import OpenAI
import json
import os


with open("keys.json", "r") as keys:
    keys = json.load(keys)

app = Flask(__name__)
app.static_folder = "static"

# Database
CONNECTION_STRING = keys['mongodb']
client = MongoClient(CONNECTION_STRING)
db = client['cupertino']
data = db['user_data']

app.config['SECRET_KEY'] = os.urandom(24)

# AI
api_key = keys['openai']
print(api_key)
client = OpenAI(api_key=api_key)

@app.route('/')
def home():
    name = session.get('name')
    return render_template("index.html", name=name)

@app.route('/login')
def login():
    name = session.get('name')
    return render_template("login.html", name=name)

@app.route('/login', methods=['POST'])
def login_submit():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        print(email, password)
        print('test')
        
        exists = data.find_one({"email": email, "password": password})
        
        if exists:
            session['name'] = exists["name"]
            return redirect(url_for('home'))
        else:
            return redirect(url_for('login', msg="Either incorrect password or username!"))

@app.route('/signup')
def signup():
    name = session.get('name')
    return render_template("signup.html", name=name)

@app.route('/signup', methods=['POST'])
def signup_submit():
    if request.method == 'POST':
        email = request.form['email']
        _name  = request.form['username']
        passw = request.form['password']
        
        details = f"Name: {_name}"
        session['name'] = _name  # Store name in session
        session['q_num'] = 1  # Set initial value for q_num
        session['basic_data'] = details  # Convert ObjectId to string before storing in session
        # print("Basic Data Stored:", session['basic_data'])  # Print basic data stored in session
        session['email'] = email
        session['password'] = passw
        session.modified = True
        return redirect(url_for('setup', name=_name, q_num=1, basic_data = details))  # Pass q_num to setup route
    
    return redirect(url_for('signup'))

    

@app.route('/settings')
def settings():
    name = session.get('name')
    return render_template("settings.html", name=name, data=data.find_one({"name": name})["else"])

@app.route('/settings', methods=['POST'])
def settings_submit():
    session.clear()
    return redirect(url_for('login'))

@app.route('/setup')
def setup():
    name = session.get('name')
    q_num = session.get('q_num')
    basic_data = session.get('basic_data')
    return render_template("setup.html", name=name, q_num=q_num, basic_data=basic_data)

@app.route('/setup', methods=['POST'])
def setup_submit():
    if request.method == 'POST':    
        name = session.get('name')
        q_num = session.get('q_num')  # Get the current value of q_num
        
        basic_data = session.get('basic_data')
        print(basic_data)
        
        # Process form data based on the current q_num
        if q_num == 1:
            duration = request.form['duration']
            check = {1: "15 minutes", 2: "30 minutes", 3: "45 minutes", 4: "1 hour", 5: "1 hour 15 minutes", 6: "1 hour 30 minutes", 7: "1 hour 45 minutes", 8: "2 hours"}
            session["basic_data"] = f"{basic_data}\nAverage Duration of Workouts: {check[int(duration)]}"
        elif q_num == 2:
            types = request.form['type']
            session["basic_data"] = f"{basic_data}\nThe type of Disability: {types}"
        else:
            works = request.form['workout']
            session["basic_data"] = f"{basic_data}\nWhat type of workout the user wants to do: {works}"
            data.insert_one({"name": name, "email": session["email"], "password": session["password"], "else": session["basic_data"]})
            return redirect(url_for("settings", name=name, msg="The setup is complete!", data=session.get('basic_data')))
        
        # Increment q_num for the next question
        session['q_num'] = q_num + 1
        
        return redirect(url_for("setup", name=name, q_num=q_num+1, basic_data=basic_data))  # Pass the updated q_num
    
    return redirect(url_for("setup"))


@app.route("/exercise")
def exercise():
    if not "messages" in session:
        session["messages"] = [{"sender": "ai", "message": "Hello! I am your AI bot to help you with fitness. I can make you exercises based on your disabilities."}]
    
    return render_template("exercise.html", messages=session["messages"], name=session.get("name"))


@app.route("/exercise", methods=["POST"])
def exercise_submit():
    if request.method == 'POST':
        if 'submit' in request.form:
            user_message = request.form["message"]
            session["messages"].append({"sender": "human", "message": user_message})
            
            no_messages_intro = f"You are a fitness tutor and your job is to make a fitness workout that lasts a given amount of time. The person you are giving a workout to has a disability, so make sure to cater your exercises to their injuries. To give more information on this person, here are some details: {session.get('basic_data')}."
            prev_messages = ""
            for i in range(1, len(session["messages"])):
                prev_messages += f"Message {i+1} from {session["messages"][i]["sender"]}: {session["messages"][i]['message']}"
            
            messages_intro = f"You are a fitness tutor and your job is to make a fitness workout that lasts a given amount of time. The person you are giving a workout to has a disability, so make sure to cater your exercises to their injuries. To give more information on this person, here are some details: {session.get('basic_data')}. To give more contenxt on what is happening here is your chat history:\n{prev_messages}"
            intro = no_messages_intro if len(session["messages"]) == 1 else messages_intro
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": intro},
                    {"role": "user", "content": f"{user_message}"}
                ]
            )
            
            ai_response = response.choices[0].message.content
            print(ai_response)
            session["messages"].append({"sender": "ai", "message": ai_response})
            session.modified = True
        elif 'nutrition' in request.form:
            if not session.get("messages"):
                return redirect(url_for("exercise", messages=session["messages"], name=session.get("name"), msg="Please make a workout plan to find a nutrition plan!"))
            else:
                session["nutri"] = session["messages"][-1]["message"]
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a nutritionist, and the user is giong to ask you to make a meal plan after giving you their workout."},
                        {"role": "user", "content": f"Using this workout:\n{session["messages"][-1]["message"]}\nMake me a nutritional plan:"}
                    ]
                )
                return redirect(url_for("nutrition", hum_msg=f"Using this workout:\n{session["messages"][-1]["message"]}\nMake me a nutritional plan:", ai_msg=response.choices[0].message.content, name=session.get("name")))
                
    return render_template("exercise.html", messages=session["messages"], name=session.get("name"))

@app.route("/nutrition")
def nutrition():
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a nutritionist, and the user is giong to ask you to make a meal plan after giving you their workout."},
            {"role": "user", "content": f"Using this workout:\n{session["messages"][-1]["message"]}\nMake me a nutritional plan:"}
        ]
    )
    return render_template("nutrition.html", hum_msg=f"Using this workout:\n{session["messages"][-1]["message"]}\nMake me a nutritional plan:", ai_msg=response.choices[0].message.content, name=session.get("name"))