import os
from google.appengine.ext.webapp import template
from google.appengine.api import users

def render_template(file, **context):
    template.register_template_library('filters')
    path = os.path.join(os.path.dirname(__file__), 'templates', file)
    context['admin'] = users.is_current_user_admin()
    return template.render(path, context)

def get_text(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)

def parse_item(item):
    item = item.split('$H')[1]
    pcs = item.split('$h')
    id = int(pcs[0].split(':')[1])
    name = pcs[1][1:-1]
    return (id, name)