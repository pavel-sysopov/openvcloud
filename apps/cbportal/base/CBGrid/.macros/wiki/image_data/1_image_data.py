def main(j, args, params, tags, tasklet):
    params.result = (args.doc, args.doc)
    imageid = args.requestContext.params.get('id')
    if not imageid:
        args.doc.applyTemplate({})
        return params
    try:
        imageid = int(imageid)
    except ValueError:
        args.doc.applyTemplate({})
        return params

    ccl = j.clients.osis.getNamespace('cloudbroker')

    if not ccl.image.exists(imageid):
        args.doc.applyTemplate({'imageid': None}, True)
        return params

    imageobj = ccl.image.get(imageid)
    image = imageobj.dump()

    args.doc.applyTemplate(image, True)

    return params


def match(j, args, params, tags, tasklet):
    return True
