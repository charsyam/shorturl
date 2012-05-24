import MySQLdb
import urllib
import sys
import os
import redis
import pdb
from flask import Flask, request, session, g, redirect, url_for, \
abort, render_template, flash

# configuration
DB_HOST='127.0.0.1'
DB_USER=''
DB_PASSWORD=''
DB_FILE='shorturl'

REDIS_ADDRESS='127.0.0.1'
REDIS_PORT=1212
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'
DIVISION_SEED=0
REDIS_INCR_KEY = 'short_url_count'

app = Flask(__name__)
app.config.from_object(__name__)

global g_cursor
global g_redis

domain="sho.rt"

def ChangeHex(n):
    x = (n % 16)
    c = ""
    if (x < 10):
        c = x
    if (x == 10):
        c = "a"
    if (x == 11):
        c = "b"
    if (x == 12):
        c = "c"
    if (x == 13):
        c = "d"
    if (x == 14):
        c = "e"
    if (x == 15):
        c = "f"

    if (n - x != 0):
        return ChangeHex(n / 16) + str(c)
    else:
        return str(c)

def connect_redis():
    return redis.StrictRedis(host=REDIS_ADDRESS, port=REDIS_PORT, db=0)

@app.route('/')
def show_entries():
    g_cursor.execute('select short_url, real_url from tbl_shorturl')
    urls = [dict(short_url=row[0], real_url=row[1]) for row in g_cursor.fetchall()]
    return render_template('show_list.html', urls=urls, domain=domain)

@app.route('/<short_url>')
def redirect_real_url(short_url):
    try:
        value = get_realurl( short_url )
        return value
    except Exception as inst:
        return str(inst)

def create_short_url_data(seed, count):
    url = "%02x%s"%(seed, ChangeHex(count))
    return url

def get_count(cursor, url):
    value = g_redis.incr(REDIS_INCR_KEY)
    return value

def save_short_url( cursor, short_url, real_url ):
#    cursor.execute( "insert into tbl_shorturl values( 0, '%s', '%s', 0, now() )"%( real_url, short_url) )
    pass

def create_short_url(cursor, url):
    real_url = urllib.quote(url.encode('utf8'), '/:')
    try:
        count = get_count(cursor, real_url)
    except:
        raise Exception("Error: Duplicate url: %s"%url)

    short_url = create_short_url_data( DIVISION_SEED, count )
    save_short_url( cursor, short_url, real_url )
    g_redis.set( short_url, real_url )
    return short_url

@app.route('/add', methods=['POST'])
def add_entry():
    try:
        real_url = request.form['real_url'].strip();
        if( real_url == '' ):
            flash("No url")
        else:
            short_url = create_short_url( g_cursor, request.form['real_url'])
            flash('New entry was successfully posted')
    except Exception as inst:
        flash(str(inst))

    #pdb.set_trace()
    return redirect(url_for('show_entries'))

@app.route('/create/<path:url>')
def create_shorturl(url):
    try:
        real_url = url.strip();
        if( real_url == '' ):
            abort(401)

        #pdb.set_trace()
        short_url = create_short_url( g_cursor, url )
    except Exception as inst:
        return str(inst)

    return "http://%s/%s"%(domain, short_url)

def get_realurl(short_url):
    #pdb.set_trace()
    url = g_redis.get(short_url)
    if url:
        return url

    g_cursor.execute( "select real_url from tbl_shorturl where short_url='%s'"%(short_url) )
    if( g_cursor.arraysize > 0 ):
        value = g_cursor.fetchone()[0]
        g_redis.set( short_url, value )
    else:
        flash("Error: No url exists")

    return value

if __name__=='__main__':
    g_redis = connect_redis() 
    db=MySQLdb.connect( host=DB_HOST, user=DB_USER, passwd=DB_PASSWORD,db=DB_FILE)
    g_cursor=db.cursor()
    g_cursor.execute( "SET AUTOCOMMIT=1" );
    start_port = int( sys.argv[1] )
    app.run(host='0.0.0.0', port=start_port) 

