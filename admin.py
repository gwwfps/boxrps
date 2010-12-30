#!/usr/bin/env python
import logging
import yaml
import cgi
from xml.dom import minidom as md
from datetime import datetime, timedelta
from collections import defaultdict
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext import db
from django.utils import simplejson

from models import *
from utils import render_to, parse_item


class AdminHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write('Hello world!')

class ParseHandler(webapp.RequestHandler):
    def get(self):
        render_to(self.response, 'admin/parse.html')
    def post(self):
        all_members = Member.all()

        parsed = md.parseString(self.request.get('log').encode('utf-8'))
        members = []
        for member in parsed.getElementsByTagName('member'):
            try:
                name = member.firstChild.firstChild
            except AttributeError:
                continue
            if name is None:
                continue
            name = name.toxml().strip().capitalize()
            class_ = member.childNodes[1].firstChild.toxml().upper()
            m = Member.gql('WHERE name = :1', name).get()
            if not m:
                new_member = Member(name=name, class_=class_)
                new_member.put()
            else:
                m.class_=class_
                m.put()
            members.append(name)

        items = []
        for item in parsed.getElementsByTagName('item'):
            try:
                name = item.firstChild.firstChild.toxml()
            except AttributeError:
                continue
            time = item.childNodes[1].firstChild.toxml()
            looter = item.childNodes[2].firstChild.toxml()
            pt = item.childNodes[3].firstChild.toxml()
            items.append(parse_item(name) + (time, looter, pt))

        render_to(self.response, 'admin/parseadd.html',
                  members=set(members), all_members=all_members, events=Event.all(),
                  datetime=parsed.getElementsByTagName('start')[0].firstChild.toxml(),
                  items=items)

class RaidHanlder(webapp.RequestHandler):
    def get(self):
        pass

    def post(self):
        pass



class EventHandler(webapp.RequestHandler):
    def get(self):
        render_to(self.response, 'admin/events.html', events=Event.all())
    def post(self):
        batch = self.request.get('batch')
        batch = batch.split('\n')
        for line in batch:
            event, pt = line.split('\t')
            Event(name=cgi.escape(event), default_pt = int(float(pt.strip()))).put()
        self.get()

class AjaxHandler(webapp.RequestHandler):
    def post(self):
        action = self.request.get('action')
        if action == 'addevent':
            event = Event(name=self.request.get('name'),
                          default_pt=int(self.request.get('pt')))
            event.put()
        elif action == 'geteventpt':
            event = Event.get(db.Key(self.request.get('key')))
            if event:
                self.response.out.write(simplejson.dumps({'pt':event.default_pt}))
        elif action == 'addraid':
            date = datetime.strptime(self.request.get('date'), '%Y.%m.%d %H:%M')
            pt = int(self.request.get('pt'))
            note = self.request.get('note')
            members = self.request.get('members').split('|')[0:-1]
            loot = self.request.get('loot').split('|')[0:-1]
            memcache = {}
            for m in Member.all():
                memcache[m.name] = m
            
            key = self.request.get('key')
            if key:
                encounter = Encounter.get(db.Key(key))
            else:
                encounter = None
            if encounter:
                delta = 0
                oldpt = encounter.pt
                if not encounter.pt == pt:
                    delta = pt - encounter.pt
                    encounter.pt = pt
                encounter.note = note
                encounter.datetime = date
                old_members = set([m.name for m in encounter.attending_members()])
                members = set([member.strip().capitalize() for member in members])
                remaining = old_members & members
                newly_added = members - old_members
                removed = old_members - members
                for m in remaining:
                    member = memcache[m]
                    member.earned += delta
                    member.balance += delta
                    member.put()
                for m in newly_added:
                    nm = memcache.get(m.strip().capitalize())
                    if not nm:
                        nm = Member(name=m)
                        memcache[m] = nm
                    nm.earned += pt
                    nm.balance += pt
                    nm.put()
                    encounter.attendees.append(nm.key())
                for m in removed:
                    dm = memcache[m]
                    dm.earned -= oldpt
                    dm.balance -= oldpt
                    dm.put()
                    encounter.attendees.remove(dm.key())
                encounter.put()
                Member.recalculate_attendance()
                
                lset = {}
                for l in encounter.loots:
                    lset[str(l.key())] = l
                plset = set(lset.keys())
                for piece in loot:
                    _, name, time, looter, cost, lkey = piece.split(';')
                    looter = looter.strip().capitalize()
                    cost = int(cost)*(-1)
                    time = datetime.strptime(time, '%Y.%m.%d %H:%M') 
                    if lkey in lset:
                        plset.remove(lkey)
                        l = lset[lkey]
                        if not l.looter.name == looter or not l.cost == cost:
                            m = l.looter
                            m.spent -= l.cost
                            m.balance -= l.cost
                            m.put()
                            ltr = memcache[looter]
                            ltr.spent += cost
                            ltr.balance += cost
                            ltr.put()
                            l.looter = ltr
                            l.cost = cost
                            l.put()
                    else:
                        item = Item.gql('WHERE name = :1', name).get()
                        if not item:
                            item = Item(name=name, gid=0, default_cost=cost)
                            item.put()
                        looter = memcache[looter]
                        looter.spent += cost
                        looter.balance += cost
                        looter.put()
        
                        loot = Loot(encounter=encounter, cost=cost, looter=looter,
                                    datetime=time, item=item)
                        loot.put()
                for rkey in plset:
                    l = lset[rkey]
                    m = l.looter
                    m.spent -= l.cost
                    m.balance -= l.cost
                    m.put()
                    l.delete()
                    
            else:
                event = Event.get(db.Key(self.request.get('event')))
    
                attendees = []
                for member in members:
                    m = memcache.get(member.strip().capitalize())
                    if not m:
                        m = Member(name=member)
                        memcache[member.strip().capitalize()] = m
                    m.earned += pt
                    m.balance += pt
                    m.put()
                    attendees.append(m.key())
    
                encounter = Encounter(event=event, note=note, pt=pt, datetime=date,
                                      attendees=attendees)
                encounter.put()   
                Member.recalculate_attendance()
                  
                for piece in loot:
                    logging.info(piece.encode('utf-8'))
                    id, name, time, looter, cost, _ = piece.split(';')
                    looter = looter.strip().capitalize()
                    try:
                        id = int(id)
                    except ValueError:
                        id = 0
                    time = datetime.strptime(time, '%Y.%m.%d %H:%M')
                    looter = memcache[looter]
                    cost = int(cost)*(-1)
    
                    item = Item.gql('WHERE name = :1', name).get()
                    if item:
                        if id:
                            item.gid = id
                            item.put()
                    else:
                        item = Item(name=name, gid=id, default_cost=cost)
                        item.put()
    
                    looter.spent += cost
                    looter.balance += cost
                    looter.put()
    
                    loot = Loot(encounter=encounter, cost=cost, looter=looter,
                                datetime=time, item=item)
                    loot.put()
            self.response.out.write(simplejson.dumps({'key': str(encounter.key())}))
        elif action == "deladjustment":
            aid = self.request.get('aid')
            adj = Adjustment.get(db.Key(aid))
            m = adj.member
            m.balance -= adj.pt
            m.adjusted -= adj.pt
            m.put()
            adj.delete()
            self.response.out.write(simplejson.dumps({}))

class ImportHandler(webapp.RequestHandler):
    def get(self):
        render_to(self.response, 'admin/import.html')
    def post(self):
        text = self.request.get('import')
        for line in text.split('\n'):
            line = line.split('\t')
            name = line[2].capitalize()
            earned = int(float(line[6]))
            spent = (-1)*int(float(line[7]))
            adjusted = int(float(line[8]))
            balance = int(float(line[9]))
            m = Member.gql('WHERE name = :1', name).get()
            if m:
                m.earned = earned
                m.spent = spent
                m.balance = balance
                m.adjusted = adjusted
            else:
                m = Member(name=name, spent=spent, earned=earned,
                           balance=balance, adjusted=adjusted)
            m.put()
        self.get()

class AdjustmentHandler(webapp.RequestHandler):
    def get(self):
        render_to(self.response, 'admin/adjust.html', members=Member.all(),
                  adjustments=Adjustment.all())
    def post(self):
        member = Member.gql('WHERE name = :1', self.request.get('member').capitalize()).get()
        if member:
            pt = int(self.request.get('pt'))
            reason = self.request.get('reason')
            dt = datetime.now()
            Adjustment(pt=pt, member=member, reason=reason, datetime=dt).put()
            member.adjusted += pt
            member.balance += pt
            member.usable = min(member.balance, member.attendance * member.balance / 100)
            member.put()
        self.get()

class YamlHandler(webapp.RequestHandler):
    def get(self):
        render_to(self.response, 'dump.html',
                  dump='<form action="/o/yaml" method="POST"><input type="submit" /> </form>')
    def post(self):
        stream = file('rps.yaml', 'r')
        data = yaml.load(stream)
        id_to_key = {}
        items = defaultdict(list)
        att = defaultdict(list)
        memcache = {}
        for m in Member.all():
            memcache[m.name] = m.key()
        for entry in data:
            if 'adjustment_id' in entry:
                continue
#                member = Member.gql('WHERE name = :1', entry['member_name']).get()
#                adj = Adjustment(pt=int(entry['adjustment_value']),
#                                 reason=entry['adjustment_reason'],
#                                 datetime=datetime.fromtimestamp(entry['adjustment_date']),
#                                 member=member)
#                adj.put()
#            elif 'item_id' in entry:
            if 'item_id' in entry:
                items[entry['raid_id']].append((entry['item_name'],
                                                entry['item_buyer'],
                                                entry['item_value'],
                                                entry['item_date']))
            elif 'raid_added_by' in entry:
                event = Event.gql('WHERE name = :1', entry['raid_name']).get()
                if event:
                    if not entry['raid_note']:
                        entry['raid_note'] = ''
                    raid = Encounter(event=event, note=entry['raid_note'],
                                     pt=int(entry['raid_value']),
                                     datetime=datetime.fromtimestamp(entry['raid_date']))
                    raid.put()
                    id_to_key[entry['raid_id']] = raid.key()
                else:
                    logging.error(entry)
            elif 'member_lastraid' in entry:
                continue
            else:
                try:
                    att[entry['raid_id']].append(entry['member_name'])
                except KeyError:
                    logging.error(entry)
        for rid, key in id_to_key.items():
            r = Encounter.get(key)
            for member in att[rid]:
                m = memcache[member.capitalize()]
                if m:
                    r.attendees.append(m)
                else:
                    logging.error(member)
            r.put()

            for name, buyer, value, date in items[rid]:
                try:
                    value = int(float(value))*(-1)
                except UnicodeEncodeError:
                    logging.error(name)
                item = Item.gql('WHERE name = :1', name).get()
                if not item:
                    item = Item(name=name, default_cost=value)
                    item.put()
                loot = Loot(item=item, encounter=key, cost=value,
                            looter=memcache[buyer],
                            datetime=datetime.fromtimestamp(date))
                loot.put()



        render_to(self.response, 'dump.html', dump=data)

class EditRaidHandler(webapp.RequestHandler):
    def get(self, key):
        raid = Encounter.get(db.Key(key))
        if raid:
            render_to(self.response, 'admin/parseadd.html', key=key,
                      members=set([m.name for m in raid.attending_members()]),
                      all_members=Member.all(), events=Event.all(),
                      datetime=raid.datetime.strftime('%Y.%m.%d %H:%M'),
                      items=[(i.item.gid, i.item.name, i.datetime.strftime('%Y.%m.%d %H:%M'), i.looter.name, (-1)*i.cost, str(i.key())) for i in raid.loots],
                      raid=raid)




def main():
    application = webapp.WSGIApplication([('/o/', AdminHandler),
                                          ('/o/parse', ParseHandler),
                                          ('/o/events', EventHandler),
                                          ('/o/ajax', AjaxHandler),
                                          ('/o/import', ImportHandler),
                                          ('/o/adjust', AdjustmentHandler),
                                          ('/o/yaml', YamlHandler),
                                          ('/o/editraid/(.+)', EditRaidHandler)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
