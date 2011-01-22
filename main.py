#!/usr/bin/env python
import urllib
from datetime import datetime, timedelta
from math import ceil
from collections import defaultdict
from google.appengine.ext.webapp import util

from app import app, request
from utils import render_template
from models import *

@app.route('/')
@app.route('/std/<sortby>/<dir>')
def roster(sortby='att', dir='d'):
    sorts = {
        'nme': 'name',
        'cls': 'class_',
        'bal': 'balance',
        'ern': 'earned',
        'spt': 'spent',
        'att': 'attendance',
        'usb': 'usable'
    }
    dirs = defaultdict(lambda: 'd')
    order = sorts.get(sortby, 'attendance')
    if dir == 'd':
        dirs[order] = 'a'
        order = '-'+order
    members = Member.all().order(order)
    return render_template('index.html', members=members, dir=dirs)

@app.route('/raids')
@app.route('/raids/<int:page>')
def raid_list(page=1):
    pages = int(ceil(float(Encounter.all().count())/30))
    encounters = Encounter.all().order('-datetime').fetch(30, offset=(page-1)*30)
    return render_template('raids.html', encounters=encounters, pages=range(1, pages+1))

@app.route('/member/<name>')
@app.route('/member/<name>/<option>')
def member_detail(name, option=None):
    member = Member.gql('WHERE name = :1',
                        urllib.unquote(name).decode('utf-8').capitalize()).get()
    if not member:
        abort(404)
       
    if option == '/raids':
        raids = member.attended_encounters
        return render_template('memberraids.html', member=member, raids=raids)
    elif option == '/loots':
        return render_template('memberloots.html', member=member)
    elif option == '/attd':
        return render_template('memberattd.html', member=member, attd=member.eattd_set.order('-attd'))
    else:
        raids = member.attended_encounters.fetch(10)
        return render_template('member.html', member=member,
                  raids=raids, loots=member.loot_set.order('-datetime').fetch(5))

@app.route('/events')
def event_list():
    events = Event.all().order('name')
    return render_template('events.html', events=events)

@app.route('/event/<key>')
def event_detail(key):
    event = Event.get(db.Key(key))
    if event:
        event.calc_attd()
        return render_template('event.html', event=event, attd=event.eattd_set.order('-attd'))
                
@app.route('/raid/<key>')
def raid_detail(key):
    raid = Encounter.get(db.Key(key))
    if raid:
        return render_template('raid.html', raid=raid)


if __name__ == '__main__':
    util.run_wsgi_app(app)
