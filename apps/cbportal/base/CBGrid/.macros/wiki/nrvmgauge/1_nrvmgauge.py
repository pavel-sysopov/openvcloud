
def main(j, args, params, tags, tasklet):
    doc = args.doc
    id = args.getTag('id')
    gid = args.getTag('gid')
    width = args.getTag('width')
    height = args.getTag('height')
    result = "{{jgauge width:%(width)s id:%(id)s height:%(height)s val:%(running)s start:0 end:%(total)s}}"
    ac = j.core.osis.getClientForCategory(j.core.portal.active.osis, 'cloudbroker', 'vmachine')
    query = {'status': 'RUNNING'}
    if gid:
      query['gid'] = int(gid)
    total = ac.count({'status':{'$ne': 'DESTROYED'}})
    running = ac.count(query)
    result = result % {'height': height,
                       'width': width,
                       'running': running,
                       'id': id,
                       'total': total}
    params.result = (result, doc)
    return params

def match(j, args, params, tags, tasklet):
    return True
