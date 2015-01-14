from JumpScale import j
from cloudbrokerlib.baseactor import BaseActor
import time, string
from random import choice
from libcloud.compute.base import NodeAuthPassword
import JumpScale.grid.osis
from JumpScale.portal.portal.auth import auth
import ujson
import JumpScale.baselib.remote.cuisine
import JumpScale.grid.agentcontroller
import JumpScale.lib.whmcs


class cloudbroker_machine(BaseActor):
    def __init__(self):
        super(cloudbroker_machine, self).__init__()
        self.libvirtcl = j.core.osis.getClientForNamespace('libvirt')
        self.vfwcl = j.core.osis.getClientForNamespace('vfw')
        self.machines_actor = self.cb.actors.cloudapi.machines
        self.portforwarding_actor = self.cb.actors.cloudapi.portforwarding
        self.acl = j.clients.agentcontroller.get()

    @auth(['level1', 'level2', 'level3'])
    def create(self, cloudspaceId, name, description, sizeId, imageId, disksize, **kwargs):
        return self.machines_actor.create(cloudspaceId, name, description, sizeId, imageId, disksize)
    @auth(['level1', 'level2', 'level3'])
    def createOnStack(self, cloudspaceId, name, description, sizeId, imageId, disksize, stackid, **kwargs):
        """
        Create a machine on a specific stackid
        param:cloudspaceId id of space in which we want to create a machine
        param:name name of machine
        param:description optional description
        param:sizeId id of the specific size
        param:imageId id of the specific image
        param:disksize size of base volume
        param:stackid id of the stack
        result bool
        """
        cloudspaceId = int(cloudspaceId)
        imageId = int(imageId)
        sizeId = int(sizeId)
        stackid = int(stackid)
        machine = self.models.vmachine.new()
        image = self.models.image.get(imageId)
        cloudspace = self.models.cloudspace.get(cloudspaceId)

        networkid = cloudspace.networkId
        machine.cloudspaceId = cloudspaceId
        machine.descr = description
        machine.name = name
        machine.sizeId = sizeId
        machine.imageId = imageId
        machine.creationTime = int(time.time())

        disk = self.models.disk.new()
        disk.name = '%s_1'
        disk.descr = 'Machine boot disk'
        disk.sizeMax = disksize
        diskid = self.models.disk.set(disk)[0]
        machine.disks.append(diskid)

        account = machine.new_account()
        if hasattr(image, 'username') and image.username:
            account.login = image.username
        else:
            account.login = 'cloudscalers'
        length = 6
        chars = string.letters + string.digits
        letters = ['abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ']
        passwd = ''.join(choice(chars) for _ in xrange(length))
        passwd = passwd + choice(string.digits) + choice(letters[0]) + choice(letters[1])
        account.password = passwd
        auth = NodeAuthPassword(passwd)
        machine.id = self.models.vmachine.set(machine)[0]

        try:
            provider = self.cb.getProviderByStackId(stackid)
            psize = self._getSize(provider, machine)
            image, pimage = provider.getImage(machine.imageId)
            if not image or not pimage:
                j.events.opserror_critical("Stack %s does not contain image %s" % (stackid, machine.imageId))
            machine.cpus = psize.vcpus if hasattr(psize, 'vcpus') else None
            name = 'vm-%s' % machine.id
        except:
            self.models.vmachine.delete(machine.id)
            raise
        node = provider.client.create_node(name=name, image=pimage, size=psize, auth=auth, networkid=networkid)
        if node == -1:
            raise
        self._updateMachineFromNode(machine, node, stackid, psize)
        return machine.id

    def _getSize(self, provider, machine):
        brokersize = self.models.size.get(machine.sizeId)
        firstdisk = self.models.disk.get(machine.disks[0])
        return provider.getSize(brokersize, firstdisk)

    def _updateMachineFromNode(self, machine, node, stackId, psize):
        machine.referenceId = node.id
        machine.referenceSizeId = psize.id
        machine.stackId = stackId
        machine.status = 'RUNNING'
        machine.hostName = node.name
        for ipaddress in node.public_ips:
            nic = machine.new_nic()
            nic.ipAddress = ipaddress
        self.models.vmachine.set(machine)

        cloudspace = self.models.cloudspace.get(machine.cloudspaceId)
        providerstacks = set(cloudspace.resourceProviderStacks)
        providerstacks.add(stackId)
        cloudspace.resourceProviderStacks = list(providerstacks)
        self.models.cloudspace.set(cloudspace)

    @auth(['level1', 'level2', 'level3'])
    def destroy(self, accountName, spaceName, machineId, reason, **kwargs):
        machineId = int(machineId)
        if not self.models.vmachine.exists(machineId):
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('404', headers)
            return 'Machine ID %s was not found' % machineId

        vmachine = self.models.vmachine.get(machineId)
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        if not cloudspace.name == spaceName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's cloudspace %s does not match the given space name %s" % (cloudspace.name, spaceName)

        account = self.models.account.get(cloudspace.accountId)
        if not account.name == accountName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's account %s does not match the given account name %s" % (account.name, accountName)

        self.machines_actor.delete(vmachine.id)
        return True

    @auth(['level1', 'level2', 'level3'])
    def start(self, accountName, spaceName, machineId, reason, **kwargs):
        machineId = int(machineId)
        if not self.models.vmachine.exists(machineId):
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('404', headers)
            return 'Machine ID %s was not found' % machineId

        vmachine = self.models.vmachine.get(machineId)
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        if not cloudspace.name == spaceName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's cloudspace %s does not match the given space name %s" % (cloudspace.name, spaceName)

        account = self.models.account.get(cloudspace.accountId)
        if not account.name == accountName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's account %s does not match the given account name %s" % (account.name, accountName)

        msg = 'Account: %s\nSpace: %s\nMachine: %s\nReason: %s' % (accountName, spaceName, vmachine.name, reason)
        subject = 'Starting machine: %s' % vmachine.name
        ticketId = j.tools.whmcs.tickets.create_ticket(subject, msg, 'High')
        self.machines_actor.start(machineId)
        j.tools.whmcs.tickets.close_ticket(ticketId)

    @auth(['level1', 'level2', 'level3'])
    def stop(self, accountName, spaceName, machineId, reason, **kwargs):
        machineId = int(machineId)
        if not self.models.vmachine.exists(machineId):
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('404', headers)
            return 'Machine ID %s was not found' % machineId

        vmachine = self.models.vmachine.get(machineId)
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        if not cloudspace.name == spaceName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's cloudspace %s does not match the given space name %s" % (cloudspace.name, spaceName)

        account = self.models.account.get(cloudspace.accountId)
        if not account.name == accountName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's account %s does not match the given account name %s" % (account.name, accountName)

        msg = 'Account: %s\nSpace: %s\nMachine: %s\nReason: %s' % (accountName, spaceName, vmachine.name, reason)
        subject = 'Stopping machine: %s' % vmachine.name
        ticketId = j.tools.whmcs.tickets.create_ticket(subject, msg, 'High')
        self.machines_actor.stop(machineId)
        j.tools.whmcs.tickets.close_ticket(ticketId)

    @auth(['level1', 'level2', 'level3'])
    def pause(self, accountName, spaceName, machineId, reason, **kwargs):
        machineId = int(machineId)
        if not self.models.vmachine.exists(machineId):
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('404', headers)
            return 'Machine ID %s was not found' % machineId

        vmachine = self.models.vmachine.get(machineId)
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        if not cloudspace.name == spaceName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's cloudspace %s does not match the given space name %s" % (cloudspace.name, spaceName)

        account = self.models.account.get(cloudspace.accountId)
        if not account.name == accountName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's account %s does not match the given account name %s" % (account.name, accountName)

        msg = 'Account: %s\nSpace: %s\nMachine: %s\nReason: %s' % (accountName, spaceName, vmachine.name, reason)
        subject = 'Pausing machine: %s' % vmachine.name
        ticketId = j.tools.whmcs.tickets.create_ticket(subject, msg, 'High')
        self.machines_actor.pause(machineId)
        j.tools.whmcs.tickets.close_ticket(ticketId)

    @auth(['level1', 'level2', 'level3'])
    def resume(self, accountName, spaceName, machineId, reason, **kwargs):
        machineId = int(machineId)
        if not self.models.vmachine.exists(machineId):
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('404', headers)
            return 'Machine ID %s was not found' % machineId

        vmachine = self.models.vmachine.get(machineId)
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        if not cloudspace.name == spaceName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's cloudspace %s does not match the given space name %s" % (cloudspace.name, spaceName)

        account = self.models.account.get(cloudspace.accountId)
        if not account.name == accountName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's account %s does not match the given account name %s" % (account.name, accountName)

        msg = 'Account: %s\nSpace: %s\nMachine: %s\nReason: %s' % (accountName, spaceName, vmachine.name, reason)
        subject = 'Resuming machine: %s' % vmachine.name
        ticketId = j.tools.whmcs.tickets.create_ticket(subject, msg, 'High')
        self.machines_actor.resume(machineId)
        j.tools.whmcs.tickets.close_ticket(ticketId)

    @auth(['level1', 'level2', 'level3'])
    def reboot(self, accountName, spaceName, machineId, reason, **kwargs):
        machineId = int(machineId)
        if not self.models.vmachine.exists(machineId):
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('404', headers)
            return 'Machine ID %s was not found' % machineId

        vmachine = self.models.vmachine.get(machineId)
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        if not cloudspace.name == spaceName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's cloudspace %s does not match the given space name %s" % (cloudspace.name, spaceName)

        account = self.models.account.get(cloudspace.accountId)
        if not account.name == accountName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's account %s does not match the given account name %s" % (account.name, accountName)

        msg = 'Account: %s\nSpace: %s\nMachine: %s\nReason: %s' % (accountName, spaceName, vmachine.name, reason)
        subject = 'Rebooting machine: %s' % vmachine.name
        ticketId = j.tools.whmcs.tickets.create_ticket(subject, msg, 'High')
        self.machines_actor.reboot(machineId)
        j.tools.whmcs.tickets.close_ticket(ticketId)

    @auth(['level1', 'level2', 'level3'])
    def snapshot(self, accountName, spaceName, machineId, snapshotName, reason, **kwargs):
        machineId = int(machineId)
        if not self.models.vmachine.exists(machineId):
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('404', headers)
            return 'Machine ID %s was not found' % machineId

        vmachine = self.models.vmachine.get(machineId)
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        if not cloudspace.name == spaceName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's cloudspace %s does not match the given space name %s" % (cloudspace.name, spaceName)

        account = self.models.account.get(cloudspace.accountId)
        if not account.name == accountName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's account %s does not match the given account name %s" % (account.name, accountName)

        msg = 'Account: %s\nSpace: %s\nMachine: %s\nSnapshot name: %s\nReason: %s' % (accountName, spaceName, vmachine.name, snapshotName, reason)
        subject = 'Snapshotting machine: %s' % vmachine.name
        ticketId = j.tools.whmcs.tickets.create_ticket(subject, msg, 'High')
        self.machines_actor.snapshot(machineId, snapshotName)
        j.tools.whmcs.tickets.close_ticket(ticketId)

    @auth(['level1', 'level2', 'level3'])
    def rollbackSnapshot(self, accountName, spaceName, machineId, snapshotName, reason, **kwargs):
        machineId = int(machineId)
        if not self.models.vmachine.exists(machineId):
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('404', headers)
            return 'Machine ID %s was not found' % machineId

        vmachine = self.models.vmachine.get(machineId)
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        if not cloudspace.name == spaceName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's cloudspace %s does not match the given space name %s" % (cloudspace.name, spaceName)

        account = self.models.account.get(cloudspace.accountId)
        if not account.name == accountName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's account %s does not match the given account name %s" % (account.name, accountName)

        msg = 'Account: %s\nSpace: %s\nMachine: %s\nSnapshot name: %s\nReason: %s' % (accountName, spaceName, vmachine.name, snapshotName, reason)
        subject = 'Rolling back snapshot: %s of machine: %s' % (snapshotName, vmachine.name)
        ticketId = j.tools.whmcs.tickets.create_ticket(subject, msg, 'High')
        self.machines_actor.rollbackSnapshot(machineId, snapshotName)
        j.tools.whmcs.tickets.close_ticket(ticketId)

    @auth(['level1', 'level2', 'level3'])
    def deleteSnapshot(self, accountName, spaceName, machineId, snapshotName, reason, **kwargs):
        machineId = int(machineId)
        if not self.models.vmachine.exists(machineId):
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('404', headers)
            return 'Machine ID %s was not found' % machineId

        vmachine = self.models.vmachine.get(machineId)
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        if not cloudspace.name == spaceName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's cloudspace %s does not match the given space name %s" % (cloudspace.name, spaceName)

        account = self.models.account.get(cloudspace.accountId)
        if not account.name == accountName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's account %s does not match the given account name %s" % (account.name, accountName)

        msg = 'Account: %s\nSpace: %s\nMachine: %s\nSnapshot name: %s\nReason: %s' % (accountName, spaceName, vmachine.name, snapshotName, reason)
        subject = 'Deleting snapshot: %s of machine: %s' % (snapshotName, vmachine.name)
        ticketId = j.tools.whmcs.tickets.create_ticket(subject, msg, 'High')
        self.machines_actor.deleteSnapshot(machineId, snapshotName)
        j.tools.whmcs.tickets.close_ticket(ticketId)

    @auth(['level1', 'level2', 'level3'])
    def clone(self, accountName, spaceName, machineId, cloneName, reason, **kwargs):
        machineId = int(machineId)
        if not self.models.vmachine.exists(machineId):
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('404', headers)
            return 'Machine ID %s was not found' % machineId

        vmachine = self.models.vmachine.get(machineId)
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        if not cloudspace.name == spaceName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's cloudspace %s does not match the given space name %s" % (cloudspace.name, spaceName)

        account = self.models.account.get(cloudspace.accountId)
        if not account.name == accountName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's account %s does not match the given account name %s" % (account.name, accountName)

        msg = 'Account: %s\nSpace: %s\nMachine: %s\nClone name: %s\nReason: %s' % (accountName, spaceName, vmachine.name, cloneName, reason)
        subject = 'Cloning machine: %s into machine: %s' % (vmachine.name, cloneName)
        ticketId = j.tools.whmcs.tickets.create_ticket(subject, msg, 'High')
        self.machines_actor.clone(machineId, cloneName)
        j.tools.whmcs.tickets.close_ticket(ticketId)

    @auth(['level1', 'level2', 'level3'])
    def moveToDifferentComputeNode(self, accountName, machineId, reason, targetStackId=None, withSnapshots=True, collapseSnapshots=False, **kwargs):
        machineId = int(machineId)
        ctx = kwargs['ctx']
        headers = [('Content-Type', 'application/json'), ]
        if not self.models.vmachine.exists(machineId):
            ctx.start_response('404', headers)
            return 'Machine ID %s was not found' % machineId

        vmachine = self.models.vmachine.get(machineId)
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        account = self.models.account.get(cloudspace.accountId)
        source_stack = self.models.stack.get(vmachine.stackId)
        if account.name != accountName:
            ctx.start_response('400', headers)
            return "Machine's account %s does not match the given account name %s" % (account.name, accountName)

        if targetStackId:
            target_stack = self.models.stack.get(int(targetStackId))
            if target_stack.gid != source_stack.gid:
                ctx.start_response('400', headers)
                return 'Target stack %(name)s is not on some grid as source' % target_stack

        else:
            target_stack = self.cb.getBestProvider(cloudspace.gid, vmachine.imageId)


        # validate machine template is on target node
        image = self.models.image.get(vmachine.imageId)
        libvirt_image = self.libvirtcl.image.get(image.referenceId)
        image_path = j.system.fs.joinPaths('/mnt', 'vmstor', 'templates', libvirt_image.UNCPath)

        srcmd5 = self.acl.executeJumpscript('cloudscalers', 'getmd5', args={'filepath': image_path}, gid=source_stack.gid, nid=int(source_stack.referenceId), wait=True)['result']
        destmd5 = self.acl.executeJumpscript('cloudscalers', 'getmd5', args={'filepath': image_path}, gid=target_stack.gid, nid=int(target_stack.referenceId), wait=True)['result']
        if srcmd5 != destmd5:
            ctx.start_response('400', headers)
            return "Image's MD5sum on target node doesn't match machine base image MD5sum"

        # create network on target node
        self.acl.executeJumpscript('cloudscalers', 'createnetwork', args={'networkid': cloudspace.networkId}, gid=target_stack.gid, nid=int(target_stack.referenceId), wait=True)

        # get disks info on source node
        disks_info = self.acl.executeJumpscript('cloudscalers', 'vm_livemigrate_getdisksinfo', args={'vmId': vmachine.id}, gid=source_stack.gid, nid=int(source_stack.referenceId), wait=True)['result']

        # create disks on target node
        snapshots = []
        if j.basetype.boolean.fromString(withSnapshots):
            snapshots = self.machines_actor.listSnapshots(vmachine.id)
        sshkey = None
        sshpath = j.system.fs.joinPaths(j.dirs.cfgDir, 'id_rsa')
        if j.system.fs.exists(sshpath):
            sshkey = j.system.fs.fileGetContents(sshpath)
        args = {'vm_id': vmachine.id,
                'disks_info': disks_info,
                'source_stack': source_stack.dump(),
                'target_stack': target_stack.dump(),
                'sshkey': sshkey,
                'snapshots': snapshots}
        job = self.acl.executeJumpscript('cloudscalers', 'vm_livemigrate', args=args, gid=target_stack.gid, nid=int(target_stack.referenceId), wait=True)
        if job['state'] != 'OK':
            ctx.start_response('500', headers)
            return "Migrate failed: %s" % (job['result'])

        vmachine.stackId = target_stack.id 
        self.models.vmachine.set(vmachine)

    @auth(['level1', 'level2', 'level3'])
    def export(self, machineId, name, backuptype, storage, host, aws_access_key, aws_secret_key, bucketname, **kwargs):
        machineId = int(machineId)
        ctx = kwargs['ctx']
        headers = [('Content-Type', 'application/json'), ]
        machine = self.models.vmachine.get(machineId)
        if not machine:
            ctx.start_response('400', headers)
            return 'Machine %s not found' % machineId
        stack = self.models.stack.get(machine.stackId)
        storageparameters  = {}
        if storage == 'S3':
            if not aws_access_key or not aws_secret_key or not host:
                  ctx.start_response('400', headers)
                  return 'S3 parameters are not provided'
            storageparameters['aws_access_key'] = aws_access_key
            storageparameters['aws_secret_key'] = aws_secret_key
            storageparameters['host'] = host
            storageparameters['is_secure'] = True

        storageparameters['storage_type'] = storage
        storageparameters['backup_type'] = backuptype
        storageparameters['bucket'] = bucketname
        storageparameters['mdbucketname'] = bucketname

        storagepath = '/mnt/vmstor/vm-%s' % machineId
        nid = int(stack.referenceId)
        gid = stack.gid
        args = {'path':storagepath, 'name':name, 'machineId':machineId, 'storageparameters': storageparameters,'nid':nid, 'backup_type':backuptype}
        guid = self.acl.executeJumpscript('cloudscalers', 'cloudbroker_export', j.application.whoAmI.nid, gid=gid, args=args, wait=False)['guid']
        return guid

    @auth(['level1', 'level2', 'level3'])
    def restore(self, vmexportId, nid, destinationpath, aws_access_key, aws_secret_key, **kwargs):
        vmexportId = int(vmexportId)
        nid = int(nid)
        ctx = kwargs['ctx']
        headers = [('Content-Type', 'application/json'), ]
        vmexport = self.models.vmexport.get(vmexportId)
        if not vmexport:
            ctx.start_response('400', headers)
            return 'Export definition with id %s not found' % vmexportId
        storageparameters = {}

        if vmexport.storagetype == 'S3':
            if not aws_access_key or not aws_secret_key:
                ctx.start_response('400', headers)
                return 'S3 parameters are not provided'
            storageparameters['aws_access_key'] = aws_access_key
            storageparameters['aws_secret_key'] = aws_secret_key
            storageparameters['host'] = vmexport.server
            storageparameters['is_secure'] = True

        storageparameters['storage_type'] = vmexport.storagetype
        storageparameters['bucket'] = vmexport.bucket
        storageparameters['mdbucketname'] = vmexport.bucket


        metadata = ujson.loads(vmexport.files)

        args = {'path':destinationpath, 'metadata':metadata, 'storageparameters': storageparameters,'nid':nid}

        id = self.acl.executeJumpscript('cloudscalers', 'cloudbroker_import', j.application.whoAmI.nid, args=args, wait=False)['result']
        return id

    @auth(['level1', 'level2', 'level3'])
    def listExports(self, status, machineId ,**kwargs):
        machineId = int(machineId)
        query = {'status': status, 'machineId': machineId}
        exports = self.models.vmexport.search(query)[1:]
        exportresult = []
        for exp in exports:
            exportresult.append({'status':exp['status'], 'type':exp['type'], 'storagetype':exp['storagetype'], 'machineId': exp['machineId'], 'id':exp['id'], 'name':exp['name'],'timestamp':exp['timestamp']})
        return exportresult

    @auth(['level1', 'level2', 'level3'])
    def tag(self, machineId, tagName, **kwargs):
        """
        Adds a tag to a machine, useful for indexing and following a (set of) machines
        param:machineId id of the machine to tag
        param:tagName tag
        """
        machineId = int(machineId)
        if not self.models.vmachine.exists(machineId):
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('404', headers)
            return 'vMachine ID %s was not found' % machineId

        vmachine = self.models.vmachine.get(machineId)
        tags = j.core.tags.getObject(vmachine.tags)
        if tags.labelExists(tagName):
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return 'Tag %s is already assigned to this vMachine' % tagName

        tags.labelSet(tagName)
        vmachine.tags = tags.tagstring
        self.models.vmachine.set(vmachine)
        return True

    @auth(['level1', 'level2', 'level3'])
    def untag(self, machineId, tagName, **kwargs):
        """
        Removes a specific tag from a machine
        param:machineId id of the machine to untag
        param:tagName tag
        """
        machineId = int(machineId)
        if not self.models.vmachine.exists(machineId):
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('404', headers)
            return 'vMachine ID %s was not found' % machineId

        vmachine = self.models.vmachine.get(machineId)
        tags = j.core.tags.getObject(vmachine.tags)
        if not tags.labelExists(tagName):
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return 'vMachine does not have tag %s' % tagName

        tags.labelDelete(tagName)
        vmachine.tags = tags.tagstring
        self.models.vmachine.set(vmachine)
        return True

    @auth(['level1', 'level2', 'level3'])
    def list(self, tag=None, computeNode=None, accountName=None, cloudspaceId=None, **kwargs):
        """
        List the undestroyed machines based on specific criteria
        At least one of the criteria needs to be passed
        param:tag a specific tag
        param:computenode name of a specific computenode
        param:accountname specific account
        param:cloudspaceId specific cloudspace
        """
        if not tag and not computeNode and not accountName and not cloudspaceId:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return 'At least one parameter must be passed'
        query = dict()
        if tag:
            query['tags'] = tag
        if computeNode:
            stacks = self.models.stack.search({'referenceId': computeNode})[1:]
            if stacks:
                stack_id = stacks[0]['id']
                query['stackId'] = stack_id
            else:
                return list()
        if accountName:
            accounts = self.models.account.search({'name': accountName})[1:]
            if accounts:
                account_id = accounts[0]['id']
                cloudspaces = self.models.cloudspace.search({'accountId': account_id})[1:]
                if cloudspaces:
                    cloudspaces_ids = [cs['id'] for cs in cloudspaces]
                    query['cloudspaceId'] = {'$in': cloudspaces_ids}
                else:
                    return list()
            else:
                return list()
        if cloudspaceId:
            query['cloudspaceId'] = cloudspaceId

        query['status'] = {'$ne': 'destroyed'}
        return self.models.vmachine.search(query)[1:]

    @auth(['level1', 'level2', 'level3'])
    def checkImageChain(self, machineId, **kwargs):
        """
        Checks on the computenode the vm is on if the vm image is there
        Check the chain of the vmimage to see if parents are there (the template starting from)
        (executes the vm.hdcheck jumpscript)
        param:machineId id of the machine
        result dict,,
        """
        #put your code here to implement this method
        vmachine = self.models.vmachine.get(int(machineId))
        stack = self.models.stack.get(vmachine.stackId)
        job = self.acl.executeJumpscript('cloudscalers', 'vm_livemigrate_getdisksinfo', args={'vmId': vmachine.id, 'chain': True}, gid=stack.gid, nid=int(stack.referenceId), wait=True)
        if job['state'] != 'OK':
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('500', headers)
            return 'Something wrong with image or node see job %s' % job['guid']
        return job['result']


    @auth(['level1', 'level2', 'level3'])
    def stopForAbusiveResourceUsage(self, accountName, machineId, reason, **kwargs):
        '''If a machine is abusing the system and violating the usage policies it can be stopped using this procedure.
        A ticket will be created for follow up and visibility, the machine stopped, the image put on slower storage and the ticket is automatically closed if all went well.
        Use with caution!
        @param:accountName str,,Account name, extra validation for preventing a wrong machineId
        @param:machineId int,,Id of the machine
        @param:reason str,,Reason
        '''
        machineId = int(machineId)
        if not self.models.vmachine.exists(machineId):
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('404', headers)
            return 'Machine ID %s was not found' % machineId
        vmachine = self.models.vmachine.get(machineId)
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        account = self.models.account.get(cloudspace.accountId)
        if not account.name == accountName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's account %s does not match the given account name %s" % (account.name, accountName)

        stack = self.models.stack.get(vmachine.stackId)
        subject = 'Stopping vmachine "%s" for abusive resources usage' % vmachine.name
        msg = 'Account: %s\nMachine: %s\nReason: %s' % (accountName, vmachine.name, reason)
        ticketId = j.tools.whmcs.tickets.create_ticket(subject, msg, "High")
        args = {'machineId': vmachine.id, 'nodeId': vmachine.referenceId}
        self.acl.executeJumpscript('cloudscalers', 'vm_stop_for_abusive_usage', gid=stack.gid, nid=stack.referenceId, args=args, wait=False)
        j.tools.whmcs.tickets.close_ticket(ticketId)

    @auth(['level1', 'level2', 'level3'])
    def backupAndDestroy(self, accountName, machineId, reason, **kwargs):
        """
        * Create a ticketjob
        * Call the backup method
        * Destroy the machine
        * Close the ticket
        """
        machineId = int(machineId)
        if not self.models.vmachine.exists(machineId):
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('404', headers)
            return 'Machine ID %s was not found' % machineId
        vmachine = self.models.vmachine.get(machineId)
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        account = self.models.account.get(cloudspace.accountId)
        if not account.name == accountName:
            ctx = kwargs['ctx']
            headers = [('Content-Type', 'application/json'), ]
            ctx.start_response('400', headers)
            return "Machine's account %s does not match the given account name %s" % (account.name, accountName)
        stack = self.models.stack.get(vmachine.stackId)
        args = {'accountName': accountName, 'machineId': machineId, 'reason': reason, 'vmachineName': vmachine.name, 'cloudspaceId': vmachine.cloudspaceId}
        self.acl.executeJumpscript('cloudscalers', 'vm_backup_destroy', gid=j.application.whoAmI.gid, nid=j.application.whoAmI.nid, args=args, wait=False)

    @auth(['level1', 'level2', 'level3'])
    def listSnapshots(self, machineId, **kwargs):
        ctx = kwargs.get('ctx')
        headers = [('Content-Type', 'application/json'), ]
        machineId = int(machineId)
        if not self.models.vmachine.exists(machineId):
            if ctx:
                ctx.start_response('400', headers)
            return 'Machine %s not found' % machineId
        vmachine = self.models.vmachine.get(machineId)
        if vmachine.status=='DESTROYED' or not vmachine.status:
            if ctx:
                ctx.start_response('400', headers)
            return 'Machine %s is invalid' % machineId
        return self.machines_actor.listSnapshots(machineId)

    @auth(['level1', 'level2', 'level3'])
    def getHistory(self, machineId, **kwargs):
        ctx = kwargs.get('ctx')
        headers = [('Content-Type', 'application/json'), ]
        machineId = int(machineId)
        if not self.models.vmachine.exists(machineId):
            if ctx:
                ctx.start_response('400', headers)
            return 'Machine %s not found' % machineId
        vmachine = self.models.vmachine.get(machineId)
        if vmachine.status=='DESTROYED' or not vmachine.status:
            if ctx:
                ctx.start_response('400', headers)
            return 'Machine %s is invalid' % machineId
        return self.machines_actor.getHistory(machineId)

    @auth(['level1', 'level2', 'level3'])
    def listPortForwards(self, machineId, **kwargs):
        ctx = kwargs.get('ctx')
        headers = [('Content-Type', 'application/json'), ]
        machineId = int(machineId)
        if not self.models.vmachine.exists(machineId):
            if ctx:
                ctx.start_response('400', headers)
            return 'Machine %s not found' % machineId
        vmachine = self.models.vmachine.get(machineId)
        if vmachine.status=='DESTROYED' or not vmachine.status:
            if ctx:
                ctx.start_response('400', headers)
            return 'Machine %s is invalid' % machineId
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        vfwkey = "%s_%s" % (cloudspace.gid, cloudspace.networkId)
        results = list()
        machineips = [nic.ipAddress for nic in vmachine.nics if not nic.ipAddress=='Undefined']
        if self.vfwcl.virtualfirewall.exists(vfwkey):
            vfw = self.vfwcl.virtualfirewall.get(vfwkey).dump()
            for forward in vfw['tcpForwardRules']:
                if forward['toAddr'] in machineips:
                    results.append(forward)
        return results

    @auth(['level1', 'level2', 'level3'])
    def createPortForward(self, machineId, spaceName, localPort, destPort, proto, reason, **kwargs):
        machineId = int(machineId)
        ctx = kwargs['ctx']
        headers = [('Content-Type', 'application/json'), ]
        if not self.models.vmachine.exists(machineId):
            ctx.start_response('404', headers)
            return 'Machine ID %s was not found' % machineId
        vmachine = self.models.vmachine.get(machineId)
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        if spaceName != cloudspace.name:
            ctx.start_response('400', headers)
            return "Machine's cloud space %s does not match the given cloud space name %s" % (cloudspace.name, spaceName)
        account = self.models.account.get(cloudspace.accountId)
        msg = 'Account: %s\nSpace: %s\nMachine: %s\nPort forwarding: %s -> %s:%s\nReason: %s' % (account.name, spaceName, vmachine.name, localPort, cloudspace.publicipaddress, destPort, reason)
        subject = 'Creating portforwarding rule for machine %s: %s -> %s:%s' % (vmachine.name, localPort, cloudspace.publicipaddress, destPort)
        ticketId = j.tools.whmcs.tickets.create_ticket(subject, msg, 'High')
        self.portforwarding_actor.create(cloudspace.id, cloudspace.publicipaddress, str(destPort), vmachine.id, str(localPort), proto)
        j.tools.whmcs.tickets.close_ticket(ticketId)

    @auth(['level1', 'level2', 'level3'])
    def deletePortForward(self, machineId, spaceName, ruleId, reason, **kwargs):
        machineId = int(machineId)
        ctx = kwargs['ctx']
        headers = [('Content-Type', 'application/json'), ]
        if not self.models.vmachine.exists(machineId):
            ctx.start_response('404', headers)
            return 'Machine ID %s was not found' % machineId
        vmachine = self.models.vmachine.get(machineId)
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        if spaceName != cloudspace.name:
            ctx.start_response('400', headers)
            return "Machine's cloud space %s does not match the given cloud space name %s" % (cloudspace.name, spaceName)
        account = self.models.account.get(cloudspace.accountId)
        msg = 'Account: %s\nSpace: %s\nMachine: %s\nDeleting Portforward ID: %s\nReason: %s' % (account.name, spaceName, vmachine.name, ruleId, reason)
        subject = 'Deleting portforwarding rule ID: %s for machine %s' % (ruleId, vmachine.name)
        ticketId = j.tools.whmcs.tickets.create_ticket(subject, msg, 'High')
        self.portforwarding_actor.delete(cloudspace.id, ruleId)
        j.tools.whmcs.tickets.close_ticket(ticketId)

    @auth(['level1', 'level2', 'level3'])
    def addDisk(self, machineId, spaceName, diskName, description, reason, size=10, type='D', **kwargs):
        machineId = int(machineId)
        ctx = kwargs['ctx']
        headers = [('Content-Type', 'application/json'), ]
        if not self.models.vmachine.exists(machineId):
            ctx.start_response('404', headers)
            return 'Machine ID %s was not found' % machineId
        vmachine = self.models.vmachine.get(machineId)
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        if spaceName != cloudspace.name:
            ctx.start_response('400', headers)
            return "Machine's cloud space %s does not match the given cloud space name %s" % (cloudspace.name, spaceName)
        account = self.models.account.get(cloudspace.accountId)
        msg = 'Account: %s\nSpace: %s\nMachine: %s\nAdding disk: %s\nReason: %s' % (account.name, spaceName, vmachine.name, diskName, reason)
        subject = 'Adding disk: %s for machine %s' % (diskName, vmachine.name)
        ticketId = j.tools.whmcs.tickets.create_ticket(subject, msg, 'High')
        self.machines_actor.addDisk(machineId, diskName, description, size=size, type=type)
        j.tools.whmcs.tickets.close_ticket(ticketId)

    @auth(['level1', 'level2', 'level3'])
    def deleteDisk(self, machineId, spaceName, diskId, reason, **kwargs):
        machineId = int(machineId)
        ctx = kwargs['ctx']
        headers = [('Content-Type', 'application/json'), ]
        if not self.models.vmachine.exists(machineId):
            ctx.start_response('404', headers)
            return 'Machine ID %s was not found' % machineId
        vmachine = self.models.vmachine.get(machineId)
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        if spaceName != cloudspace.name:
            ctx.start_response('400', headers)
            return "Machine's cloud space %s does not match the given cloud space name %s" % (cloudspace.name, spaceName)
        account = self.models.account.get(cloudspace.accountId)
        msg = 'Account: %s\nSpace: %s\nMachine: %s\nDeleting disk: %s\nReason: %s' % (account.name, spaceName, vmachine.name, diskId, reason)
        subject = 'Deleting disk: %s for machine %s' % (diskId, vmachine.name)
        ticketId = j.tools.whmcs.tickets.create_ticket(subject, msg, 'High')
        self.machines_actor.delDisk(machineId, diskId)
        j.tools.whmcs.tickets.close_ticket(ticketId)

    @auth(['level1', 'level2', 'level3'])
    def createTemplate(self, machineId, spaceName, templateName, reason, **kwargs):
        machineId = int(machineId)
        ctx = kwargs['ctx']
        headers = [('Content-Type', 'application/json'), ]
        if not self.models.vmachine.exists(machineId):
            ctx.start_response('404', headers)
            return 'Machine ID %s was not found' % machineId
        vmachine = self.models.vmachine.get(machineId)
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        if spaceName != cloudspace.name:
            ctx.start_response('400', headers)
            return "Machine's cloud space %s does not match the given cloud space name %s" % (cloudspace.name, spaceName)
        account = self.models.account.get(cloudspace.accountId)
        msg = 'Account: %s\nSpace: %s\nMachine: %s\nCreating template: %s\nReason: %s' % (account.name, spaceName, vmachine.name, templateName, reason)
        subject = 'Creating template: %s for machine %s' % (templateName, vmachine.name)
        ticketId = j.tools.whmcs.tickets.create_ticket(subject, msg, 'High')
        self.machines_actor.createTemplate(machineId, templateName, None)
        j.tools.whmcs.tickets.close_ticket(ticketId)

    @auth(['level1', 'level2', 'level3'])
    def updateMachine(self, machineId, spaceName, description, reason, **kwargs):
        machineId = int(machineId)
        ctx = kwargs['ctx']
        headers = [('Content-Type', 'application/json'), ]
        if not self.models.vmachine.exists(machineId):
            ctx.start_response('404', headers)
            return 'Machine ID %s was not found' % machineId
        vmachine = self.models.vmachine.get(machineId)
        cloudspace = self.models.cloudspace.get(vmachine.cloudspaceId)
        if spaceName != cloudspace.name:
            ctx.start_response('400', headers)
            return "Machine's cloud space %s does not match the given cloud space name %s" % (cloudspace.name, spaceName)
        account = self.models.account.get(cloudspace.accountId)
        msg = 'Account: %s\nSpace: %s\nMachine: %s\nUpdating machine description: %s\nReason: %s' % (account.name, spaceName, vmachine.name, description, reason)
        subject = 'Updating description: %s for machine %s' % (description, vmachine.name)
        ticketId = j.tools.whmcs.tickets.create_ticket(subject, msg, 'High')
        self.machines_actor.update(machineId, description=description)
        j.tools.whmcs.tickets.close_ticket(ticketId)
