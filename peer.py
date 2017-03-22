import re
from Queue import Queue
from socket import *
from threading import Thread
from time import sleep

def run_sender(username, host, port, q):
    sender = socket(AF_INET, SOCK_DGRAM)
    sender.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    sender.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    try:
        join_message = write_app_message(username, "JOIN", "has joined chat")
        sender.sendto(join_message, (host, port))
        while True:
            user_message = raw_input()
            if user_message == "/leave":
                q.put("quit")
                app_message = write_app_message(username, "LEAVE", "left chat")
                sender.sendto(app_message, (host, port))
                break
            app_message = write_app_message(username, "TALK", user_message)
            sender.sendto(app_message, (host, port))
            sleep(1)
    except error, msg:
        print msg
    finally:
        sender.close()

def run_receiver(host, port, q):
    receiver = socket(AF_INET, SOCK_DGRAM)
    receiver.bind((host, port))
    try:
        while True:
            if not q.empty():
                item = q.get(block=False, timeout=None)
                if item == "quit":
                    q.task_done()
                    break
            data, addr = receiver.recvfrom(1024)  # buffer size is 1024 bytes
            sender, command, message = read_app_message(data)

            if command == "TALK":
                print "[{}]: {}".format(sender, message)
            elif command == "JOIN":
                print "{} joined!".format(sender)
            elif command == "LEAVE":
                print "{} left!".format(sender)
    except error, msg:
        print msg
    finally:
        receiver.close()

def write_app_message(username, message, command):
    return "user: {}\ncommand: {}\nmessage: {}\n\n".format(username,message, command)

def read_app_message(data):
    search = re.search('user: (\w+)\s*command: (TALK|JOIN|LEAVE)\s*message: ([\w \S]*)\n\n', data)
    return (search.group(1), search.group(2), search.group(3))

username = raw_input("Please choose a username: ")

q = Queue()

receiver = Thread(target=run_receiver, args=('', 8081, q))
receiver.start()

sender = Thread(target=run_sender, args=(username, '255.255.255.255', 8081, q))
sender.start()

q.join()
receiver.join()
sender.join()

