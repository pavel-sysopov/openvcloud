
def main(j, args, params, tags, tasklet):
    import JumpScale.baselib.units

    stid = args.getTag('id')
    if not stid:
        out = 'Missing Stack id param "id"'
        params.result = (out, args.doc)
        return params

    stid = int(stid)
    ccl = j.clients.osis.getNamespace('cloudbroker')

    if not ccl.stack.exists(stid):
        params.result = ('Stack with id %s not found' % stid, args.doc)
        return params

    def objFetchManipulate(id):
        stack = ccl.stack.get(stid).dump()
        stack['breadcrumbname'] = stack['name']
        return stack

    push2doc=j.apps.system.contentmanager.extensions.macrohelper.push2doc

    return push2doc(args,params,objFetchManipulate)

def match(j, args, params, tags, tasklet):
    return True
