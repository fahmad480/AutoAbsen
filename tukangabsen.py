from flask import Flask, render_template, request, make_response, url_for, redirect, session
from flask_mysqldb import MySQL

from bs4 import BeautifulSoup
import requests
from lxml import html
from cryptography.fernet import Fernet

app = Flask(__name__)
app.secret_key = 'APDN49CM8B4HF902067DN19364BF'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'autoabsen'

mysql = MySQL(app)

fernet_key = b'yY5oeWM_vgbfnRXHN2y2V6soFh9ciUSwMWUTumgktzM='
fernet = Fernet(fernet_key)


def headerMaker(referer):
    headers = {
        "referer": referer,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36"
    }
    return headers


def login_elearning(USERNAME, PASSWORD, CAMPUS):
    session_requests = requests.session()
    # ---------------------------------------[ GET LOGIN TOKEN FROM LOGIN PAGE ]--------------------------------------- #
    loopRes = True
    countLoopRes = 0

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT * FROM campus WHERE id=%s", (CAMPUS, ))
    res = cur.fetchone()
    LOGIN_URL = res[3]
    cur.close()

    while loopRes is True:
        try:
            result = session_requests.get(LOGIN_URL)
            tree = html.fromstring(result.text)
            authenticity_token = list(
                set(tree.xpath("//input[@name='logintoken']/@value")))[0]
            loopRes = False
        except:
            countLoopRes += 1
            if countLoopRes >= 10:
                break
            pass
    if countLoopRes >= 10:
        return False
    # ---------------------------------------[ CREATE LOGIN PAYLOAD ]--------------------------------------- #
    payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "logintoken": authenticity_token
    }
    # ---------------------------------------[ LOGIN ACTION ]--------------------------------------- #
    loopRes = True
    countLoopRes = 0
    while loopRes is True:
        try:
            result = session_requests.post(
                LOGIN_URL, data=payload, headers=headerMaker(LOGIN_URL))
            loopRes = False
        except:
            countLoopRes += 1
            if countLoopRes >= 10:
                break
            pass
    if countLoopRes >= 10:
        return False

    # ---------------------------------------[ CHECK IF LOGIN SUCCESS OR NOT ]--------------------------------------- #
    if result.url == LOGIN_URL:
        return False
    else:
        return session_requests


def get_elearning_data(session_requests, campus_id):
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT * FROM campus WHERE id=%s", (campus_id,))
    rv = cur.fetchone()
    cur.close()

    profilephp = session_requests.get(rv[2]+'/user/profile.php',
                                      headers=headerMaker(rv[2]), allow_redirects=True)
    soup = BeautifulSoup(profilephp.content, 'html.parser')
    name = soup.find('h1').text
    images = soup.find_all("img", class_="userpicture")
    profile_picture = None
    for image in images:
        profile_picture = image['src']
    return name, profile_picture


def getCountData():
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT (SELECT COUNT(username) FROM account) as account, (SELECT COUNT(url) FROM class) as courses FROM dual")
    rv = cur.fetchone()
    cur.close()
    return rv


def getAllColleger():
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT a.username, a.dhooks, b.name AS campus_name FROM account AS a INNER JOIN campus AS b ON b.id = a.campus_id")
    rv = cur.fetchall()
    cur.close()
    return rv


def getAllCampus():
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT id, name, home_url FROM campus")
    rv = cur.fetchall()
    cur.close()
    return rv


def getSchedule(username):
    output = []
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT * FROM account_class WHERE username_account=%s", (username, ))
    result = cur.fetchall()
    for row in result:
        cur.execute(
            "SELECT * FROM class WHERE id=%s", (row[2], ))
        result2 = cur.fetchall()
        for roww in result2:
            output.append([roww[0], roww[1], roww[2],
                           roww[3], roww[4], roww[6], row[0], roww[5]])
    cur.close()
    return output


def get_creator_of_schedule(id):
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT * FROM account_class WHERE id=%s", (id, ))
    result = cur.fetchone()
    id_class = result[2]
    cur.execute(
        "SELECT * FROM class WHERE id=%s", (id_class, ))
    result = cur.fetchone()
    cur.close()
    return result


@app.route('/', methods=['GET', 'POST'])
def show_login():
    if request.method == 'POST':
        # nice execution
        if not request.form['username']:
            rv = getCountData()
            return render_template('login.html', colleger=rv[0], courses=rv[1], campuseslist=getAllCampus())
        elif not request.form['password']:
            rv = getCountData()
            return render_template('login.html', colleger=rv[0], courses=rv[1], campuseslist=getAllCampus())
        elif request.form['campuses'] == "-":
            rv = getCountData()
            return render_template('login.html', colleger=rv[0], courses=rv[1], campuseslist=getAllCampus())
        else:
            session_req = login_elearning(
                request.form['username'], request.form['password'], request.form['campuses'])
            if session_req != False:
                name, profile_picture = get_elearning_data(
                    session_req, request.form['campuses'])
                session['username'] = request.form['username']
                session['name'] = name
                session['profile_picture'] = profile_picture
                session['campus'] = request.form['campuses']
                try:
                    enc_pass = fernet.encrypt(
                        request.form['password'].encode()).decode()
                    cur = mysql.connection.cursor()
                    cur.execute("INSERT INTO account(username, password, campus_id) VALUES (%s, %s, %s)",
                                (request.form['username'], enc_pass, request.form['campuses']))
                    mysql.connection.commit()
                    cur.close()
                except:
                    pass
                return redirect(url_for('show_dashboard'))
            else:
                rv = getCountData()
                return render_template('login.html', danger='Wrong username/password, or maybe you are not registered to your elearning campus', colleger=rv[0], courses=rv[1], campuseslist=getAllCampus())
    else:
        if 'username' in session:
            return redirect(url_for('show_dashboard'))
        rv = getCountData()
        return render_template('login.html', colleger=rv[0], courses=rv[1], campuseslist=getAllCampus())


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('name', None)
    session.pop('profile_picture', None)
    session.pop('campus', None)
    return redirect(url_for('show_login'))


@app.route('/dashboard')
def show_dashboard():
    if 'username' in session:
        rv = getCountData()
        return render_template('index.html', colleger=rv[0], courses=rv[1])
    elif 'username' not in session:
        return redirect(url_for('show_login'))


@app.route('/profile')
def show_profile():
    if 'username' in session:
        rv = getCountData()
        return render_template('profile.html', colleger=rv[0], courses=rv[1])
    elif 'username' not in session:
        return redirect(url_for('show_login'))


@app.route('/discordhook', methods=['GET', 'POST'])
def show_discordhook():
    if 'username' in session:
        if request.method == 'POST':
            url = request.form['url']
            cur = mysql.connection.cursor()
            cur.execute("UPDATE account SET dhooks=%s WHERE username=%s",
                        (url,  session['username']))
            mysql.connection.commit()
            cur.close()
            rv = getCountData()
            return render_template('discordhook.html', colleger=rv[0], courses=rv[1], success='Discord Webhook URL has been updated', dhooks=url)
        else:
            cur = mysql.connection.cursor()
            cur.execute(
                "SELECT * FROM account WHERE username=%s", (session['username'], ))
            result = cur.fetchone()
            rv = getCountData()
            return render_template('discordhook.html', colleger=rv[0], courses=rv[1], dhooks=result[4])
    elif 'username' not in session:
        return redirect(url_for('show_login'))


@app.route('/accountlist')
def show_accountlist():
    if 'username' in session:
        if session['username'] == 'faraazap':
            rv = getCountData()
            colleger = getAllColleger()
            return render_template('accountlist.html', colleger=rv[0], courses=rv[1], collegerlist=colleger)
        else:
            return redirect(url_for('show_dashboard'))
    elif 'username' not in session:
        return redirect(url_for('show_login'))


@app.route('/schedule')
def show_schedule():
    if 'username' in session:
        rv = getCountData()
        schedule = getSchedule(session['username'])
        return render_template('schedule.html', colleger=rv[0], courses=rv[1], schedule=schedule)
    elif 'username' not in session:
        return redirect(url_for('show_login'))


@app.route('/removeaccount')
def removeaccount():
    if 'username' in session:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM account WHERE username=%s" %
                    session['username'])
        mysql.connection.commit()
        cur.close()
        session.pop('username', None)
        session.pop('name', None)
        session.pop('profile_picture', None)
        rv = getCountData()
        return render_template('login.html', primary='さよなら', colleger=rv[0], courses=rv[1], campuseslist=getAllCampus())
    elif 'username' not in session:
        return redirect(url_for('show_login'))


@app.route('/schedule/delete', methods=['GET'])
def delete_schedule():
    if 'username' in session:
        id = request.args.get('id')
        creator = get_creator_of_schedule(id)
        cur = mysql.connection.cursor()
        if creator[6] == session['username']:
            cur.execute("DELETE FROM class WHERE id=%s", (creator[0], ))
            success = '1'  # 'Your schedule has been deleted, all colleger can\'t use this schedule anymore'
        else:
            cur.execute("DELETE FROM account_class WHERE id=%s", (id, ))
            success = '2'  # 'Your schedule has been deleted'
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('show_schedule', success=success))
    elif 'username' not in session:
        return redirect(url_for('show_login'))


@app.route('/schedule/add', methods=['GET', 'POST'])
def add_schedule():
    if 'username' in session:
        if request.method == 'POST':
            submit = request.form['submit']
            if submit == 'myself':
                course = request.form['course']
                url = request.form['url']
                day = request.form['day']
                time = request.form['time']

                cur = mysql.connection.cursor()
                cur.execute("INSERT INTO class(name, url, day, time, created_by, campus_id) VALUES (%s, %s, %s, %s, %s, %s)",
                            (course, url, day, time, session['username'], session['campus']))
                mysql.connection.commit()
                cur.execute(
                    "SELECT * FROM class WHERE name=%s AND url=%s AND day=%s AND time=%s AND created_by=%s", (course, url, day, time, session['username']))
                rv = cur.fetchone()
                id_class = rv[0]
                cur.execute("INSERT INTO account_class(username_account, id_class) VALUES (%s, %s)",
                            (session['username'], id_class))
                mysql.connection.commit()
                cur.close()
            else:
                id_class = request.form['course']
                cur = mysql.connection.cursor()
                cur.execute("INSERT INTO account_class(username_account, id_class) VALUES (%s, %s)",
                            (session['username'], id_class))
                mysql.connection.commit()
                cur.close()
            return redirect(url_for('show_schedule', success='3'))
        else:
            cur = mysql.connection.cursor()
            cur.execute(
                "SELECT * FROM class WHERE campus_id=%s AND id NOT IN (SELECT id_class FROM account_class WHERE username_account = %s)", (session['campus'], session['username']))
            result = cur.fetchall()
            cur.close()
            rv = getCountData()
            return render_template('schedule_add.html', colleger=rv[0], courses=rv[1], courselist=result)
    else:
        return redirect(url_for('show_login'))


@app.route('/schedule/edit', methods=['GET', 'POST'])
def edit_schedule():
    if 'username' in session:
        if request.method == 'POST':
            course = request.form['course']
            url = request.form['url']
            day = request.form['day']
            time = request.form['time']

            cur = mysql.connection.cursor()
            cur.execute("UPDATE class SET name=%s, url=%s, day=%s, time=%s WHERE created_by=%s AND id=%s",
                        (course, url, day, time, session['username'], request.args.get('id')))
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('show_schedule', success='4'))
        else:
            id = request.args.get('id')
            print('id '+id)
            cur = mysql.connection.cursor()
            cur.execute(
                "SELECT * FROM class WHERE id=%s AND created_by=%s", (id, session['username']))
            result = cur.fetchone()
            cur.close()
            if result is None:
                return redirect(url_for('show_schedule'))
            rv = getCountData()
            return render_template('schedule_edit.html', colleger=rv[0], courses=rv[1], data=result)
    elif 'username' not in session:
        return redirect(url_for('show_login'))


@app.route('/campus/request')
def show_campusreq():
    if 'username' in session:
        return redirect(url_for('show_dashboard'))
    elif 'username' not in session:
        rv = getCountData()
        return render_template('campusrequest.html', colleger=rv[0], courses=rv[1])


# bikin fungsi robot autorun
# SELECT a.username, a.password, a.dhooks, c.name AS class_name, c.url AS class_url, c.day AS class_day, c.time AS class_time FROM account AS a
# INNER JOIN account_class AS ac ON ac.username_account = a.username
# INNER JOIN class AS c ON c.id = ac.id_class AND c.day = 'rabu'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=85)
