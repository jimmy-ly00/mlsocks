# from gevent import monkey; monkey.patch_all()
import socket
import sys
import select
import SocketServer
import struct

import fcntl
import termios
import array

import time
import random
from math import log, exp, ceil
from gevent import sleep, spawn, select
from gevent.pool import Group


BUF_SIZE = 512


class ThreadingTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer): pass
class Socks5Server(SocketServer.StreamRequestHandler):
    def delay_message(self, message, delay, current_target):
        sleep(delay)
        print("New delay: {}".format(delay))
        current_target.send(message)

    def calculate_delay(self, prev):
        # Generate random number from truncated exponential distribution
        u = random.SystemRandom().random()
        lam = 2  # mean
        tau = 10  # maximum bound
        delay = -log(1 - (1 - exp(-lam * tau)) * u) / lam

        timestamp = time.time() * 1000
        new = timestamp + delay * 1000
        # Stops messages overtaking each other by checking against the latest delay
        if prev[0] < new:
            prev[0] = new
            prev[1] = delay
        else:
            delay = prev[1]

        return delay
        
    def handle_tcp(self, sock, remote):
        fdset = [sock, remote]
        tasks = Group()
        prev = [0, 0]
        sock_switch = remote_switch = 0
        sock_counter = remote_counter = 0
        sock_count = remote_count = 0
        sock_size = array.array('i', [0])
        remote_size = array.array('i', [0])
        while True:
            r, w, e = select.select(fdset, [], [])
            # Problem is knowing beforehand when the socket is going to switch to joinall remainding tasks
            # FIONREAD will check size of available bytes of the socket to catch the last send()/recv()
            if sock in r:
                if sock_switch == 0:
                    fcntl.ioctl(sock, termios.FIONREAD, sock_size, True)
                    sock_count = ceil(sock_size[0] / float(BUF_SIZE))
                    print("sock", sock_size[0], sock_count)
                    sock_switch = 1
                delay = self.calculate_delay(prev)
                sock_buf = sock.recv(BUF_SIZE)
                #print(sock_buf)
                if sock_buf is None or sock_buf == "": break
                tasks.spawn(self.delay_message, sock_buf, delay, remote)
                sock_counter += 1
            if remote in r:
                if remote_switch == 0:
                    fcntl.ioctl(remote, termios.FIONREAD, remote_size, True)
                    remote_count = ceil(remote_size[0] / float(BUF_SIZE))
                    print("remote", remote_size[0], remote_count)
                    remote_switch = 1
                delay = self.calculate_delay(prev)
                remote_buf = remote.recv(BUF_SIZE)
                #print(remote_buf)
                if remote_buf is None or remote_buf == "": break
                tasks.spawn(self.delay_message, remote_buf, delay, sock)
                remote_counter += 1

            # Wait for last task before switching socket
            if sock_count == sock_counter and sock_switch == 1:
                print("joiningsocks")
                tasks.join()
                sock_counter = sock_switch = 0
            if remote_count == remote_counter and remote_switch == 1:
                print("joiningremote")
                tasks.join()
                remote_counter = remote_switch = 0

    def handle(self):
        try:
            print 'socks connection from ', self.client_address
            sock = self.connection
            # 1. Version
            sock.recv(262)
            sock.send(b"\x05\x00")
            # 2. Request
            data = self.rfile.read(4)
            mode = ord(data[1])
            addrtype = ord(data[3])
            if addrtype == 1:       # IPv4
                addr = socket.inet_ntoa(self.rfile.read(4))
            elif addrtype == 3:     # Domain name
                addr = self.rfile.read(ord(sock.recv(1)[0]))
            port = struct.unpack('>H', self.rfile.read(2))
            reply = b"\x05\x00\x00\x01"
            try:
                if mode == 1:  # 1. Tcp connect
                    remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    remote.connect((addr, port[0]))
                    print 'Tcp connect to', addr, port[0]
                else:
                    reply = b"\x05\x07\x00\x01"  # Command not supported
                local = remote.getsockname()
                reply += socket.inet_aton(local[0]) + struct.pack(">H", local[1])
            except socket.error:
                # Connection refused
                reply = '\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00'
            sock.send(reply)
            # 3. Transfering
            if reply[1] == '\x00':  # Success
                if mode == 1:    # 1. Tcp connect
                    self.handle_tcp(sock, remote)
        except socket.error, exc:
            print "Caught exception socket.error : %s" % exc


def main():
    ThreadingTCPServer.allow_reuse_address = True
    server = ThreadingTCPServer(('127.0.0.1', 1080), Socks5Server)
    server.serve_forever()

if __name__ == '__main__':
    main()
