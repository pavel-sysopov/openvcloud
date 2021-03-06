from JumpScale import j
from libcloud.compute.base import NodeAuthPassword
from JumpScale.portal.portal import exceptions
from CloudscalerLibcloud.compute.drivers.libvirt_driver import CSLibvirtNodeDriver, StorageException, NotEnoughResources, Node, NetworkInterface
from cloudbrokerlib import enums, network
from CloudscalerLibcloud.utils.connection import CloudBrokerConnection
from CloudscalerLibcloud.utils.gridconfig import GridConfig
from .netmgr import NetManager
import random
import time
import string
import re

DEFAULTIOPS = 2000

ujson = j.db.serializers.ujson
models = j.clients.osis.getNamespace('cloudbroker')
_providers = dict()


def removeConfusingChars(input):
    return input.replace('0', '').replace('O', '').replace('l', '').replace('I', '')


class Dummy(object):

    def __init__(self, **kwargs):
        self.extra = {}
        for key, value in kwargs.iteritems():
            setattr(self, key, value)


def CloudProvider(stackId):
    if stackId not in _providers:
        stack = models.stack.get(stackId)
        kwargs = dict()
        kwargs['stack'] = stack
        driver = CSLibvirtNodeDriver(**kwargs)
        client = None
        if 'libcloud__libvirt' not in j.apps.system.contentmanager.getActors():
            client = j.clients.portal.getByInstance('cloudbroker')
        cb = CloudBrokerConnection(client)
        driver.set_backend(cb)
        _providers[stackId] = driver
    return _providers[stackId]




class CloudBroker(object):
    _resourceProviderId2StackId = dict()

    def __init__(self):
        self.Dummy = Dummy
        self._actors = None
        self.syscl = j.clients.osis.getNamespace('system')
        self.cbcl = j.clients.osis.getNamespace('cloudbroker')
        self.vcl = j.clients.osis.getNamespace('vfw')
        self.agentcontroller = j.clients.agentcontroller.get()
        self.machine = Machine(self)
        self.cloudspace = CloudSpace(self)
        self.netmgr = NetManager(self)

    def getImage(self, provider, imageId):
        if imageId not in provider.stack.images:
            provider.stack = self.stack.get(provider.stack.id)
            if imageId not in self.stack.images:
                return None

        return models.image.get(imageId)

    @property
    def actors(self):
        ctx = j.core.portal.active.requestContext
        hrd = j.application.getAppInstanceHRD(name="portal_client", instance='cloudbroker')
        addr = hrd.get('instance.param.addr')
        port = hrd.getInt('instance.param.port')
        cl = j.clients.portal.get2(ip=addr, port=port)
        oldauth = ctx.env.get('HTTP_AUTHORIZATION', None)
        if oldauth is not None:
            cl._session.headers.update({'Authorization': oldauth})
        elif ctx.env.get('HTTP_COOKIE', None):
            cookie = ctx.env.get('HTTP_COOKIE', None)
            cl._session.headers.update({'Cookie': cookie})
        elif 'authkey' in ctx.params:
            secret = ctx.params['authkey']
            cl._session.headers.update({'Authorization': 'authkey {}'.format(secret)})
        return cl

    def getProviderByStackId(self, stackId):
        return CloudProvider(stackId)

    def addDiskToMachine(self, machine, disk):
        return True

    def getProviderByGID(self, gid):
        stacks = models.stack.search({'gid': gid, 'status': 'ENABLED'})[1:]
        if stacks:
            return self.getProviderByStackId(stacks[0]['id'])
        raise exceptions.ServiceUnavailable('Not enough resources available on current location')

    def markProvider(self, stack, eco):
        stack = models.stack.get(stack.id)
        update = {'error': stack.error + 1}
        if update['error'] >= 2:
            update['status'] = 'ERROR'
            update['eco'] = eco.guid
        models.stack.updateSearch({'id': stack.id}, {'$set': update})

    def clearProvider(self, stack):
        models.stack.updateSearch({'id': stack.id}, {'$set': {'error': 0, 'eco': None, 'status': 'ENABLED'}})

    def getIdByReferenceId(self, objname, referenceId):
        model = getattr(models, '%s' % objname)
        queryapi = getattr(model, 'search')
        query = {'referenceId': referenceId}
        ids = queryapi(query)[1:]
        if ids:
            return ids[0]['id']
        else:
            return None

    def getBestProvider(self, gid, imageId=None, excludelist=[], memory=None):
        capacityinfo = self.getCapacityInfo(gid, imageId)
        if not capacityinfo:
            return -1
        capacityinfo = [node for node in capacityinfo if node['id'] not in excludelist]
        if not capacityinfo:
            return -1

        for provider in capacityinfo:
            if memory is None:
                return provider
            elif memory < provider['freememory']:
                return provider
        return -1

    def getNode(self, machine, driver=None):
        image = models.image.get(machine.imageId)
        cloudspace = models.cloudspace.get(machine.cloudspaceId)
        name = 'vm-{}'.format(machine.id)
        interfaces = []
        volumes = []
        for nic in machine.nics:
            if nic.type == 'bridge':
                bridgename = 'space_{:04x}'.format(cloudspace.networkId)
                bridgetype = 'private'
                networkId = cloudspace.networkId
            elif nic.type == 'PUBLIC':
                tags = j.core.tags.getObject(nic.params)
                pool = models.externalnetwork.get(int(tags.tagGet('externalnetworkId')))
                networkId = pool.vlan
                if networkId == 0:
                    bridgename = 'public'
                else:
                    bridgename = 'ext-{:04x}'.format(networkId)
                bridgetype = 'PUBLIC'
            else:
                continue
            interfaces.append(NetworkInterface(nic.macAddress, nic.deviceName, bridgetype, bridgename, networkId))
        for diskId in machine.disks:
            disk = models.disk.get(diskId)
            volume = j.apps.cloudapi.disks.getStorageVolume(disk, driver)
            volumes.append(volume)

        size = models.size.get(machine.sizeId)
        extra = {'ifaces': interfaces, 'imagetype': image.type, 'volumes': volumes, 'size': size}
        node = Node(
            id=machine.referenceId,
            name=name,
            state=5,
            public_ips=[],
            private_ips=[],
            driver=driver,
            extra=extra
        )
        return node

    def getProvider(self, machine):
        if machine.referenceId and machine.stackId:
            return self.getProviderByStackId(machine.stackId)
        return None

    def getProviderAndNode(self, machineId):
        machineId = int(machineId)
        machine = models.vmachine.get(machineId)
        if machine.status in ['ERROR', 'DESTROYED', 'DESTROYING']:
            return None, None, machine
        provider = self.getProvider(machine)
        vmnode = None
        drivertype = 'libvirt'
        if provider:
            drivertype = provider.name
            vmnode = provider.ex_get_node_details(machine.referenceId)
        node = self.getNode(machine, provider)
        if vmnode:
            node.state = vmnode.state

        realstatus = enums.MachineStatusMap.getByValue(node.state, drivertype) or machine.status
        if realstatus != machine.status:
            if realstatus == 'DESTROYED':
                realstatus = 'HALTED'
            machine.status = realstatus
            models.vmachine.set(machine)
        return provider, node, machine

    def chooseProvider(self, machine):
        cloudspace = models.cloudspace.get(machine.cloudspaceId)
        size = models.size.get(machine.sizeId)
        newstack = self.getBestProvider(cloudspace.gid, machine.imageId, memory=size.memory)
        if newstack == -1:
            raise exceptions.ServiceUnavailable('Not enough resources available to start the requested machine')
        machine.stackId = newstack['id']
        models.vmachine.set(machine)
        return True

    def getActiveSessionsKeys(self):
        return self.agentcontroller.listActiveSessions().keys()

    def getCapacityInfo(self, gid, imageId=None):
        resourcesdata = list()
        activesessions = self.getActiveSessionsKeys()
        if imageId:
            stacks = models.stack.search({"images": imageId, 'gid': gid})[1:]
        else:
            stacks = models.stack.search({'gid': gid})[1:]
        nodeids = [int(stack['referenceId']) for stack in stacks]
        query = {'$query': {'id': {'$in': nodeids}},
                 '$fields': ['id', 'memory']}
        nodesbyid = {node['id']: node['memory'] for node in self.syscl.node.search(query)[1:]}
        sizes = {s['id']: s['memory'] for s in models.size.search({'$fields': ['id', 'memory']})[1:]}
        grid = self.syscl.grid.get(gid)
        for stack in stacks:
            if stack.get('status', 'ENABLED') == 'ENABLED':
                nodeid = int(stack['referenceId'])
                if (stack['gid'], nodeid) not in activesessions:
                    continue
                self.getStackCapacity(stack, grid, sizes, nodesbyid)
                resourcesdata.append(stack)
        resourcesdata.sort(key=lambda s: s['usedmemory'])
        return resourcesdata

    def getStackCapacity(self, stack, grid, sizes, nodesbyid):
        # search for all vms running on the stacks
        usedvms = models.vmachine.search({'$fields': ['id', 'sizeId'],
                                          '$query': {'stackId': stack['id'],
                                                     'status': {'$nin': ['HALTED', 'ERROR', 'DESTROYED']}}
                                          }
                                         )[1:]
        stack['usedvms'] = len(usedvms)
        if usedvms:
            stack['usedmemory'] = sum(sizes[vm['sizeId']] for vm in usedvms)
        else:
            stack['usedmemory'] = 0
        # add vfws
        nodeid = int(stack['referenceId'])
        roscount = self.vcl.virtualfirewall.count({'gid': stack['gid'], 'nid': nodeid})
        stack['usedmemory'] += roscount * 128
        stack['usedros'] = roscount
        stack['totalmemory'] = nodesbyid[nodeid]
        reservedmemory = GridConfig(grid, stack['totalmemory']/1024.).get('reserved_mem') or 0
        stack['reservedmemory'] = reservedmemory
        stack['freememory'] = stack['totalmemory'] - stack['usedmemory'] - reservedmemory

    def checkUser(self, username, activeonly=True):
        """
        Check if a user exists with the given username or email address

        :param username: username or emailaddress of the user
        :param activeonly: only return activated users if set to True
        :return: User if found
        """
        query = {'$or': [{'id': username}, {'emails': username}]}
        if activeonly:
            query['active'] = True
        users = self.syscl.user.search(query)[1:]
        if users:
            return users[0]
        else:
            return None

    def updateResourceInvitations(self, username, emailaddress):
        """
        Update the invitations in ACLs of Accounts, Cloudspaces and Machines after user registration

        :param username: username the user has registered with
        :param emailaddress: emailaddress of the registered users
        :return: True if resources were updated
        """
        # Validate that only one email address was sent for updating the resources
        if len(emailaddress.split(',')) > 1:
            raise exceptions.BadRequest('Cannot update resource invitations for a list of multiple '
                                        'email addresses')

        for account in self.cbcl.account.search({'acl.userGroupId': emailaddress})[1:]:
            accountobj = self.cbcl.account.get(account['guid'])
            for ace in accountobj.acl:
                if ace.userGroupId == emailaddress:
                    # Update userGroupId and status after user registration
                    ace.userGroupId = username
                    ace.status = 'CONFIRMED'
                    self.cbcl.account.set(accountobj)
                    break

        for cloudspace in self.cbcl.cloudspace.search({'acl.userGroupId': emailaddress})[1:]:
            cloudspaceobj = self.cbcl.cloudspace.get(cloudspace['guid'])
            for ace in cloudspaceobj.acl:
                if ace.userGroupId == emailaddress:
                    # Update userGroupId and status after user registration
                    ace.userGroupId = username
                    ace.status = 'CONFIRMED'
                    self.cbcl.cloudspace.set(cloudspaceobj)
                    break

        for vmachine in self.cbcl.vmachine.search({'acl.userGroupId': emailaddress})[1:]:
            vmachineobj = self.cbcl.vmachine.get(vmachine['guid'])
            for ace in cloudspaceobj.acl:
                if ace.userGroupId == emailaddress:
                    # Update userGroupId and status after user registration
                    ace.userGroupId = username
                    ace.status = 'CONFIRMED'
                    self.cbcl.vmachine.set(vmachineobj)
                    break

        return True

    def isaccountuserdeletable(self, userace, acl):
        if set(userace.right) != set('ARCXDU'):
            return True
        else:
            otheradmins = filter(lambda a: set(a.right) == set('ARCXDU') and a != userace, acl)
            if not otheradmins:
                return False
            else:
                return True

    def isValidEmailAddress(self, emailaddress):
        r = re.compile('^[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}$')
        return r.match(emailaddress) is not None

    def isValidRole(self, accessrights):
        """
        Validate that the accessrights map to a valid access role on a resource
        'R' for read only access, 'RCX' for Write and 'ARCXDU' for Admin

        :param accessrights: string with the accessrights to verify
        :return: role name if a valid set of permissions, otherwise fail with an exception
        """
        if accessrights == 'R':
            return 'Read'
        elif set(accessrights) == set('RCX'):
            return 'Read/Write'
        elif set(accessrights) == set('ARCXDU'):
            return 'Admin'
        else:
            raise exceptions.BadRequest('Invalid set of access rights "%s". Please only use "R" '
                                        'for Read, "RCX" for Read/Write and "ARCXDU" for Admin '
                                        'access.' % accessrights)

    def fillResourceLimits(self, resource_limits, preserve_none=False):
        for limit_type in ['CU_M', 'CU_D', 'CU_C', 'CU_NP', 'CU_I']:
            if limit_type not in resource_limits or resource_limits[limit_type] is None:
                resource_limits[limit_type] = None if preserve_none else -1
            elif resource_limits[limit_type] < -1 or resource_limits[limit_type] == 0:
                raise exceptions.BadRequest('A resource limit should be a positive number or -1 (unlimited).')
            if limit_type == 'CU_M':
                resource_limits[limit_type] = resource_limits[limit_type] and float(resource_limits[limit_type])
            else:
                resource_limits[limit_type] = resource_limits[limit_type] and int(resource_limits[limit_type])
        maxVDiskCapacity = resource_limits['CU_D']
        if maxVDiskCapacity is not None and maxVDiskCapacity != -1 and maxVDiskCapacity < 10:
            raise exceptions.BadRequest("Minimum disk capacity for cloudspace is 10GB.")


class CloudSpace(object):

    def __init__(self, cb):
        self.cb = cb
        self.libvirt_actor = j.apps.libcloud.libvirt
        self.network = network.Network(models)

    def release_resources(self, cloudspace, releasenetwork=True):
        #  delete routeros
        fwguid = "%s_%s" % (cloudspace.gid, cloudspace.networkId)
        try:
            fw = self.cb.netmgr._getVFWObject(fwguid)
        except exceptions.ServiceUnavailable:
            pass
        else:
            stack = next(iter(models.stack.search({'referenceId': str(fw.nid), 'gid': fw.gid})[1:]), None)
            if stack and stack['status'] != 'DECOMISSIONED':
                # destroy vm and model
                self.cb.netmgr.fw_delete(fwguid, cloudspace.gid)
            else:
                # destroy model only
                self.cb.netmgr.fw_destroy(fwguid)
        if cloudspace.networkId and releasenetwork:
            self.libvirt_actor.releaseNetworkId(cloudspace.gid, cloudspace.networkId)
            cloudspace.networkId = None
        if cloudspace.externalnetworkip:
            self.network.releaseExternalIpAddress(cloudspace.externalnetworkId, cloudspace.externalnetworkip)
            cloudspace.externalnetworkip = None
        return cloudspace

    def get_leases(self, cloudspaceId):
        leases = []
        for vm in models.vmachine.search({'cloudspaceId': cloudspaceId, 'status': {'$nin': ['DESTROYED', 'ERROR']}})[1:]:
            for nic in vm['nics']:
                if nic['ipAddress'] != 'Undefined' and nic['type'] != 'PUBLIC' and nic['macAddress']:
                    leases.append({'mac-address': nic['macAddress'], 'address': nic['ipAddress']})
        return leases

    def update_firewall(self, cloudspace):
        fwid = '{}_{}'.format(cloudspace.gid, cloudspace.networkId)
        self.cb.netmgr.fw_reapply(fwid)



class Machine(object):

    def __init__(self, cb):
        self.cb = cb
        self.acl = self.cb.agentcontroller

    def cleanup(self, machine):
        for diskid in machine.disks:
            if models.disk.exists(diskid):
                models.disk.delete(diskid)
        if models.vmachine.exists(machine.id):
            models.vmachine.delete(machine.id)

    def validateCreate(self, cloudspace, name, sizeId, imageId, disksize, datadisks):
        self.assertName(cloudspace.id, name)
        if not disksize:
            raise exceptions.BadRequest("Invalid disksize %s" % disksize)

        for datadisksize in datadisks:
            if datadisksize > 2000:
                raise exceptions.BadRequest("Invalid data disk size {}GB max size is 2000GB".format(datadisksize))

        if cloudspace.status == 'DESTROYED':
            raise exceptions.BadRequest('Can not create machine on destroyed Cloud Space')

        image = models.image.get(imageId)
        if disksize < image.size:
            raise exceptions.BadRequest(
                "Disk size of {}GB is to small for image {}, which requires at least {}GB.".format(disksize, image.name, image.size))
        if image.status != "CREATED":
            raise exceptions.BadRequest("Image {} is disabled.".format(imageId))

        if models.vmachine.count({'status': {'$ne': 'DESTROYED'}, 'cloudspaceId': cloudspace.id}) >= 250:
            raise exceptions.BadRequest("Can not create more than 250 Virtual Machines per Cloud Space")

        sizes = j.apps.cloudapi.sizes.list(cloudspace.id)
        if sizeId not in [s['id'] for s in sizes]:
            raise exceptions.BadRequest("Cannot create machine with specified size on this cloudspace")

        size = models.size.get(sizeId)
        if disksize not in size.disks:
            raise exceptions.BadRequest("Disk size of {}GB is invalid for sizeId {}.".format(disksize, sizeId))

    def assertName(self, cloudspaceId, name):
        if not name or not name.strip():
            raise ValueError("Machine name can not be empty")
        results = models.vmachine.search({'cloudspaceId': cloudspaceId, 'name': name,
                                          'status': {'$nin': ['DESTROYED', 'ERROR']}})[1:]
        if results:
            raise exceptions.Conflict('Selected name already exists')

    def createModel(self, name, description, cloudspace, imageId, sizeId, disksize, datadisks):
        datadisks = datadisks or []

        image = models.image.get(imageId)
        machine = models.vmachine.new()
        machine.cloudspaceId = cloudspace.id
        machine.descr = description
        machine.name = name
        machine.sizeId = sizeId
        machine.imageId = imageId
        machine.creationTime = int(time.time())
        machine.updateTime = int(time.time())
        machine.type = 'VIRTUAL'

        def addDisk(order, size, type, name=None):
            disk = models.disk.new()
            disk.name = name or 'Disk nr %s' % order
            disk.descr = 'Machine disk of type %s' % type
            disk.sizeMax = size
            disk.iotune = {'total_iops_sec': DEFAULTIOPS}
            disk.accountId = cloudspace.accountId
            disk.gid = cloudspace.gid
            disk.order = order
            disk.type = type
            diskid = models.disk.set(disk)[0]
            machine.disks.append(diskid)
            return diskid

        addDisk(0, disksize, 'B', 'Boot disk')
        diskinfo = []
        for order, datadisksize in enumerate(datadisks):
            diskid = addDisk(order + 1, int(datadisksize), 'D')
            diskinfo.append((diskid, int(datadisksize)))

        account = machine.new_account()
        if hasattr(image, 'username') and image.username:
            account.login = image.username
        elif image.type != 'Custom Templates':
            account.login = 'cloudscalers'
        else:
            account.login = 'Custom login'
            account.password = 'Custom password'

        if hasattr(image, 'password') and image.password:
            account.password = image.password

        if not account.password:
            length = 6
            chars = removeConfusingChars(string.letters + string.digits)
            letters = [removeConfusingChars(string.ascii_lowercase), removeConfusingChars(string.ascii_uppercase)]
            passwd = ''.join(random.choice(chars) for _ in range(length))
            passwd = passwd + random.choice(string.digits) + random.choice(letters[0]) + random.choice(letters[1])
            account.password = passwd
        auth = NodeAuthPassword(account.password)
        with models.cloudspace.lock('{}_ip'.format(cloudspace.id)):
            nic = machine.new_nic()
            nic.type = 'bridge'
            nic.ipAddress = self.cb.cloudspace.network.getFreeIPAddress(cloudspace)
            machine.id = models.vmachine.set(machine)[0]
        return machine, auth, diskinfo

    def updateMachineFromNode(self, machine, node, stack):
        cloudspace = models.cloudspace.get(machine.cloudspaceId)
        machine.referenceId = node.id
        machine.stackId = stack.id
        machine.status = enums.MachineStatus.RUNNING
        machine.hostName = node.name
        if 'ifaces' in node.extra:
            for iface in node.extra['ifaces']:
                for nic in machine.nics:
                    if nic.macAddress == iface.mac:
                        break
                    if not nic.macAddress:
                        nic.macAddress = iface.mac
                        nic.deviceName = iface.target
                        nic.type = iface.type
                        break
                else:
                    nic = machine.new_nic()
                    nic.macAddress = iface.mac
                    nic.deviceName = iface.target
                    nic.type = iface.type
                    nic.ipAddress = 'Undefined'
        else:
            for ipaddress in node.public_ips:
                nic = machine.new_nic()
                nic.ipAddress = ipaddress
        machine.updateTime = int(time.time())

        # filter out iso volumes
        volumes = filter(lambda v: v.type == 'disk', node.extra['volumes'])
        bootdisk = None
        for order, diskid in enumerate(machine.disks):
            disk = models.disk.get(diskid)
            disk.stackId = stack.id
            disk.referenceId = volumes[order].id
            models.disk.set(disk)
            if disk.type == 'B':
                bootdisk = disk

        cdroms = filter(lambda v: v.type == 'cdrom', node.extra['volumes'])
        for cdrom in cdroms:
            disk = models.disk.new()
            disk.name = 'Metadata iso'
            disk.type = 'M'
            disk.stackId = stack.id
            disk.accountId = bootdisk.accountId
            disk.gid = bootdisk.gid
            disk.referenceId = cdrom.id
            diskid = models.disk.set(disk)[0]
            machine.disks.append(diskid)


        with models.cloudspace.lock('{}_ip'.format(cloudspace.id)):
            for nic in machine.nics:
                if nic.type == 'bridge' and nic.ipAddress == 'Undefined':
                    nic.ipAddress = self.cb.cloudspace.network.getFreeIPAddress(cloudspace)
            models.vmachine.set(machine)


    def create(self, machine, auth, cloudspace, diskinfo, imageId, stackId):
        excludelist = []
        name = 'vm-%s' % machine.id
        newstackId = stackId
        size = models.size.get(machine.sizeId)
        volumes = []

        def getStackAndProvider(newstackId):
            provider = None
            try:
                if not newstackId:
                    stack = self.cb.getBestProvider(cloudspace.gid, imageId, excludelist, size.memory)
                    if stack == -1:
                        self.cleanup(machine)
                        raise exceptions.ServiceUnavailable(
                            'Not enough resources available to provision the requested machine')
                    provider = self.cb.getProviderByStackId(stack['id'])
                else:
                    activesessions = self.cb.getActiveSessionsKeys()
                    provider = self.cb.getProviderByStackId(newstackId)
                    if (provider.gid, provider.id) not in activesessions:
                        raise exceptions.ServiceUnavailable(
                            'Not enough resources available to provision the requested machine')
            except:
                if volumes:
                    # we don't have a provider yet so we get a random one to cleanup
                    provider = self.cb.getProviderByGID(cloudspace.gid)
                    provider.destroy_volumes_by_guid([volume.vdiskguid for volume in volumes])
                self.cleanup(machine)
                raise
            return provider

        node = -1
        while node == -1:
            provider = getStackAndProvider(newstackId)
            image = self.cb.getImage(provider, machine.imageId)
            if not image:
                self.cleanup(machine)
                raise exceptions.BadRequest("Image is not available on requested stack")

            firstdisk = models.disk.get(machine.disks[0])
            try:
                if not volumes:
                    node = provider.create_node(name=name, image=image, disksize=firstdisk.sizeMax, auth=auth,
                                                networkid=cloudspace.networkId, size=size,
                                                datadisks=diskinfo, iotune=firstdisk.iotune)
                else:
                    node = provider.init_node(name, size, volumes, image.type)
            except StorageException as e:
                eco = j.errorconditionhandler.processPythonExceptionObject(e)
                self.cleanup(machine)
                raise exceptions.ServiceUnavailable('Not enough resources available to provision the requested machine')
            except NotEnoughResources as e:
                volumes = e.volumes
                if stackId:
                    provider.destroy_volumes_by_guid([volume.vdiskguid for volume in volumes])
                    self.cleanup(machine)
                    raise exceptions.ServiceUnavailable('Not enough resources available to provision the requested machine')
                else:
                    newstackId = 0
                    excludelist.append(provider.stackId)
            except exceptions.ServiceUnavailable:
                self.cleanup(machine)
                raise
            except Exception as e:
                eco = j.errorconditionhandler.processPythonExceptionObject(e)
                self.cb.markProvider(provider.stack, eco)
                newstackId = 0
                machine.status = 'ERROR'
                models.vmachine.set(machine)
        self.cb.clearProvider(provider.stack)
        self.updateMachineFromNode(machine, node, provider.stack)
        tags = str(machine.id)
        j.logger.log('Created', category='machine.history.ui', tags=tags)
        return machine.id
