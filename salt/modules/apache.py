# -*- coding: utf-8 -*-
'''
Support for Apache
'''

# Import python libs
import os
import re
import logging
import urllib2

# Import salt libs
import salt.utils

log = logging.getLogger(__name__)


def __virtual__():
    '''
    Only load the module if apache is installed
    '''
    cmd = _detect_os()
    if salt.utils.which(cmd):
        return 'apache'
    return False


def _detect_os():
    '''
    Apache commands and paths differ depending on packaging
    '''
    # TODO: Add pillar support for the apachectl location
    if __grains__['os_family'] == 'RedHat':
        return 'apachectl'
    elif __grains__['os_family'] == 'Debian':
        return 'apache2ctl'
    else:
        return 'apachectl'


def version():
    '''
    Return server version from apachectl -v

    CLI Example:

    .. code-block:: bash

        salt '*' apache.version
    '''
    cmd = '{0} -v'.format(_detect_os())
    out = __salt__['cmd.run'](cmd).splitlines()
    ret = out[0].split(': ')
    return ret[1]


def fullversion():
    '''
    Return server version from apachectl -V

    CLI Example:

    .. code-block:: bash

        salt '*' apache.fullversion
    '''
    cmd = '{0} -V'.format(_detect_os())
    ret = {}
    ret['compiled_with'] = []
    out = __salt__['cmd.run'](cmd).splitlines()
    # Example
    #  -D APR_HAS_MMAP
    define_re = re.compile(r'^\s+-D\s+')
    for line in out:
        if ': ' in line:
            comps = line.split(': ')
            if not comps:
                continue
            ret[comps[0].strip().lower().replace(' ', '_')] = comps[1].strip()
        elif ' -D' in line:
            cwith = define_re.sub('', line)
            ret['compiled_with'].append(cwith)
    return ret


def modules():
    '''
    Return list of static and shared modules from apachectl -M

    CLI Example:

    .. code-block:: bash

        salt '*' apache.modules
    '''
    cmd = '{0} -M'.format(_detect_os())
    ret = {}
    ret['static'] = []
    ret['shared'] = []
    out = __salt__['cmd.run'](cmd).splitlines()
    for line in out:
        comps = line.split()
        if not comps:
            continue
        if '(static)' in line:
            ret['static'].append(comps[0])
        if '(shared)' in line:
            ret['shared'].append(comps[0])
    return ret


def servermods():
    '''
    Return list of modules compiled into the server (apachectl -l)

    CLI Example:

    .. code-block:: bash

        salt '*' apache.servermods
    '''
    cmd = '{0} -l'.format(_detect_os())
    ret = []
    out = __salt__['cmd.run'](cmd).splitlines()
    for line in out:
        if not line:
            continue
        if '.c' in line:
            ret.append(line.strip())
    return ret


def directives():
    '''
    Return list of directives together with expected arguments
    and places where the directive is valid (``apachectl -L``)

    CLI Example:

    .. code-block:: bash

        salt '*' apache.directives
    '''
    cmd = '{0} -L'.format(_detect_os())
    ret = {}
    out = __salt__['cmd.run'](cmd)
    out = out.replace('\n\t', '\t')
    for line in out.splitlines():
        if not line:
            continue
        comps = line.split('\t')
        desc = '\n'.join(comps[1:])
        ret[comps[0]] = desc
    return ret


def vhosts():
    '''
    Show the settings as parsed from the config file (currently
    only shows the virtualhost settings). (``apachectl -S``)
    Because each additional virtual host adds to the execution
    time, this command may require a long timeout be specified.

    CLI Example:

    .. code-block:: bash

        salt -t 10 '*' apache.vhosts
    '''
    cmd = '{0} -S'.format(_detect_os())
    ret = {}
    namevhost = ''
    out = __salt__['cmd.run'](cmd)
    for line in out.splitlines():
        if not line:
            continue
        comps = line.split()
        if 'is a NameVirtualHost' in line:
            namevhost = comps[0]
            ret[namevhost] = {}
        else:
            if comps[0] == 'default':
                ret[namevhost]['default'] = {}
                ret[namevhost]['default']['vhost'] = comps[2]
                ret[namevhost]['default']['conf'] = re.sub(r'\(|\)', '', comps[3])
            if comps[0] == 'port':
                ret[namevhost][comps[3]] = {}
                ret[namevhost][comps[3]]['vhost'] = comps[3]
                ret[namevhost][comps[3]]['conf'] = re.sub(r'\(|\)', '', comps[4])
                ret[namevhost][comps[3]]['port'] = comps[1]
    return ret


def signal(signal=None):
    '''
    Signals httpd to start, restart, or stop.

    CLI Example:

    .. code-block:: bash

        salt '*' apache.signal restart
    '''
    no_extra_args = ('configtest', 'status', 'fullstatus')
    valid_signals = ('start', 'stop', 'restart', 'graceful', 'graceful-stop')

    if signal not in valid_signals and signal not in no_extra_args:
        return
    # Make sure you use the right arguments
    if signal in valid_signals:
        arguments = ' -k {0}'.format(signal)
    else:
        arguments = ' {0}'.format(signal)
    cmd = _detect_os() + arguments
    out = __salt__['cmd.run_all'](cmd)

    # A non-zero return code means fail
    if out['retcode'] and out['stderr']:
        ret = out['stderr'].strip()
    # 'apachectl configtest' returns 'Syntax OK' to stderr
    elif out['stderr']:
        ret = out['stderr'].strip()
    elif out['stdout']:
        ret = out['stdout'].strip()
    # No output for something like: apachectl graceful
    else:
        ret = 'Command: "{0}" completed successfully!'.format(cmd)
    return ret


def useradd(pwfile, user, password, opts=''):
    '''
    Add an HTTP user using the htpasswd command. If the htpasswd file does not
    exist, it will be created. Valid options that can be passed are:

        n  Don't update file; display results on stdout.
        m  Force MD5 encryption of the password (default).
        d  Force CRYPT encryption of the password.
        p  Do not encrypt the password (plaintext).
        s  Force SHA encryption of the password.

    CLI Examples:

    .. code-block:: bash

        salt '*' apache.useradd /etc/httpd/htpasswd larry badpassword
        salt '*' apache.useradd /etc/httpd/htpasswd larry badpass opts=ns
    '''
    if not os.path.exists(pwfile):
        opts += 'c'

    cmd = ['htpasswd', '-b{0}'.format(opts), pwfile, user, password]
    out = __salt__['cmd.run'](cmd, python_shell=False).splitlines()
    return out


def userdel(pwfile, user):
    '''
    Delete an HTTP user from the specified htpasswd file.

    CLI Examples:

    .. code-block:: bash

        salt '*' apache.userdel /etc/httpd/htpasswd larry
    '''
    if not os.path.exists(pwfile):
        return 'Error: The specified htpasswd file does not exist'

    cmd = ['htpasswd', '-D', pwfile, user]
    out = __salt__['cmd.run'](cmd, python_shell=False).splitlines()
    return out


def check_site_enabled(site):
    '''
    Checks to see if the specific Site symlink is in /etc/apache2/sites-enabled.

    This will only be functional on Debian-based operating systems (Ubuntu,
    Mint, etc).

    CLI Examples:

    .. code-block:: bash

        salt '*' apache.check_site_enabled example.com
    '''
    if os.path.islink('/etc/apache2/sites-enabled/{0}'.format(site)):
        return True
    elif (site == 'default' and os.path.islink('/etc/apache2/sites-enabled/000-{0}'.format(site))):
        return True
    else:
        return False


def a2ensite(site):
    '''
    Runs a2ensite for the given site.

    This will only be functional on Debian-based operating systems (Ubuntu,
    Mint, etc).

    CLI Examples:

    .. code-block:: bash

        salt '*' apache.a2ensite example.com
    '''
    ret = {}
    command = ['a2ensite', site]

    try:
        status = __salt__['cmd.retcode'](command, python_shell=False)
    except Exception as e:
        return e

    ret['Name'] = 'Apache2 Enable Site'
    ret['Site'] = site

    if status == 1:
        ret['Status'] = 'Site {0} Not found'.format(site)
    elif status == 0:
        ret['Status'] = 'Site {0} enabled'.format(site)
    else:
        ret['Status'] = status

    return ret


def a2dissite(site):
    '''
    Runs a2dissite for the given site.

    This will only be functional on Debian-based operating systems (Ubuntu,
    Mint, etc).

    CLI Examples:

    .. code-block:: bash

        salt '*' apache.a2dissite example.com
    '''
    ret = {}
    command = ['a2dissite', site]

    try:
        status = __salt__['cmd.retcode'](command, python_shell=False)
    except Exception as e:
        return e

    ret['Name'] = 'Apache2 Disable Site'
    ret['Site'] = site

    if status == 256:
        ret['Status'] = 'Site {0} Not found'.format(site)
    elif status == 0:
        ret['Status'] = 'Site {0} disabled'.format(site)
    else:
        ret['Status'] = status

    return ret


def server_status(profile='default'):
    '''
    Get Information from the Apache server-status handler

    NOTE:
    the server-status handler is disabled by default.
    in order for this function to work it needs to be enabled.
    http://httpd.apache.org/docs/2.2/mod/mod_status.html

    The following configuration needs to exists in pillar/grains
    each entry nested in apache.server-status is a profile of a vhost/server
    this would give support for multiple apache servers/vhosts

    apache.server-status:
      'default':
        'url': http://localhost/server-status
        'user': someuser
        'pass': password
        'realm': 'authentication realm for digest passwords'
        'timeout': 5

    CLI Examples:

    .. code-block:: bash

        salt '*' apache.server_status
        salt '*' apache.server_status other-profile
    '''
    ret = {
        'Scoreboard': {
            '_': 0,
            'S': 0,
            'R': 0,
            'W': 0,
            'K': 0,
            'D': 0,
            'C': 0,
            'L': 0,
            'G': 0,
            'I': 0,
            '.': 0,
        },
    }

    # Get configuration from pillar
    url = __salt__['config.get']('apache.server-status:{0}:url'.format(profile), 'http://localhost/server-status')
    user = __salt__['config.get']('apache.server-status:{0}:user'.format(profile), '')
    passwd = __salt__['config.get']('apache.server-status:{0}:pass'.format(profile), '')
    realm = __salt__['config.get']('apache.server-status:{0}:realm'.format(profile), '')
    timeout = __salt__['config.get']('apache.server-status:{0}:timeout'.format(profile), 5)

    # create authentication handler if configuration exists
    if user and passwd:
        basic = urllib2.HTTPBasicAuthHandler()
        basic.add_password(realm=realm, uri=url, user=user, passwd=passwd)
        digest = urllib2.HTTPDigestAuthHandler()
        digest.add_password(realm=realm, uri=url, user=user, passwd=passwd)
        urllib2.install_opener(urllib2.build_opener(basic, digest))

    # get http data
    url += '?auto'
    try:
        response = urllib2.urlopen(url, timeout=timeout).read().splitlines()
    except urllib2.URLError:
        return 'error'

    # parse the data
    for line in response:
        splt = line.split(':', 1)
        splt[0] = splt[0].strip()
        splt[1] = splt[1].strip()

        if splt[0] == 'Scoreboard':
            for c in splt[1]:
                ret['Scoreboard'][c] += 1
        else:
            if splt[1].isdigit():
                ret[splt[0]] = int(splt[1])
            else:
                ret[splt[0]] = float(splt[1])

    # return the good stuff
    return ret
