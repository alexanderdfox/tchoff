import sqlite3
import os
import statistics
import datetime
from flask import Flask, request, render_template, g, send_from_directory

app = Flask(__name__, subdomain_matching=True)
app.config['SERVER_NAME'] = "tchoff.com"
path = '/var/www/tchoff/tchoff.com/static/databases/'


def get_db(DATABASE):
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.teardown_appcontext
def close(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/static/<path:filename>')
def serve_databases(filename):
    root_dir = os.path.dirname(os.getcwd())
    return send_from_directory(os.path.join(root_dir, 'static'), filename)


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@app.route('/', methods=['GET', 'POST'], subdomain="<subdomain>")
def year(subdomain=None):
    if subdomain != "www":
        subdomain = path + subdomain + '.db'
        cur = get_db(subdomain).cursor()
        cur.execute('SELECT * FROM `states` ORDER BY state ASC;')
        states = cur.fetchall()
        data = []
        totalVotes = 0
        for state in states:
            table = state[1] + ".votes"
            cur.execute(
                'SELECT * FROM "{}" ORDER BY vote ASC;'
                .format(table.replace('"', '""')))
            vote = cur.fetchall()
            cur.execute(
                'SELECT * FROM "{}" ORDER BY count DESC LIMIT 1;'
                .format(table.replace('"', '""')))
            winner = cur.fetchall()
            data.append([state, vote, winner])
            count = cur.execute('SELECT sum(count) FROM "{}";'.format(
                table.replace('"', '""'))).fetchall()
            if count[0][0] != None:
                totalVotes += count[0][0]
        cur.execute('INSERT INTO "ip_log" (ip,datetime) VALUES (?, ?);', [request.remote_addr, datetime.datetime.now()])
        get_db(subdomain).commit()
        cur.close()
        return render_template('year.html', data=data, totalVotes=totalVotes)
    else:
        return render_template('index.html')


@app.route('/<state>/', methods=['GET', 'POST'], subdomain="<subdomain>")
def state(state=None, subdomain=None):
    subdomain = path + subdomain + '.db'
    cur = get_db(subdomain).cursor()
    cur.execute('SELECT * FROM `candidates` ORDER BY name ASC;')
    candidates = cur.fetchall()
    cur.execute('SELECT * FROM `states` WHERE abbr = ?;', [state])
    stateInfo = cur.fetchall()
    cur.execute(
        'SELECT SUM(count) FROM "{}";'
        .format(stateInfo[0][1] + ".votes".replace('"', '""')))
    totalVotes = cur.fetchall()[0][0]
    votes = []
    for candidate in candidates:
        cur.execute('SELECT * FROM "{}" WHERE vote = ?;'.format(
            stateInfo[0][1] + ".votes".replace('"', '""')), [candidate[1]])
        votes.append([candidate, cur.fetchall()])
    cur.execute('INSERT INTO "ip_log" (ip,datetime) VALUES (?, ?);', [request.remote_addr, datetime.datetime.now()])
    get_db(subdomain).commit()
    cur.close()
    return render_template('state.html', state=stateInfo[0][1], votes=votes, abbr=stateInfo[0][3], totalVotes=totalVotes)

#questions per state
@app.route('/q/<state>/', methods=['GET', 'POST'], subdomain="<subdomain>")
def qstate(state=None, subdomain=None):
    subdomain = path + subdomain + '-Questions.db'
    cur = get_db(subdomain).cursor()
    cur.execute('SELECT * FROM `states` WHERE abbr = ?;', [state])
    stateInfo = cur.fetchall()
    cur.execute('SELECT Questions FROM `Questions`;')
    questions = cur.fetchall()
    cur.execute('INSERT INTO "ip_log" (ip,datetime) VALUES (?, ?);', [request.remote_addr, datetime.datetime.now()])
    get_db(subdomain).commit()
    cur.close()
    return render_template('qstate.html', state=stateInfo[0][1], abbr=stateInfo[0][3], questions=questions)
#end questions per state

@app.route('/<state>/top10/', methods=['GET', 'POST'], subdomain="<subdomain>")
@app.route('/top10/', methods=['GET', 'POST'], subdomain="<subdomain>")
def top10(state=None, subdomain=None):
    subdomain = path + subdomain + '.db'
    if state:
        cur = get_db(subdomain).cursor()
        cur.execute('SELECT * FROM `states` WHERE abbr = ?;', [state])
        stateInfo = cur.fetchall()
        cur.execute('SELECT * FROM "{}" ORDER BY count DESC LIMIT 10;'.format(
            stateInfo[0][1] + ".votes".replace('"', '""')))
        votes = cur.fetchall()
        cur.execute('INSERT INTO "ip_log" (ip,datetime) VALUES (?, ?);', [request.remote_addr, datetime.datetime.now()])
        get_db(subdomain).commit()
        cur.close()
        votes = [stateInfo[0][1], votes]
    else:
        cur = get_db(subdomain).cursor()
        cur.execute('SELECT * FROM `states` ORDER BY state ASC;')
        states = cur.fetchall()
        votes = []
        for state in states:
            cur.execute('SELECT * FROM "{}" ORDER BY count DESC LIMIT 10;'.format(
                state[1] + ".votes".replace('"', '""')))
            votes.append([cur.fetchall(), state])
        cur.execute('INSERT INTO "ip_log" (ip,datetime) VALUES (?, ?);', [request.remote_addr, datetime.datetime.now()])
        get_db(subdomain).commit()
        cur.close()
        votes = ["50 States and D.C.", votes]
    return render_template('top10.html', votes=votes)


@app.route('/electoral/', methods=['GET', 'POST'], subdomain="<subdomain>")
def electoral(subdomain=None):
    subdomain = path + subdomain + '.db'
    cur = get_db(subdomain).cursor()
    cur.execute('SELECT * FROM `states` ORDER BY state ASC;')
    states = cur.fetchall()
    votes = []
    for state in states:
        cur.execute('SELECT * FROM "{}" ORDER BY count DESC LIMIT 1;'.format(
            state[1] + ".votes".replace('"', '""')))
        vote = cur.fetchall()
        if len(vote) != 0:
            if vote[0][1]:
                cur.execute(
                    'SELECT party FROM candidates WHERE name = ?;', [vote[0][1]])
                party = cur.fetchall()
            else:
                party = ""
        else:
            party = ""
        votes.append([state, vote, party])
    cur.execute('INSERT INTO "ip_log" (ip,datetime) VALUES (?, ?);', [request.remote_addr, datetime.datetime.now()])
    get_db(subdomain).commit()
    cur.close()
    return render_template('electoral.html', votes=votes)


@app.route('/vote/', methods=['POST', 'GET'], subdomain="<subdomain>")
def vote(subdomain="<subdomain>"):
    subdomain = path + subdomain + '.db'
    name = request.form['name']
    state = request.form['state']
    cur = get_db(subdomain).cursor()
    cur.execute('SELECT * FROM "{}" WHERE vote = ?;'.format(
        state + '.votes'.replace('"', '""')), [name])
    if cur.fetchall():
        cur.execute('UPDATE "{}" SET count = count + 1 WHERE vote = ?;'.format(
            state + '.votes'.replace('"', '""')), [name])
    else:
        cur.execute('INSERT INTO "{}" (vote,count) VALUES (?, 1);'.format(
            state + '.votes'.replace('"', '""')), [name])
    get_db(subdomain).commit()
    cur.execute('INSERT INTO "ip_log" (ip,datetime) VALUES (?, ?);', [request.remote_addr, datetime.datetime.now()])
    get_db(subdomain).commit()
    cur.close()
    return render_template('vote.html', votedFor=name, votedIn=state)


# BROKEN!
# @app.route('/winning/', methods=['GET', 'POST'], subdomain="<subdomain>")
# def winning(subdomain="<subdomain>"):
#     subdomain = path + subdomain + '.db'
#     cur = get_db(subdomain).cursor()
#     cur.execute('SELECT * FROM `candidates`;')
#     candidates = cur.fetchall()
#     cur.execute('SELECT * FROM `states` ORDER BY state ASC;')
#     states = cur.fetchall()
#     electoral = []
#     for state in states:
#         for candidate in candidates:
#             cur.execute('SELECT * FROM "{}" WHERE vote = ? ORDER BY count DESC LIMIT 1'.format(
#                 state[1] + '.votes'.replace('"', '""')), [candidate[1]])
#             count = 0
#             elec = 0
#             for votes in cur.fetchall():
#                 count += votes[2]
#                 elec = state[2]
#             electoral.append([candidate, count, elec, state])
#     electoral.sort(key=lambda x: x[1], reverse=True)
#     return render_template('winning.html', electoral=electoral)
# BROKEN!

# @app.route('/stats/', methods=['POST', 'GET'], subdomain="<subdomain>")
# def stats(subdomain="<subdomain>"):
#     subdomain = path + subdomain + '.db'
#     cur = get_db(subdomain).cursor()
#     stats = []
#     for row in cur.execute('SELECT name FROM sqlite_master WHERE type = "table" AND name LIKE "%votes";').fetchall():
#         stat = []
#         if cur.execute('SELECT * FROM "{}";'.format(row[0])).fetchall() != None:
#             for row2 in cur.execute('SELECT * FROM "{}";'.format(row[0])).fetchall():
#                 stat.append(row2[2])
#             state = [["Sum", int(sum(stat))], ["Mean", int(statistics.mean(stat))], ["Median", int(statistics.median(stat))], ["Standard Deviation", int(statistics.stdev(stat))]]
#         stats.append(state)
#     cur.execute('INSERT INTO "ip_log" (ip,datetime) VALUES (?, ?);', [request.remote_addr, datetime.datetime.now()])
#     get_db(subdomain).commit()
#     cur.close()
#     return render_template('stats.html', stats=stats)


@app.route('/privacy/', methods=['POST', 'GET'], subdomain="<subdomain>")
def privacy(subdomain="<subdomain>"):
    print(subdomain)
    return render_template('privacy.html')


@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(410)
@app.errorhandler(500)
def errorPage(e):
    return render_template('error.html', error=e)
