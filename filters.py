# -*- coding: utf-8 -*-
from google.appengine.ext.webapp import template

register = template.create_template_register()
classes = {
    'Deathknight': (u'死亡骑士', 'C41F3B'),
    'Druid': (u'德鲁伊', 'FF7D0A'),
    'Hunter': (u'猎人', 'ABD473'),
    'Mage': (u'法师', '69CCF0'),
    'Paladin': (u'圣骑士', 'F58CBA'),
    'Priest': (u'牧师', 'FFFFFF'),
    'Rogue': (u'潜行者', 'FFF569'),
    'Shaman': (u'萨满', '0070DE'),
    'Warlock': (u'术士', '9482C9'),
    'Warrior': (u'战士', 'C79C6E'),
    'Unknown': (u'未知', '999')
}

@register.filter
def rp(value):
    if value > 0:
        return '<span style="color:#33a691;">%d</span>'%value
    elif value < 0:
        return '<span style="color:#f25a38;">%d</span>'%value
    return value

@register.filter
def class_(value):
    if value:
        name, color = classes[value.capitalize()]
        return '<span style="color:#%s;">%s</span>' % (color, name)
    else:
        return u'<span style="color:#999;">未知</span>'

@register.filter
def class_color(value):
    if value.class_:
        return '<a href="/member/%s" style="color:#%s;">%s</a>' % (value.name, classes[value.class_.capitalize()][1], value.name)
    else:
        return '<a href="/member/%s" style="color:#999;">%s</a>' % (value.name, value.name)