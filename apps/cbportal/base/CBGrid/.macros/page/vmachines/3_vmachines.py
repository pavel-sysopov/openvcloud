import datetime

def main(j, args, params, tags, tasklet):
    page = args.page
    modifier = j.html.getPageModifierGridDataTables(page)
    stackid = args.getTag("stackid")
    cloudspaceId = args.getTag("cloudspaceid")
    imageid = args.getTag('imageid')
    gid = args.getTag('gid')
    filters = dict()
    filters['status'] = ['RUNNING','HALTED','PAUSED']
    ccl = j.core.osis.getClientForNamespace('cloudbroker')

    if stackid:
        stackid = int(stackid)
        filters['stackId'] = stackid
    if cloudspaceId:
        filters['cloudspaceId'] = int(cloudspaceId)
    if imageid:
        imageid = str(imageid)
        images = ccl.image.search({'referenceId': imageid})[1:]
        if images:
            filters['imageId'] = images[0]['id']
    if gid:
        gid = int(gid)
        stacks = ccl.stack.simpleSearch({'gid':gid})
        stacksids = [ stack['id'] for stack in stacks ]
        filters['stackId'] = stacksids

    fieldnames = ['Name', 'Status', 'Host Name', 'Created at', 'Cloud Space', 'Stack']

    def stackLinkify(row, field):
        return '[%s|stack?id=%s]' % (row[field], row[field])

    def nameLinkify(row, field):
        return '[%s|vmachine?id=%s]' % (row[field], row['id'])

    def spaceLinkify(row, field):
        return '[%s|cloudspace?id=%s]' % (row[field], row[field])

    fieldids = ['name', 'status', 'hostName', 'creationTime', 'cloudspaceId', 'stackId']
    fieldvalues = [nameLinkify, 'status', 'hostName', modifier.makeTime, spaceLinkify, stackLinkify]
    tableid = modifier.addTableForModel('cloudbroker', 'vmachine', fieldids, fieldnames, fieldvalues, filters)
    modifier.addSearchOptions('#%s' % tableid)
    modifier.addSorting('#%s' % tableid, 0, 'desc')

    params.result = page

    return params


def match(j, args, params, tags, tasklet):
    return True