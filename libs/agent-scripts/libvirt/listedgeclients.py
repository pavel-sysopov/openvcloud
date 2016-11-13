from JumpScale import j

descr = """
Libvirt script to list existing vpools
"""

name = "listedgeclients"
category = "libvirt"
organization = "greenitglobe"
author = "geert@greenitglobe.com"
license = "bsd"
version = "2.0"
roles = []
async = True


def action(ovs_connection):
    # Lists edge clients
    #
    # ovs_connection: dict holding connection info for ovs restapi
    #   eg: { ips: ['ip1', 'ip2', 'ip3'], client_id: 'dsfgfs', client_secret: 'sadfafsdf'}
    #
    # returns list of edge clients
    #   eg: [{'storageip': '10.106.1.34',
    #         'edgeport': 26202,
    #         'storagerouterguid': '....',
    #         'vpool_guid': '....',
    #         'vpool': 'vmstor',
    #         'protocol': 'tcp'
    #        }, ...]


    # TODO: This information should come from the OVS restapi's.
    rdma = None
    for ip in ovs_connection['ips']:
        con = j.remote.cuisine.connect(ip, 22)
        try:
            rdma = con.run("python -c \"import sys; sys.path.append('/opt/OpenvStorage'); from ovs.extensions.generic.configuration import Configuration; print Configuration.get('/ovs/framework/rdma')\"") == 'True'
            break
        except Exception, e:
            j.logger.log("Failed to get storage transport protocol:\n\n{}".format(str(e)))
    protocol = "rdma" if rdma else "tcp"


    ovs = j.clients.openvstorage.get(ips=ovs_connection['ips'],
                                     credentials=(ovs_connection['client_id'],
                                                  ovs_connection['client_secret']))

    # First create a vpools dict
    vpools = dict()
    result = ovs.get('/vpools', params={'contents': 'vpool'})
    for vpool in result['data']:
        vpools[vpool['guid']] = vpool['name']

    # Then list the storage drivers
    edgeclients = list()
    result = ovs.get('/storagedrivers', params={'contents': 'vpool,storagerouter,vdisks_guids'})
    for storagedriver in result['data']:
        edgeclients.append(dict(storageip=storagedriver['storage_ip'],
                                edgeport=storagedriver['ports']['edge'],
                                storagerouterguid=storagedriver['storagerouter_guid'],
                                vpoolguid=storagedriver['vpool_guid'],
                                vpool=vpools[storagedriver['vpool_guid']],
                                vdiskcount=len(storagedriver['vdisks_guids']),
                                protocol=protocol))

    return edgeclients


if __name__ == '__main__':
    import pprint
    scl = j.clients.osis.getNamespace('system')
    grid = scl.grid.get(j.application.whoAmI.gid)
    credentials = grid.settings['ovs_credentials']
    credentials['ips'] = ['localhost']
    pprint.pprint(action(credentials))