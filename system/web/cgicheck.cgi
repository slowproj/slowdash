#! /usr/bin/python

####################
# IF YOU SEE THIS TEXT ON YOUR BROWSER, IT MEANS YOUR CGI SETTING IS NOT PROPERLY DONE #
####################




















import sys
sys.stdout.write('Content-type: text/html\n\n')
sys.stdout.write('<html>\n<head></head>\n<body>\n')
sys.stdout.write('<h3>Congratulations</h3>\n')
sys.stdout.write('Your CGI is running\n')
sys.stdout.write('</body>\n</html>\n')
