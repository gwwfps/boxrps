import logging
from datetime import datetime, timedelta
from google.appengine.ext import db

class Member(db.Model):
    name = db.StringProperty()
    class_ = db.StringProperty(default="UNKNOWN")
    attendance = db.IntegerProperty(default=0)

    earned = db.IntegerProperty(default=0)
    spent = db.IntegerProperty(default=0)
    adjusted = db.IntegerProperty(default=0)
    balance = db.IntegerProperty(default=0)
    usable = db.IntegerProperty(default=0)

    @property
    def attended_encounters(self):
        return Encounter.all().filter("attendees =", self.key()).order('-datetime')

    @classmethod
    def recalculate_attendance(cls):
        total = Encounter.all().filter('datetime >', datetime.now()-timedelta(weeks=4)).count()
        for m in cls.all():
            attended = m.attended_encounters.filter('datetime >', datetime.now()-timedelta(weeks=4)).count()
            attended = float(attended)
            m.attendance = int(attended/total*100)
            m.usable = min(m.balance, m.attendance * m.balance / 100)
            m.put()

class Event(db.Model):
    name = db.StringProperty(required=True)
    default_pt = db.IntegerProperty(default=0)

class Encounter(db.Model):
    event = db.ReferenceProperty(Event, collection_name='encounters')
    note = db.StringProperty()
    pt = db.IntegerProperty(required=True, default=0)
    attendees = db.ListProperty(db.Key)
    datetime = db.DateTimeProperty()

    def attending_members(self):
        for key in self.attendees:
            yield Member.get(key)

class Item(db.Model):
    name = db.StringProperty(required=True)
    gid = db.IntegerProperty(default=0)
    default_cost = db.IntegerProperty()

class Loot(db.Model):
    item = db.ReferenceProperty(Item)
    encounter = db.ReferenceProperty(Encounter, collection_name='loots')
    cost = db.IntegerProperty()
    looter = db.ReferenceProperty(Member)
    datetime = db.DateTimeProperty()

class Adjustment(db.Model):
    pt = db.IntegerProperty()
    member = db.ReferenceProperty(Member)
    reason = db.StringProperty()
    datetime = db.DateTimeProperty()

