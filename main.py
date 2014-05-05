#
# @file main.py
# @author TheLastProject, aitjcize
#
# Copyright (C) 2014 TheLastProject
# All Rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

import sys
import os

from time import sleep, time
from os import path, listdir, makedirs
import fcntl

from tox import Tox, OperationFailedError

SERVER = ["54.199.139.199", 33445, "7F9C31FE850E97CEFD4C4591DF93FC757C7C12549DDD55F8EEAECC34FE76C029"]
admin = ""

DATA = "data"

class ShareBot(Tox):
    def __init__(self):

        self.send_files = {}
        self.recv_files = {}
        self.localfiles = []

        if path.exists('data'):
            self.load_from_file('data')

        if path.exists(DATA):
            self.load_from_file(DATA)

        if not path.exists("files/"):
            makedirs("files/")
        self.set_name("ShareBot")
        self.set_status_message("Send me a message with the word 'help'")
        print('ID: %s' % self.get_address())
        if admin:
            try:
                self.add_friend(admin, "Hello, admin. It's ShareBot.")
            except: # This yields tox.OperationFailedError if the friend is already there. How to catch? FIXME
                pass
        else:
            if not self.count_friendlist():
                print("ShareBot has no friends added. Please restart ShareBot and give your Tox ID as the last argument")
                exit(1)

        self.connect()

    def connect(self):
        print('connecting...')
        self.bootstrap_from_address(SERVER[0], 1, SERVER[1], SERVER[2])

    def loop(self):
        checked = False

        try:
            while True:
                status = self.isconnected()

                if not checked and status:
                    print('Connected to DHT.')
                    checked = True

                if checked and not status:
                    print('Disconnected from DHT.')
                    self.connect()
                    checked = False

                if len(self.send_files):
                    self.do_file_senders()

                self.do()
                sleep(0.01)
        except KeyboardInterrupt:
            self.save_to_file('data')
            self.kill()

    def do_file_senders(self):
        for fno in self.send_files.keys():
            ct = self.send_files[fno]
            try:
                chunck_size = self.file_data_size(ct['fn'])
                print('Progress: %d' % (ct['sent'] * 100 / ct['size']))
                while ct['start']:
                    data = ct['fd'].read(chunck_size)
                    if len(data):
                        self.file_send_data(ct['fn'], fno, data)
                    ct['sent'] += len(data)

                    if ct['sent'] == ct['size']:
                        ct['fd'].close()
                        self.file_send_control(ct['fn'], 0, fno,
                                Tox.FILECONTROL_FINISHED)
                        del self.send_files[fno]
                        break
            except OperationFailedError as e:
                ct['fd'].seek(ct['sent'], os.SEEK_SET)

    #: Temp function for testing
    def on_friend_request(self, pk, message):
        print('Friend request from %s: %s' % (pk, message))
        self.add_friend_norequest(pk)
        print('Accepted.')

    def on_friend_message(self, friendId, message):
        message = message.split(" ")
        if message[0] == "help":
            self.send_message(friendId, "Type 'list' to get a list of files I can serve you.")
            self.send_message(friendId, "Type 'get', followed by the number of the file you want to have sent to you.")
            self.send_message(friendId, "Type 'add', followed by one or more friend ID(s), to give one or more friend(s) access to me.")
            self.send_message(friendId, "To add a file to my collection, simply start a file transfer.")
        elif message[0] == "list":
            self.send_message(friendId, "I have the following files available. Type 'get', followed by the number between [] to receive that file.")
            files = listdir("files/")
            files.sort()
            self.localfiles = []
            currentid = 0
            for result in files:
                self.send_message(friendId, "[%d] %s (%s bytes)" % (currentid, result, path.getsize('files/%s' % result)))
                self.localfiles.append(result)
                currentid += 1
            self.send_message(friendId, "End of list.")
        elif message[0] == "get":
            try:
                filename = self.localfiles[int(message[1])]
            except IndexError:
                self.send_message(friendId, "Sorry, but I couldn't find that file.")
                return
            try:
                size = path.getsize('files/%s' % filename)
            except: # How to catch os.error? FIXME
                self.send_message(friendId, "Sorry, but for some reason I can't access that file.")
                return
            file_no = self.new_file_sender(friendId, size, 'files/%s' % filename)
            self.send_files[file_no] = {
                'fn': friendId,
                'fd': None,
                'name': 'files/%s' % filename,
                'size': size,
                'sent': 0,
                'start': False
            }
        elif message[0] == "add":
            if len(message) >= 2:
                for newfriend in message[1:]:
                    try:
                        self.add_friend(newfriend, "Hey, it's ShareBot. Someone wants to give you access to my files. Please accept my friend request.")
                    except: # tox.OperationalError FIXME
                        pass
                self.send_message(friendId, "Friend request(s) sent")
            else:
                self.send_message(friendId, "Add who?")

    def on_file_send_request(self, friendId, file_no, file_size, filename):
        self.recv_files[file_no] = {
            'fd': open('files/%s' % filename[:-1], 'w'),
            'fn': friendId,
            'size': file_size
        }
        self.file_send_control(friendId, 1, file_no, Tox.FILECONTROL_ACCEPT)

    def on_file_control(self, friendId, receive_send, file_no, ctrl, data):
        # Check if friend accepts file send request
        if receive_send == 1 and ctrl == Tox.FILECONTROL_ACCEPT:
            ct = self.send_files[file_no]
            ct['start'] = True

            fd = open(ct['name'], 'r')
            flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            ct['fd'] = fd
        elif receive_send == 0 and ctrl == Tox.FILECONTROL_FINISHED:
             self.recv_files[file_no]['fd'].close()
             del self.recv_files[file_no]

    def on_file_data(self, friendId, file_no, data):
        if self.recv_files.has_key(file_no):
            ct = self.recv_files[file_no]
            ct['fd'].write(data)

if len(sys.argv) == 2:
    admin = sys.argv[1]

t = ShareBot()
t.loop()
