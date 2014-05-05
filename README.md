<!--
Copyright (c) 2014 TheLastProject
This README file is available under the CC0 license
-->

ToxShare
==========

ToxShare, identifying itself as ShareBot, is a bot allowing you and your friends to easily share, store and retrieve files over the secure, decentralised Tox network.

ToxShare is written in Python, using PyTox to communicate with Tox.

Dependencies
------------

ToxShare depends on PyTox and Python 2.7.3 (other versions may work, but have not been tested)

How to run ToxShare
---------------------

To run ToxShare, execute the main.py file using Python. For example:
``python main.py``

*Note: On the first run, be sure to append the Tox ID of the administrator to the command. As ToxShare will only communicate with users on its friend list and does not accept friend invites, it is important that the bot adds you to its friend list. To do so, run the following command, replacing ToxID with your own Tox ID:*

``python main.py ToxID``

How to use ToxShare
--------

ToxShare is very simple to use and listens to the following commands (in alphabetical order):
* add `<ToxID>` -> add one or more users to ToxShare's friend list
* get `<file>` -> get a file as listed by the ``list`` command
* help -> get a list of commands and instructions
* list [`<search term>`] -> list all files. When a search term is defined, list the files which match the search term

To add a file to ToxShare's storage, simply start a file transfer to it. ToxShare will automatically accept the file transfer and save the file accordingly.

License
-------

This project licensed under the GNU GPLv2 or, at your option, any later version. For more info, please read LICENSE.
