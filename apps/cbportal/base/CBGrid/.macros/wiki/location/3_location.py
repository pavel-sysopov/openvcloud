try:
    import ujson as json
except:
    import json

def main(j, args, params, tags, tasklet):

    gid = args.getTag('gid')
    if not gid:
        args.doc.applyTemplate({})
        params.result = (args.doc, args.doc)
        return params

    gid = int(gid)
    cbclient = j.clients.osis.getNamespace('cloudbroker')

    locations = cbclient.location.search({'gid': gid})[1:]
    if not locations:
        params.result = ('Grid with id %s not found' % id, args.doc)
        return params

    obj = locations[0]
    args.doc.applyTemplate(obj, True)
    params.result = (args.doc, args.doc)
    return params

def match(j, args, params, tags, tasklet):
    return True
