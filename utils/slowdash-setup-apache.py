#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 19 Mar 2022 #


from argparse import ArgumentParser
parser = ArgumentParser()
parser.add_argument(
    '-i', '--interface',
    action='store', dest='interface', default='CGI',
    choices=['CGI', 'WSGI'],
    help='specify gateway interface: CGI (default) or WSGI'
)
args = parser.parse_args()
interface = args.interface

        
import sys, os, stat, glob, shutil, logging

sys_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(sys_dir, 'app', 'server'))
from sd_project import Project

project = Project()
if project.config is None:
    exit(-1)
    

sys_dir = os.path.abspath(project.sys_dir)
project_dir = os.path.abspath(project.project_dir)
project_name = project.config.get('name', None)
user_list = project.auth_list
wsgi_pgrp = 'slowdash_%s_wsgi' % project_name


def ask_yes_no(question, default="yes"):
    valid = {
        "yes":"yes", "y":"yes", "ye":"yes", 
        "no":"no", "n":"no"
    }
    if default == None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while 1:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return default
        elif choice in valid.keys():
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'y(es)' or 'n(o)'\n")


def find_html_base_dir():
    html_base_dir = ''
    home_dir = os.getenv('HOME')
    if not home_dir:
        current_dir = os.getcwd()
        home_dir = '/'.join(current_dir.split('/')[0:3])
            
    home_dir_spilt = home_dir[1:].split('/')
    if len(home_dir_spilt) > 1:
        if home_dir_spilt[-2] == 'home':
            html_base_dir = os.path.join(home_dir, 'public_html')
        elif home_dir_spilt[-2] == 'Users':
            html_base_dir = os.path.join(home_dir, 'Sites')
    if not os.path.isdir(html_base_dir):
        logging.warning(
            'unable to find HTML directory (public_html or Sites)'
        )
        return None
    return html_base_dir

html_base_dir = find_html_base_dir()
if html_base_dir:
    html_dir = os.path.join(html_base_dir, 'SlowDash', project_name)
else:
    sys.stdout.write('ERROR: unable to determine public HTML directory\n')
    exit(-1)


    
sys.stdout.write('Project: %s\n' % project_name)
sys.stdout.write('Interface: %s with Apache2\n' % interface)
sys.stdout.write('Project directory: %s\n' % project_dir)
sys.stdout.write('Public HTML directory: %s\n' % html_dir)
if user_list is not None:
    sys.stdout.write('User: %s\n' % ', '.join(user_list.keys()))
if not (len(project_dir) > 0 and os.path.isdir(project_dir)):
    sys.stdout.write('ERROR: unable to find project directory\n')
    sys.stdout.write('check your SLOWDASH_PROJECT setting\n')
    exit(-1)

    
if len(sys.argv) > 1 and sys.argv[1] == '-y':
    pass
elif ask_yes_no('continue?') != 'yes':
    exit(-1)


if os.path.isdir(html_dir):
    sys.stdout.write('Public HTML directory already exists: %s\n' % html_dir)
else:
    try:
        os.makedirs(html_dir)
        sys.stdout.write('Public HTML directory created: %s\n' % html_dir)
    except:
        sys.stdout.write(
            'ERROR: unable to create public HTML directory: %s\n' % html_dir
        )
        exit(-1)


with open(os.path.join(html_dir, 'slowdash_cgi_config.py'), 'w') as f:
    f.write("sys_dir = '%s'\n" % sys_dir)
    f.write("project_dir = '%s'\n" % project_dir)
    f.close()

with open(os.path.join(html_dir, '.htaccess'), 'w') as f:
    f.write('DirectoryIndex slowhome.html\n')
    f.write('AddType text/javascript .mjs\n')
    f.write('Options +ExecCGI\n')
    if interface == 'CGI':
        f.write('AddHandler cgi-script .cgi\n')
    else:
        f.write('AddHandler wsgi-script .wsgi\n')
    f.write('\n')
    f.write('RewriteEngine On\n')
    if interface == 'CGI':
        f.write('RewriteRule ^api/(.*)$ slowdash.cgi/$1\n')
    else:
        f.write('RewriteRule ^api/(.*)$ slowdash.wsgi/$1\n')
    f.write('\n')
    if user_list is not None:
        f.write('AuthType Basic\n')
        f.write('AuthName "Slowdash Authorization"\n')
        f.write('AuthUserFile %s/.htpasswd\n' % html_dir)
        f.write('Require user %s\n' % ' '.join(user_list.keys()))
        f.write('\n')
    f.write('<FilesMatch "\\.(html|mjs|js)$">\n')
    f.write('  <IfModule mod_headers.c>\n')
    f.write('    Header set Cache-Control "max-age=3600"\n')
    f.write('  </IfModule>\n')
    f.write('</FilesMatch>\n')
    f.write('\n')
  
        
if user_list is not None:
    with open(os.path.join(html_dir, '.htpasswd'), 'w') as f:
        for user in user_list:
            f.write('%s:%s\n' % (user, user_list[user]))

                    
filelist = [
    '*.html', '*.js', '*.mjs', '*.png', '*.css'
]
dirlist = [
    'jagaimo', 'autocruise', 'docs', 'extern'
]
for fileglob in filelist:
    for src in glob.glob(os.path.join(sys_dir, 'app', 'site', fileglob)):
        name = os.path.basename(src)
        shutil.copy(src, html_dir)
for dirname in dirlist:
    src = os.path.join(sys_dir, 'app', 'site', dirname)
    name = os.path.basename(src)
    dst = os.path.join(html_dir, name)
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=True)
if interface == 'CGI':
    src = os.path.join(sys_dir, 'app', 'site', 'slowdash.cgi')
    dest = os.path.join(html_dir, 'slowdash.cgi')
    shutil.copy(src, dest)
    src = os.path.join(sys_dir, 'app', 'site', 'slowdash_wsgi.py')
    dest = os.path.join(html_dir, 'slowdash_wsgi.py')
    shutil.copy(src, dest)
else:
    src = os.path.join(sys_dir, 'app', 'site', 'slowdash_wsgi.py')
    dest = os.path.join(html_dir, 'slowdash.wsgi')
    shutil.copy(src, dest)

    
sys.stdout.write('\n')
sys.stdout.write('=== INSTALLATION IS SUCCESSFUL ===\n')
sys.stdout.write('Public HTML directory for this project is: %s\n' % html_dir)
sys.stdout.write('- To setup a public HTML for another project, set SLOWDASH_PROJECT and run this program.\n')
sys.stdout.write('- It is safe to run this program multiple times, even for the same project.\n')
sys.stdout.write('- Public HTML can be disabled by deleting the HTML directory.\n')
sys.stdout.write('- Disabled public HTML can be re-enabled by running this program again.\n')
sys.stdout.write('\n')

if interface == 'CGI':
    sys.stdout.write('=== Apache configuration (CGI) ===\n')
    sys.stdout.write('- Install Apache2.\n')
    sys.stdout.write('- Enable cgi, userdir, rewrite, and headers modules by:\n')
    sys.stdout.write('    $ sudo a2enmod cgid userdir rewrite headers\n')
    sys.stdout.write('- Edit /etc/apache2/mods-enabled/userdir.conf to allow overriding and GET/POST/DELETE access:\n')
    sys.stdout.write('    AllowOverride All')
    sys.stdout.write('    Require method GET POST OPTIONS')
    sys.stdout.write('- Restart Apache by:\n')
    sys.stdout.write('    $ sudo systemctl restart apache2\n')
else:
    sys.stdout.write('=== Apache configuration (WSGI) ===\n')
    sys.stdout.write('- Install Apache2.\n')
    sys.stdout.write('- Install mod_wsgi by something like:\n')
    sys.stdout.write('    $ sudo apt install libapache2-mod-wsgi-py3\n')
    sys.stdout.write('    $ sudo yum install mod_wsgi\n')
    sys.stdout.write('    $ brew install mod-wsgi\n')
    sys.stdout.write('- Enable wsgi, userdir, rewrite, and headers modules by:\n')
    sys.stdout.write('    $ sudo a2enmod wsgi userdir rewrite headers\n')
    sys.stdout.write('- Add the following lines to /etc/apache2/apache2.conf for WSGI daemon:\n')
    sys.stdout.write('    WSGIDaemonProcess %s processes=5 threads=1 home=%s\n' % (wsgi_pgrp, html_dir))
    sys.stdout.write('    WSGIProcessGroup %s\n' % wsgi_pgrp)
    sys.stdout.write('    WSGIApplicationGroup %{GLOBAL}\n')
    sys.stdout.write('- Restart Apache by:\n')
    sys.stdout.write('    $ sudo systemctl restart apache2\n')
sys.stdout.write('\n')
