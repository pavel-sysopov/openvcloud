from JumpScale import j
from JumpScale.portal.portal.auth import auth as audit
from cloudbrokerlib import authenticator
from JumpScale.portal.portal import exceptions
from cloudbrokerlib.baseactor import BaseActor

class cloudapi_images(BaseActor):
    """
    Lists all the images. A image is a template which can be used to deploy machines.

    """
    @audit()
    def list(self, accountId, cloudspaceId, **kwargs):
        """
        List the available images, filtering can be based on the cloudspace and the user which is doing the request
        """
        fields = ['id', 'name','description', 'type', 'UNCPath', 'size', 'username', 'accountId', 'status']
        if accountId:
            q = {'status': 'CREATED', 'accountId': {"$in": [0, int(accountId)]}}
        else:
            q = {'status': 'CREATED', 'accountId': 0}
        query = {'$query': q, '$fields': fields}

        if cloudspaceId:
            cloudspace = self.models.cloudspace.get(int(cloudspaceId))
            if cloudspace:
                stacks = self.models.stack.search({'gid': cloudspace.gid, '$fields': ['images']})[1:]
                imageids = set()
                for stack in stacks:
                    imageids.update(stack['images'])
                if len(imageids) > 0:
                    q['id'] = {'$in': list(imageids)}

        results = self.models.image.search(query)[1:]

        def imagesort(image_a, image_b):
            def getName(image):
                name = "%d %s %s" % (image['accountId'] or 0, image['type'], image['name'])
                return name
            return cmp(getName(image_a), getName(image_b))

        return sorted(results, cmp=imagesort)

    @audit()
    def delete(self, imageId, **kwargs):
        """
        Delete an image

        :param imageId: id of the image to delete
        :return True if image was deleted successfully
        """
        ctx = kwargs['ctx']
        user = ctx.env['beaker.session']['user']
        image = self.models.image.get(imageId)
        if image.accountId <= 0:
            raise exceptions.MethodNotAllowed("Can not delete system images")
        account = self.models.account.get(image.accountId)
        auth = authenticator.auth(acl={'account': set('C')})
        auth.isAuthorized(user, account)
        references = self.models.vmachine.count({'imageId': imageId,
                                                 'status': {'$ne': 'DESTROYED'}})
        if references:
            raise exceptions.Conflict("Can not delete an image which is still used")

        stacks = self.models.stack.search({'images': imageId})[1:]
        gid = None
        if stacks:
            gid = stacks[0]['gid']
        if not gid:
            raise exceptions.Error("Could not find image template")

        acc = j.clients.agentcontroller.get()
        args = {'imageId': image.referenceId}
        job = acc.executeJumpscript('cloudscalers', 'deletetemplate', gid=gid, role='storagenode', args=args)
        if job['state'] != 'OK':
            raise exceptions.Error("Something unexpected went wrong, please try again later")
        elif job['result'] == -1:
            raise exceptions.Conflict("Can not delete an image which is still used")

        self.models.image.delete(imageId)
        return True

