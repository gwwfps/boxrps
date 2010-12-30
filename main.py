#!/usr/bin/env python
import urllib
from math import ceil
from collections import defaultdict
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from utils import render_to
from models import *


class MainHandler(webapp.RequestHandler):
    def get(self, sortby='att', dir='d'):
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
        render_to(self.response, 'index.html', members=members, dir=dirs)

class RaidListHandler(webapp.RequestHandler):
    def get(self, page=1):
        pages = ceil(float(Encounter.all().count())/30)
        encounters = Encounter.all().order('-datetime').fetch(30, offset=(int(page)-1)*30)
        render_to(self.response, 'raids.html', encounters=encounters, pages=range(1, pages+1))

class MemberDetailHandler(webapp.RequestHandler):
    def get(self, name):
        member = Member.gql('WHERE name = :1', urllib.unquote(name).decode('utf-8').capitalize()).get()
        if member:
            render_to(self.response, 'member.html', member=member)

class EventListHandler(webapp.RequestHandler):
    def get(self):
        events = Event.all().order('name')
        render_to(self.response, 'events.html', events=events)

class RaidDetailHandler(webapp.RequestHandler):
    def get(self, key):
        raid = Encounter.get(db.Key(key))
        if raid:
            render_to(self.response, 'raid.html', raid=raid)


def main():
    application = webapp.WSGIApplication([('/', MainHandler),
                                          ('/std/(.+)/(.+)', MainHandler),
                                          ('/raids', RaidListHandler),
                                          ('/raids/(\d+)', RaidListHandler),
                                          ('/events', EventListHandler),
                                          ('/raid/(.+)', RaidDetailHandler),
                                          ('/member/(.+)', MemberDetailHandler)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
