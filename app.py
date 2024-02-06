from flask import Flask, render_template, request, redirect, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import sqlite3
import datetime

global number
number = 0

global oldname
oldname = ""

connection = sqlite3.connect("user_data.db", check_same_thread=False)
db = connection.cursor()
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def home(): 
    if db.execute("SELECT username FROM users WHERE userid=?",(session.get("user_id"),)).fetchone():
        username = db.execute("SELECT username FROM users WHERE userid=?",(session.get("user_id"),)).fetchone()[0]
        return render_template("index.html",name=username)
    else:
        return render_template("layout.html")

@app.route("/progress", methods=['GET', 'POST'])
@login_required

def progress(): 
    squat_data = []
    bench_data = []
    deadlift_data = []

    username = db.execute("SELECT username FROM users WHERE userid=?",(session.get("user_id"),)).fetchone()[0]

    x = db.execute(f"SELECT * FROM '{username+'_sbd'}' WHERE movement='Squat'").fetchall()
    for i in x:
        squat_data.append((i[2],i[1]))

    x = db.execute(f"SELECT * FROM '{username+'_sbd'}' WHERE movement='Bench'").fetchall()
    for i in x:
        bench_data.append((i[2],i[1]))

    x = db.execute(f"SELECT * FROM '{username+'_sbd'}' WHERE movement='Deadlift'").fetchall()
    for i in x:
        deadlift_data.append((i[2],i[1]))

    squat_labels = [row[0] for row in squat_data]
    squat_values = [row[1] for row in squat_data]
    bench_labels = [row[0] for row in bench_data]
    bench_values = [row[1] for row in bench_data]
    deadlift_labels = [row[0] for row in deadlift_data]
    deadlift_values = [row[1] for row in deadlift_data]

    return render_template("progress.html", squat_labels=squat_labels, squat_values=squat_values,
                                            bench_labels=bench_labels, bench_values=bench_values,
                                            deadlift_labels=deadlift_labels, deadlift_values=deadlift_values)
    
@app.route("/view_workouts", methods=['GET', 'POST'])
@login_required

def view_workouts(): 
    username = db.execute("SELECT username FROM users WHERE userid=?",(session.get("user_id"),)).fetchone()[0]
    editmode = False
    global oldname
    if request.method == "POST":
        if request.form.get("Delete"):
            deletename = username+"."+request.form.get("Delete")[6:]
            db.execute(f"DROP TABLE '{deletename}';")
            connection.commit()

        if request.form.get("Edit"):
            oldname = username+"."+request.form.get("Edit")[4:]
            edit = db.execute(f"SELECT * FROM '{oldname}'").fetchall()
            edit.insert(0, request.form.get("Edit")[4:])
            return render_template("edit_workout.html", exercises=[edit])

        if request.form.get("Save"):
            username = db.execute("SELECT username FROM users WHERE userid=?",(session.get("user_id"),)).fetchone()[0]
            newname = username+"."+request.form.get("named")

            db.execute(f"DROP TABLE '{oldname}';")
            db.execute(f"""CREATE TABLE IF NOT EXISTS '{newname}'(
                exercise TEXT,
                sets TEXT,
                reps TEXT,
                wt TEXT
                )
            """)

            count = 1
            while request.form.get(str(count+3)):
                print(count)
                db.execute(f""" INSERT INTO '{newname}' (exercise, sets, reps, wt) VALUES (
                    '{request.form.get(str(count))}',
                    '{request.form.get(str(count+1))}',
                    '{request.form.get(str(count+2))}',
                    '{request.form.get(str(count+3))}'
                )
                """)
                count += 4
            connection.commit()
            
    if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ? ;", (username+"."+"%",),).fetchone():
        full = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ? ;", (username+"."+"%",),).fetchall()
        exercises = []
        for i in full:
            x = db.execute(f"SELECT * FROM '{i[0]}' ;").fetchall()
            x.insert(0,i[0][len(username)+1:])
            exercises.append(x)
        return render_template("view_workouts.html", exercises=exercises)
    return render_template("view_workouts.html")

@app.route("/create_workouts", methods=['GET', 'POST'])
@login_required

def create_workouts():  
    if request.method == "POST":
        global number

        if request.form.get("AddEx")=="AddEx":
            number += 1
        elif request.form.get("RemoveEx")=="RemoveEx":
            if number > 0:
                number -= 1

        if request.form.get("Complete")=="Complete":
            username = db.execute("SELECT username FROM users WHERE userid=?",(session.get("user_id"),)).fetchone()[0]
            name = username+"."+request.form.get("name")

            if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?; ", (name,),).fetchone():
                return render_template("create_workouts.html",number=number, error="Workout already exists!")
            else:
                db.execute(f"""CREATE TABLE IF NOT EXISTS '{name}'(
                    exercise TEXT,
                    sets TEXT,
                    reps TEXT,
                    wt TEXT
                    )
                """)

            for i in range(number):
                db.execute(f""" INSERT INTO '{name}' (exercise, sets, reps, wt) VALUES (
                    '{request.form.get(f"Ex{i}")}',
                    '{request.form.get(f"Set{i}")}',
                    '{request.form.get(f"Rep{i}")}',
                    '{request.form.get(f"Weight{i}")}'
                )
                """)
            number = 0
            connection.commit()
            return render_template("create_workouts.html",number=number, success=True)
        return render_template("create_workouts.html",number=number)
    else:
        number = 0
        return render_template("create_workouts.html",number=number)

@app.route("/sbd", methods=['GET', 'POST'])
@login_required
def sbd():
    if request.method == "POST":
        squat = db.execute("SELECT squat FROM users WHERE userid = ?", (session.get("user_id"),)).fetchone()
        bench = db.execute("SELECT bench FROM users WHERE userid = ?", (session.get("user_id"),)).fetchone()
        deadlift = db.execute("SELECT deadlift FROM users WHERE userid = ?", (session.get("user_id"),)).fetchone()

        if int(request.form.get("Squat")) <= 0:
            return render_template("sbd.html", error="Please make sure all values are above 0!",
            squat=squat[0], bench=bench[0], deadlift=deadlift[0])
        if int(request.form.get("Bench")) <= 0:
            return render_template("sbd.html", error="Please make sure all values are above 0!",
            squat=squat[0], bench=bench[0], deadlift=deadlift[0])
        if int(request.form.get("Deadlift")) <= 0:
            return render_template("sbd.html", error="Please make sure all values are above 0!",
            squat=squat[0], bench=bench[0], deadlift=deadlift[0])

        db.execute("UPDATE users SET squat = ?, bench = ?, deadlift = ? WHERE userid = ?",
        (request.form.get("Squat"),
        request.form.get("Bench"),
        request.form.get("Deadlift"),
        session.get("user_id"))
        )

        username = db.execute("SELECT username FROM users WHERE userid=?",(session.get("user_id"),)).fetchone()[0]

        db.execute(f"INSERT INTO '{username+'_sbd'}' (movement, weight, date) VALUES (?,?,?)",
            ("Squat",
            str(request.form.get("Squat")),
            str(datetime.datetime.now()))
        )

        db.execute(f"INSERT INTO '{username+'_sbd'}' (movement, weight, date) VALUES (?,?,?)",
            ("Bench",
            str(request.form.get("Bench")),
            str(datetime.datetime.now()))
        )

        db.execute(f"INSERT INTO '{username+'_sbd'}' (movement, weight, date) VALUES (?,?,?)",
            ("Deadlift",
            str(request.form.get("Deadlift")),
            str(datetime.datetime.now()))
        )
        
        connection.commit()
        return render_template("sbd.html", success=True, squat=squat[0], bench=bench[0], deadlift=deadlift[0])
    else:
        name = db.execute("SELECT username FROM users WHERE userid = ?", (session.get("user_id"),)).fetchone()[0]
        squat = db.execute("SELECT squat FROM users WHERE userid = ?", (session.get("user_id"),)).fetchone()
        bench = db.execute("SELECT bench FROM users WHERE userid = ?", (session.get("user_id"),)).fetchone()
        deadlift = db.execute("SELECT deadlift FROM users WHERE userid = ?", (session.get("user_id"),)).fetchone()

        return render_template("sbd.html",squat=squat[0], bench=bench[0], deadlift=deadlift[0])

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/login", methods=['GET', 'POST'])
def login():
    """Log user in"""
    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            return render_template('login.html', error="Please Provide Username")

        elif not request.form.get("password"):
            return render_template('login.html', error="Please Provide Password")

        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", (request.form.get("username"),),
        )
        row = rows.fetchone()
        if not row:
            return render_template('login.html', error="invalid username and/or password")
        if not check_password_hash(row[2], request.form.get("password")):
            return render_template('login.html', error="invalid username and/or password")

        session["user_id"] = row[0]

        return redirect("/")
    else:
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    # Register user


    if request.method == "POST":
        if not request.form.get("username"):
            return render_template('register.html', error="Please Provide Username")

        elif not request.form.get("password"):
            return render_template('register.html', error="Please Provide Password")

        elif not request.form.get("confirmation"):
            return render_template('register.html', error="Please Provide Password Confirmation")
        rows = db.execute(
            "SELECT * FROM users WHERE username=(?)", 
            (request.form.get("username"),)
        )
        row = rows.fetchone()
        if row:
            return render_template('register.html', error="Username already exists")

        if request.form.get("password") != request.form.get("confirmation"):
            return render_template('register.html', error="Passwords Don't Match")

        password = request.form.get("password")
        
        rows = db.execute(
            "INSERT INTO users (userid, username, hash, squat, bench, deadlift) VALUES (?,?,?,0,0,0)",
            (session.get("user_id"),
            str(request.form.get("username")),
            str(generate_password_hash(password, method="sha256", salt_length=16)))
        )

        name = request.form.get("username")
        db.execute(f"""CREATE TABLE IF NOT EXISTS '{name+"_"+"sbd"}'(
                movement TEXT,
                weight TEXT,
                date TEXT
                )
            """)
        
        connection.commit()

        return redirect("/")

    else:
        return render_template("register.html")

if __name__=="__main__":
    app.run(debug=True)
