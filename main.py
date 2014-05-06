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

from __future__ import print_function

import sys
import os

from time import sleep, time
from os.path import join, normpath, exists, basename, dirname, getsize
from os import listdir, makedirs
import fcntl

from tox import Tox, OperationFailedError

SERVER = ["54.199.139.199", 33445, "7F9C31FE850E97CEFD4C4591DF93FC757C7C12549DDD55F8EEAECC34FE76C029"]
admin = ""

SERV_ROOT = "files"

class FileRecord(object):
    def __init__(self, friendId, filename, size, op_recv=False):
        self.friendId = friendId
        self.filename = filename
        self.size = size
        self.sent = 0
        self.recv = 0
        self.fd = None
        self.start = False
        self.op_recv = op_recv

    def setup(self):
        if not self.op_recv:
            self.fd = open(self.filename, 'r')
            flags = fcntl.fcntl(self.fd, fcntl.F_GETFL)
            fcntl.fcntl(self.fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            self.start = True
        else:
            self.fd = open(self.filename, 'w')

    def tear_down(self):
        self.start = None
        self.fd.close()

    def rewind(self):
        self.fd.seek(self.sent, os.SEEK_SET)

    def print_progressbar(self):
        COL = 80
        if self.op_recv:
            progress = float(self.recv) / self.size
        else:
            progress = float(self.sent) / self.size

        print("[", end='')
        total = COL - 7
        level = int(total * progress)
        for i in range(level):
            print("#", end='')

        for i in range(total - level):
            print("-", end='')
        print("] %3d%%\r" % int(progress * 100), end='')

        if self.recv == self.size or self.sent == self.size:
            print('')


class ShareBot(Tox):
    def __init__(self):

        self.send_files = {}
        self.recv_files = {}
        self.localfiles = []

        if exists('data'):
            self.load_from_file('data')

        if not exists(SERV_ROOT):
            makedirs(SERV_ROOT)
        self.set_name("ShareBot")
        self.set_status_message("Send me a message with the word 'help'")
        print('ID: %s' % self.get_address())
        if admin:
            try:
                self.add_friend(admin, "Hello, admin. It's ShareBot.")
            except OperationFailedError:
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

    def get_path(self, filename):
        result = normpath(join(SERV_ROOT, filename))

        #: Possibly cross directory attack
        if not result.startswith(SERV_ROOT):
            result = normpath(join(SERV_ROOT, basename(filename)))

        return result

    def update_filelist(self):
        self.localfiles = []
        localdirs = listdir(SERV_ROOT)
        for directory in localdirs:
            for localfile in listdir(os.path.join(SERV_ROOT, directory)):
                if localfile[-5:] != ".part": # Don't list incomplete transfers
                    self.localfiles.append("%s/%s" % (directory, localfile))
        self.localfiles.sort()

    def do_file_senders(self):
        for fileno in self.send_files.keys():
            rec = self.send_files[fileno]
            if not rec.start:
                continue

            try:
                chunck_size = self.file_data_size(fileno)
                while True:
                    data = rec.fd.read(chunck_size)
                    if len(data):
                        self.file_send_data(fileno, fileno, data)
                    rec.sent += len(data)

                    if rec.sent == rec.size:
                        rec.tear_down()
                        self.file_send_control(fileno, 0, fileno,
                                Tox.FILECONTROL_FINISHED)
                        del self.send_files[fileno]
                        break
            except OperationFailedError as e:
                rec.rewind()

            rec.print_progressbar()

    #: Temp function for testing
    def on_friend_request(self, pk, message):
        print('Friend request from %s: %s' % (pk, message))
        self.add_friend_norequest(pk)
        print('Accepted.')

    def on_friend_message(self, friendId, message):
        message = message.split(" ")
        if message[0] == "help":
            self.send_message(friendId, "Type 'list', optionally followed by a search term, to get a list of files I can serve you.")
            self.send_message(friendId, "Type 'get', followed by the number of the file you want to have sent to you.")
            self.send_message(friendId, "Type 'add', followed by one or more friend ID(s), to give one or more friend(s) access to me.")
            self.send_message(friendId, "To add a file to my collection, simply start a file transfer.")
        elif message[0] == "list":
            if len(message) >= 2:
                search = True
            else:
                search = False
            self.send_message(friendId, "I have the following files available. Type 'get', followed by the number between [] to receive that file.")
            self.update_filelist()
            currentid = 0
            for result in self.localfiles:
                if not search or (search and all(term in result for term in message[1:])):
                    self.send_message(friendId, "[%d] %s (%s bytes)" %
                            (currentid, result.split("/")[1], getsize(self.get_path(result))))
                currentid += 1
            self.send_message(friendId, "End of list.")
        elif message[0] == "get":
            try:
                filename = self.localfiles[int(message[1])]
            except IndexError:
                self.send_message(friendId, "Sorry, but I couldn't find that file.")
                return
            print("%s request file `%s', sending" % (self.get_name(friendId),
                filename))
            try:
                size = getsize(self.get_path(filename))
            except OSError:
                self.send_message(friendId, "Sorry, but for some reason I can't access that file.")
                return
            file_no = self.new_file_sender(friendId, size,
                    self.get_path(filename))

            self.send_files[file_no] = FileRecord(friendId,
                self.get_path(filename), size)
        elif message[0] == "add":
            if len(message) >= 2:
                for newfriend in message[1:]:
                    try:
                        self.add_friend(newfriend, "Hey, it's ShareBot. Someone wants to give you access to my files. Please accept my friend request.")
                    except OperationFailedError:
                        pass
                self.send_message(friendId, "Friend request(s) sent")
            else:
                self.send_message(friendId, "Add who?")

    def on_file_send_request(self, friendId, file_no, file_size, filename):
        #: TODO: implement some sort of access control
        print("%s tries to upload a file `%s', accepted" %
                (self.get_name(friendId), filename))
        friend_key = self.get_client_id(friendId)
        
        # Make sure this user has a directory
        path = join(SERV_ROOT, friend_key)
        if not exists(path):
            makedirs(path)

        rec = FileRecord(friendId, self.get_path("%s/%s.part" % (friend_key, filename)), file_size, True)
        rec.setup()

        self.recv_files[file_no] = rec
        self.file_send_control(friendId, 1, file_no, Tox.FILECONTROL_ACCEPT)

    def on_file_control(self, friendId, receive_send, file_no, ctrl, data):
        if receive_send == 1 and ctrl == Tox.FILECONTROL_ACCEPT:
            self.send_files[file_no].setup()
        elif receive_send == 0 and ctrl == Tox.FILECONTROL_FINISHED:
            self.recv_files[file_no].tear_down()
            filename = self.recv_files[file_no].filename
            os.rename(filename, filename.rstrip(".part"))
            del self.recv_files[file_no]

    def on_file_data(self, friendId, file_no, data):
        if self.recv_files.has_key(file_no):
            rec = self.recv_files[file_no]
            rec.fd.write(data)
            rec.recv += len(data)
            rec.print_progressbar()

if len(sys.argv) == 2:
    admin = sys.argv[1]

t = ShareBot()
t.loop()
