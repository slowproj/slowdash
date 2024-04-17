#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 19 Mar 2022 #


import sys, os, stat, glob, shutil, logging
from slowdash_config import Config

config = Config()
if config.project is None:
    exit(-1)
    

sys_dir = os.path.abspath(config.sys_dir)
project_dir = os.path.abspath(config.project_dir)
project_name = config.project.get('name', None)
user_list = config.auth_list


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


def find_cgi_base_dir():
    cgi_base_dir = ''
    home_dir = os.getenv('HOME')
    if not home_dir:
        current_dir = os.getcwd()
        home_dir = '/'.join(current_dir.split('/')[0:3])
            
    home_dir_spilt = home_dir[1:].split('/')
    if len(home_dir_spilt) > 1:
        if home_dir_spilt[-2] == 'home':
            cgi_base_dir = os.path.join(home_dir, 'public_html')
        elif home_dir_spilt[-2] == 'Users':
            cgi_base_dir = os.path.join(home_dir, 'Sites')
    if not os.path.isdir(cgi_base_dir):
        logging.warning(
            'unable to find HTML directory (public_html or Sites)'
        )
        return None
    return cgi_base_dir

cgi_base_dir = find_cgi_base_dir()
if cgi_base_dir:
    cgi_dir = os.path.join(cgi_base_dir, 'SlowDash', project_name)
else:
    sys.stdout.write('ERROR: unable to determine CGI directory\n')
    exit(-1)

        
sys.stdout.write('Project: %s\n' % project_name)
sys.stdout.write('Project directory: %s\n' % project_dir)
sys.stdout.write('CGI directory: %s\n' % cgi_dir)
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


if os.path.isdir(cgi_dir):
    sys.stdout.write('CGI directory already exists: %s\n' % cgi_dir)
else:
    try:
        os.makedirs(cgi_dir)
        sys.stdout.write('CGI directory created: %s\n' % cgi_dir)
    except:
        sys.stdout.write(
            'ERROR: unable to create CGI directory: %s\n' % cgi_dir
        )
        exit(-1)


with open(os.path.join(cgi_dir, 'slowdash_cgi_config.py'), 'w') as f:
    f.write("sys_dir = '%s'\n" % sys_dir)
    f.write("project_dir = '%s'\n" % project_dir)
    f.close()

with open(os.path.join(cgi_dir, '.htaccess'), 'w') as f:
    f.write('DirectoryIndex slowhome.html\n')
    f.write('Options +ExecCGI\n')
    f.write('AddType application/x-httpd-cgi .cgi\n')
    f.write('AddHandler cgi-script .cgi\n')
    f.write('AddType text/javascript .mjs\n')
    f.write('\n')
    f.write('RewriteEngine On\n')
    f.write('RewriteRule ^api/(.*)$ slowdash.cgi/$1\n')
    f.write('\n')
    if user_list is not None:
        f.write('AuthType Basic\n')
        f.write('AuthName "Slowdash Authorization"\n')
        f.write('AuthUserFile %s/.htpasswd\n' % cgi_dir)
        f.write('Require user %s\n' % ' '.join(user_list.keys()))
        
if user_list is not None:
    with open(os.path.join(cgi_dir, '.htpasswd'), 'w') as f:
        for user in user_list:
            f.write('%s:%s\n' % (user, user_list[user]))

                    
filelist = {
    'slowdash.cgi',
    '*.html', '*.js', '*.mjs', '*.png', '*.css'
}
dirlist = {
    'jagaimo', 'autocruise', 'docs', 'extern'
}
for fileglob in filelist:
    for src in glob.glob(os.path.join(sys_dir, 'system', 'web', fileglob)):
        name = os.path.basename(src)
        shutil.copy(src, cgi_dir)
for dirname in dirlist:
    src = os.path.join(sys_dir, 'system', 'web', dirname)
    name = os.path.basename(src)
    dst = os.path.join(cgi_dir, name)
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


    
sys.stdout.write('\n')
sys.stdout.write('=== INSTALLATION IS SUCCESSFUL ===\n')
sys.stdout.write('*) To setup SLOWDASH CGI for another project, set SLOWDASH_PROJECT and run this program.\n')
sys.stdout.write('*) It is safe to run this slowdash-setup-cgi.py multiple times, even for the same project.\n')
sys.stdout.write('*) CGI can be disabled by deleting the CGI directory.\n')
sys.stdout.write('*) Disabled CGI can be re-enabled by running this program again.\n')
sys.stdout.write('*) CGI directory for this project: %s\n' % cgi_dir)
sys.stdout.write('\n')
