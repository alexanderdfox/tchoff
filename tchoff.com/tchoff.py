import sqlite3
import os
import statistics
import datetime
import secure
from flask import Flask, request, render_template, g, send_from_directory

secure_headers = secure.Secure()

app = Flask(__name__, subdomain_matching=True)
app.config['SERVER_NAME'] = "tchoff.com"
path = '/var/www/tchoff/tchoff.com/static/databases/'


def get_db(DATABASE):
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.after_request
def set_secure_headers(response):
    secure_headers.framework.flask(response)
    return response

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

@app.route('/fox/', methods=['GET', 'POST'])
def fox():
    return render_template('fox.html')

@app.route('/egg/', methods=['GET', 'POST'])
def egg():
    return render_template('easter.html')

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
            cur.execute(html.escape(
                'SELECT * FROM "{}" ORDER BY vote ASC;'
                .format(table.replace('"', '""'))))
            vote = cur.fetchall()
            cur.execute(html.escape(
                'SELECT * FROM "{}" ORDER BY count DESC LIMIT 1;'
                .format(table.replace('"', '""'))))
            winner = cur.fetchall()
            data.append([state, vote, winner])
            count = cur.execute(html.escape('SELECT sum(count) FROM "{}";'.format(
                table.replace('"', '""')))).fetchall()
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
    cur.execute('SELECT DISTINCT district FROM `candidates` WHERE state = ?;', [state])
    districts = cur.fetchall()
    districts.append(['PRESIDENT'])
    get_db(subdomain).commit()
    cur.close()
    return render_template('state.html', state=state, districts=districts)

@app.route('/<state>/<district>/', methods=['GET', 'POST'], subdomain="<subdomain>")
def district(state=None, district=None, subdomain=None):
    subdomain = path + subdomain + '.db'
    cur = get_db(subdomain).cursor()
    if district != "PRESIDENT":
        cur.execute('SELECT * FROM `candidates` WHERE district = ? AND state = ? ORDER BY name ASC;', [district, state])
        candidates = cur.fetchall()
    else:
        cur.execute('SELECT * FROM `candidates` WHERE district = ? ORDER BY name ASC;', ['PRESIDENT'])
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
    return render_template('district.html', state=stateInfo[0][1], votes=votes, totalVotes=totalVotes)

#questions per state
@app.route('/q/<state>/', methods=['GET', 'POST'], subdomain="<subdomain>")
def qstate(state=None, subdomain=None):
    subdomain = path + subdomain + '-Questions.db'
    cur = get_db(subdomain).cursor()
    cur.execute('SELECT * FROM `states` WHERE abbr = ?;', [state])
    stateInfo = cur.fetchall()
    cur.execute(html.escape('SELECT * FROM "{}";'.format(
                stateInfo[0][1] + '.Questions'.replace('"', '""'))))
    questions = cur.fetchall()
    cur.execute('INSERT INTO "ip_log" (ip,datetime) VALUES (?, ?);', [request.remote_addr, datetime.datetime.now()])
    get_db(subdomain).commit()
    cur.close()
    return render_template('qstate.html', state=stateInfo[0][1], questions=questions,)

@app.route('/q/', methods=['GET', 'POST'], subdomain="<subdomain>")
def q(state=None, subdomain=None):
    subdomain = path + subdomain + '-Questions.db'
    cur = get_db(subdomain).cursor()
    state = request.form['state']
    answers = request.form
    for a in answers:
        if a != "state":
            if answers[a] == "1":
                table_name = state + '.Questions'
                escaped_table_name = table_name.replace('"', '""')
                query = 'UPDATE "{}" SET "YES" = "YES" + 1 WHERE id = ?;'.format(escaped_table_name)
                cur.execute(html.escape(query), [a])
            elif answers[a] == "3":
                table_name = state + '.Questions'
                escaped_table_name = table_name.replace('"', '""')
                query = 'UPDATE "{}" SET "NO" = "NO" + 1 WHERE id = ?;'.format(escaped_table_name)
                cur.execute(html.escape(query), [a])
            elif answers[a] == "2":
                table_name = state + '.Questions'
                escaped_table_name = table_name.replace('"', '""')
                query = 'UPDATE "{}" SET "UNDECIDED" = "UNDECIDED" + 1 WHERE id = ?;'.format(escaped_table_name)
                cur.execute(html.escape(query), [a])
    cur.execute('INSERT INTO "ip_log" (ip,datetime) VALUES (?, ?);', [request.remote_addr, datetime.datetime.now()])
    get_db(subdomain).commit()
    cur.close()
    return render_template('qstate.html', state=state, answers=answers)
#end questions per state

@app.route('/<state>/top10/', methods=['GET', 'POST'], subdomain="<subdomain>")
@app.route('/top10/', methods=['GET', 'POST'], subdomain="<subdomain>")
def top10(state=None, subdomain=None):
    subdomain = path + subdomain + '.db'
    if state:
        cur = get_db(subdomain).cursor()
        cur.execute('SELECT * FROM `states` WHERE abbr = ?;', [state])
        stateInfo = cur.fetchall()
        table_name = stateInfo[0][1] + ".votes"
        escaped_table_name = table_name.replace('"', '""')
        query = 'SELECT * FROM "{}" ORDER BY count DESC LIMIT 10;'.format(escaped_table_name)
        cur.execute(query)
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
            table_name = state[1] + ".votes"
            escaped_table_name = table_name.replace('"', '""')
            query = 'SELECT * FROM "{}" ORDER BY count DESC LIMIT 10;'.format(escaped_table_name)
            cur.execute(query)
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
    table_name = state + '.votes'
    escaped_table_name = table_name.replace('"', '""')
    query = 'SELECT * FROM "{}" WHERE vote = ?;'.format(escaped_table_name)
    cur.execute(html.escape(query), [name])
    if cur.fetchall():
        table_name = state + '.votes'
        escaped_table_name = table_name.replace('"', '""')
        query = 'UPDATE "{}" SET count = count + 1 WHERE vote = ?;'.format(escaped_table_name)
        cur.execute(html.escape(query), [name])
    else:
        table_name = state + '.votes'
        escaped_table_name = table_name.replace('"', '""')
        query = 'INSERT INTO "{}" (vote,count) VALUES (?, 1);'.format(escaped_table_name)
        cur.execute(html.escape(query), [name])
    get_db(subdomain).commit()
    cur.execute('INSERT INTO "ip_log" (ip,datetime) VALUES (?, ?);', [request.remote_addr, datetime.datetime.now()])
    get_db(subdomain).commit()
    cur.close()
    return render_template('vote.html', votedFor=name, votedIn=state)

#testing
# @app.route('/winning/', methods=['GET', 'POST'], subdomain="<subdomain>")
# def winning(subdomain="<subdomain>"):
#     subdomain = subdomain + '.db'
#     cur = get_db(subdomain).cursor()
#     cur.execute('SELECT * FROM "candidates";')
#     candidates = cur.fetchall()
#     cur.execute('SELECT * FROM "states" ORDER BY state ASC;')
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

# @app.route('/stats/', methods=['POST', 'GET'], subdomain="<subdomain>")
# def stats(subdomain="<subdomain>"):
#     subdomain = subdomain + '.db'
#     cur = get_db(subdomain).cursor()
#     stats = []
#     for row in cur.execute('SELECT name FROM sqlite_master WHERE type = "table" AND name LIKE "%votes";').fetchall():
#         stat = []
#         state = []
#         if cur.execute('SELECT * FROM "{}";'.format(row[0])).fetchall():
#             for row2 in cur.execute('SELECT * FROM "{}";'.format(row[0])).fetchall():
#                 stat.append(row2[2])
#             state = [["Sum", int(sum(stat))], ["Mean", int(statistics.mean(stat))], ["Median", int(statistics.median(stat))], ["Standard Deviation", int(statistics.stdev(stat))]]
#             stats.append(state)
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
