from fabric.api import run, put, reboot
import os

def install_prereqs():
    run('apt-get update')
    run('apt-get install python2.7 dialog nginx curl mc ssh mercurial python-gevent python-simplejson python-numpy byobu python-apt ipython python-pip python-imaging python-requests python-paramiko gcc g++ python-dev python-zmq msgpack-python python-mhash python-libvirt wget openssl ca-certificates php5-cgi -y')
    run('yes w | pip install urllib3 ujson blosc pycrypto pylzma')
    
    WORKSPACE = os.environ.get('WORKSPACE')
    run('mkdir -p /opt/jumpscale/cfg/jpackages/')
    run('touch /opt/jumpscale/cfg/jpackages/sources.cfg')
    run('mv /opt/jumpscale/cfg/jpackages/sources.cfg /opt/jumpscale/cfg/jpackages/sources.cfg.bak', pty=True)
    # run('touch /opt/jumpscale/cfg/jpackages/sources.cfg')
    # append('/opt/jumpscale/cfg/jpackages/sources.cfg', "\n[cloudscalers]\nmetadatafromtgz = 0\nqualitylevel = unstable\nmetadatadownload = \nmetadataupload = \nbitbucketaccount = incubaid\nbitbucketreponame = jp_cloudscalers\nblobstorremote = jpackages_remote\nblobstorlocal = jpackages_local")
    put(os.path.join(WORKSPACE, 'ComputeBox/test/sources.cfg'), '/opt/jumpscale/cfg/jpackages/')
    run('mv /usr/local/lib/python2.7/dist-packages/JumpScale/core/_defaultcontent/cfg/jpackages/sources.cfg /usr/local/lib/python2.7/dist-packages/JumpScale/core/_defaultcontent/cfg/jpackages/sources.cfg.bak', pty=True)
    put(os.path.join(WORKSPACE, 'ComputeBox/test/sources.cfg'), '/usr/local/lib/python2.7/dist-packages/JumpScale/core/_defaultcontent/cfg/jpackages/')
    run('mkdir -p ~/.ssh/')
    put(os.path.join(WORKSPACE, 'config/*'), '~/.ssh/')
    run('chmod 0600 ~/.ssh/*')
    run('mkdir -p /opt/jumpscale/var/jpackages/metadata/cloudscalers')
    run('hg clone --ssh "ssh -o StrictHostKeyChecking=no" ssh://hg@bitbucket.org/incubaid/jp_cloudscalers /opt/jumpscale/var/jpackages/metadata/cloudscalers')
    run('mv /opt/jumpscale/var/jpackages/metadata/cloudscalers/unstable/* /opt/jumpscale/var/jpackages/metadata/cloudscalers')
    run('mkdir -p /opt/jumpscale/var/jpackages/metadata/jpackagesbase')
    run('hg clone https://hg@bitbucket.org/jumpscale/jpackages_base /opt/jumpscale/var/jpackages/metadata/jpackagesbase/')
    run('mv /opt/jumpscale/var/jpackages/metadata/jpackagesbase/unstable/* /opt/jumpscale/var/jpackages/metadata/jpackagesbase')
    run('hg clone https://hg@bitbucket.org/jumpscale/jp_test /opt/jumpscale/var/jpackages/metadata/test/')
    run('mv /opt/jumpscale/var/jpackages/metadata/test/unstable/* /opt/jumpscale/var/jpackages/metadata/test')
    debians = ('linux-headers-3.11.0-5_3.11.0-5.10_all.deb', 'linux-headers-3.11.0-5-generic_3.11.0-5.10_amd64.deb', 'linux-image-3.11.0-5-generic_3.11.0-5.10_amd64.deb', 'linux-image-extra-3.11.0-5-generic_3.11.0-5.10_amd64.deb', 'linux-tools-common_3.11.0-5.10_all.deb', 'bcache-tools-1.0.0_1.0.0-1_all.deb')
    for deb in debians:
        run('dpkg -i /opt/jumpscale/var/jpackages/files/test/test_os/1.0/generic/%s' % deb)
    reboot(wait=120)
    run('jpackage_install --name test_os')
    
    run('mkdir -p /home/ISO')
    run('wget -P /home/ISO/ http://files.incubaid.com/iaas/ubuntu-13.04-server-amd64.iso')
    
    put(os.path.join(WORKSPACE, 'ComputeBox/test/libvirt_no_sparse.patch'), '/usr/share/pyshared/')
    put(os.path.join(WORKSPACE, 'ComputeBox/test/raring.patch'), '/tmp/')
   

    run('jpackage_install --name bootstrapper')
    run('jpackage_install --name cloudbroker')
    run('jpackage_install --name cloudscalers_fe')
    run('mv /opt/jumpscale/cfg/jpackages/sources.cfg.bak /opt/jumpscale/cfg/jpackages/sources.cfg', pty=True)
    run('mv /usr/local/lib/python2.7/dist-packages/JumpScale/core/_defaultcontent/cfg/jpackages/sources.cfg.bak /usr/local/lib/python2.7/dist-packages/JumpScale/core/_defaultcontent/cfg/jpackages/sources.cfg', pty=True)
    put(os.path.join(WORKSPACE, 'ComputeBox/test/startall.py'), '/tmp/')
    run('python /tmp/startall.py')
