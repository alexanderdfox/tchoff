import sqlite3, array
from flask import Flask, escape, request, render_template, g

DATABASE = '2024.db'

app = Flask(__name__, static_url_path='/static')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    cur = get_db().cursor()
    cur.execute("SELECT * FROM `states` ORDER BY state ASC;")
    states = cur.fetchall()
    data = []
    for state in states:
        cur.execute("SELECT * FROM `"+state[1]+".votes` ORDER BY vote ASC;")
        vote = cur.fetchall()
        cur.execute("SELECT * FROM `"+state[1]+".votes` ORDER BY count DESC LIMIT 1;")
        winner = cur.fetchall()
        data.append([state,vote,winner])
    cur.close()
    return render_template('index.html', data=data)

@app.route('/<state>/', methods=['GET', 'POST'])
def state(state=None):
    cur = get_db().cursor()
    cur.execute("SELECT * FROM `candidates` ORDER BY name ASC;")
    candidates = cur.fetchall()
    cur.execute("SELECT * FROM `states` WHERE abbr = '"+state+"';")
    stateInfo = cur.fetchall()
    votes = []
    for candidate in candidates:
        cur.execute('SELECT * FROM "{}" WHERE vote = ?;'.format(stateInfo[0][1]+".votes".replace('"', '""')), [candidate[1]])
        votes.append([candidate,cur.fetchall()])
    cur.close()
    return render_template('state.html',state=stateInfo[0][1],votes=votes,abbr=stateInfo[0][3])

@app.route('/<state>/top10/', methods=['GET', 'POST'])
@app.route('/top10/', methods=['GET', 'POST'])
def top10(state=None):
    if state:
        cur = get_db().cursor()
        cur.execute("SELECT * FROM `states` WHERE abbr = '"+state+"';")
        stateInfo = cur.fetchall()
        cur.execute("SELECT * FROM `"+stateInfo[0][1]+".votes` ORDER BY count DESC LIMIT 10;")
        votes = cur.fetchall()
        cur.close()
        votes = [stateInfo[0][1],votes]
    else:
        cur = get_db().cursor()
        cur.execute("SELECT * FROM `states` ORDER BY state ASC;")
        states = cur.fetchall()
        votes = []
        for state in states:
            cur.execute("SELECT * FROM `"+state[1]+".votes` ORDER BY count DESC LIMIT 10;")
            votes.append([cur.fetchall(),state])
        cur.close()
        votes = ["50 States and D.C.",votes]
    return render_template('top10.html',votes=votes)

@app.route('/electoral/', methods=['GET', 'POST'])
def electoral():
    cur = get_db().cursor()
    cur.execute("SELECT * FROM `states` ORDER BY state ASC;")
    states = cur.fetchall()
    votes = []
    for state in states:
        cur.execute("SELECT * FROM `"+state[1]+".votes` ORDER BY vote DESC LIMIT 1;")
        vote = cur.fetchall()
        if len(vote) != 0:
            print(vote)
            if vote[0][1]:
                cur.execute("SELECT party FROM candidates WHERE name = ?;", [vote[0][1]])
                party = cur.fetchall()
            else:
                party = ""
        else:
            party = ""
        print(party)
        votes.append([state,vote,party])
    cur.close()
    return render_template('electoral.html',votes=votes)

@app.route('/vote/', methods=['POST', 'GET'])
def vote():
    name = request.form['name']
    state = request.form['state']
    cur = get_db().cursor()
    cur.execute('SELECT * FROM "{}" WHERE vote = ?;'.format(state+'.votes'.replace('"', '""')), [name])
    if cur.fetchall():
        cur.execute('UPDATE "{}" SET count = count + 1 WHERE vote = ?;'.format(state+'.votes'.replace('"', '""')), [name])
    else:
        cur.execute('INSERT INTO "{}" (vote,count) VALUES (?, 1);'.format(state+'.votes'.replace('"', '""')), [name])
    get_db().commit()
    cur.close()
    return render_template('vote.html',votedFor=name,votedIn=state)

@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(410)
@app.errorhandler(500)
def errorPage(e):
    return render_template('error.html', error=e)