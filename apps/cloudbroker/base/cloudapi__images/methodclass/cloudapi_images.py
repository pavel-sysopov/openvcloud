from JumpScale import j
from JumpScale.portal.portal.auth import auth as audit
from cloudbrokerlib.baseactor import BaseActor

class cloudapi_images(BaseActor):
    """
    Lists all the images. A image is a template which can be used to deploy machines.

    """
    @audit()
    def list(self, accountid, cloudspaceid, **kwargs):
        """
        List the availabe images, filtering can be based on the cloudspace and the user which is doing the request
        """
        fields = ['id', 'name','description', 'type', 'UNCPath', 'size', 'username', 'accountId', 'status']
        if accountid:
            q = {'status': 'CREATED', 'accountId': {"$in": [0, int(accountid)]}}
        else:
            q = {'status': 'CREATED', 'accountId': 0}
        query = {'$query': q, '$fields': fields}

        if cloudspaceid:
            cloudspace = self.models.cloudspace.get(int(cloudspaceid))
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
    def delete(self, imageid, **kwargs):
        """
        Delete a image, you need to have Write access on the image
        param:imageid id of the image to delete
        result
        """
        #put your code here to implement this method
        raise NotImplementedError ("not implemented method delete")

