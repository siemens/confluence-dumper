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
