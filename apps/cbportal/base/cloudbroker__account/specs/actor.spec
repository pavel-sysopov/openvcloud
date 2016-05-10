[actor] @dbtype:mem,fs
    """
    Operator actions for interventions on accounts
    """
    method:disable
        """
        disable an account.
        """
        var:accountId int,,ID of account
        var:reason str,,reason of disabling the account

    method:enable
        """
        enable an account.
        """
        var:accountId int,,ID of account to enable
        var:reason str,,reason of enabling the account

    method:delete
        """
        Complete delete an account from the system
        """"
        var:accountId int,,ID of account to delete
        var:reason str,,reason for deleting the account

    method:addUser
        """
        Give a user access rights.
        Access rights can be 'R' or 'W'
        """"
        var:accountId int,,ID of account to add to
        var:username str,,name of the user to be given rights
        var:accesstype str,, R or W

    method:deleteUser
        """
        Delete user from account.
        """"
        var:accountId int,,ID of account to remove from
        var:username str,,name of the user to be removed
        var:recursivedelete bool,, recursively delete access rights from owned cloudspaces and vmachines


    method:create
        """
        Create Account.
        Setting a cloud unit maximum to -1 will not put any restrictions on the resource
        """"
        var:name str,, Display name
        var:username str,, name of the account
        var:emailaddress str,,email
        var:location str,,locationcode
        var:maxMemoryCapacity float,-1, max size of memory in GB @optional
        var:maxVDiskCapacity int,-1, max size of aggregated vdisks in GB @optional
        var:maxCPUCapacity int,-1, max number of cpu cores @optional
        var:maxNASCapacity int,-1, max size of primary(NAS) storage in TB @optional
        var:maxArchiveCapacity int,-1, max size of secondary(Archive) storage in TB @optional
        var:maxNetworkOptTransfer int,-1, max sent/received network transfer in operator @optional
        var:maxNetworkPeerTransfer int,-1, max sent/received network transfer peering @optional
        var:maxNumPublicIP int,-1, max number of assigned public IPs @optional

    method:update
        """
        Update Account.
        Setting a cloud unit maximum to -1 will not put any restrictions on the resource
        """"
        var:accountId int,,ID of account
        var:name str,, Display name
        var:maxMemoryCapacity float,, max size of memory in GB
        var:maxVDiskCapacity int,, max size of aggregated vdisks in GB
        var:maxCPUCapacity int,, max number of cpu cores
        var:maxNASCapacity int,, max size of primary(NAS) storage in TB
        var:maxArchiveCapacity int,, max size of secondary(Archive) storage in TB
        var:maxNetworkOptTransfer int,, max sent/received network transfer in operator
        var:maxNetworkPeerTransfer int,, max sent/received network transfer peering
        var:maxNumPublicIP int,, max number of assigned public IPs
