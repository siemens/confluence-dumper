==============
How to install
==============
***************************
Configure virtualenvwrapper
***************************
For convenience you should use `virtualenvwrapper <http://virtualenvwrapper.readthedocs.io/en/latest/>`_::

 sudo pip install virtualenvwrapper

Add three lines to /etc/environment or another shell startup file::

 export WORKON_HOME=$HOME/.virtualenvs
 export PROJECT_HOME=$HOME/python_dev
 source /usr/share/virtualenvwrapper/virtualenvwrapper.sh

Create a new virtual environment::

 mkvirtualenv confluence_dumper_venv

Enter the virtual environment::

 workon confluence_dumper_venv

***************************
Configure confluence dumper
***************************
Install dependencies::

 pip install -r requirements.txt

Copy confluence settings::

 cd confluence_dumper
 cp settings.sample.py settings.py

Please personalize the ``settings.py`` on your own according to your confluence instance.

==========
How to use
==========
Don't forget to switch to the virtual environment because of the installed dependencies::

 workon confluence_dumper_venv

Run confluence dumper::

 cd confluence_dumper
 python confluence_dumper.py


======================
How to use with Docker 
======================
Update docker-compose confuguration namely environment variables 

CONFLUENCE_BASE_URL: ""

SPACES_TO_EXPORT: "" # comma separated list of strings, example SPACES_TO_EXPORT: "abc ,cde , confluence_space" 

HTTP_AUTHENTICATION_USERNAME: ""

HTTP_AUTHENTICATION_PASSWORD: ""

VERIFY_PEER_CERTIFICATE: "False" #recommended False

HTTP_PROXIES : "" #Example: HTTP_PROXIES="http:http://localhost:3128, https: http://localhost:3128"

HTTP_CUSTOM_HEADERS : "" # Example for custom authentication: {'user': 'johndoe', 'password': 'sup3rs3cur3pw'}

run with docker compose 

```
docker-compose up 
```

Please use command 

```
docker-compose up -d 
```

for detached mode (all output and input will not be attached to local terminal)


You can also copy docker-compose file to another file and run this command

```
docker-compose up -d -f <filename>
```
