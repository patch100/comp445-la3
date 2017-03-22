import re
from Queue import Queue
from socket import *
from threading import Thread
from time import sleep


def run_sender(username, host, port, q):
    sender = socket(AF_INET, SOCK_DGRAM)
    sender.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    sender.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    channel = "GENERAL"
    try:
        join_message = write_app_message(username, "JOIN", "has joined chat", channel)
        sender.sendto(join_message, (host, port))
        sleep(1)
        while True:
            if not q.empty():
                item = q.get(block=False, timeout=None)
                if item == "quit":
                    q.task_done()
                    break

            user_message = raw_input()
            if user_message == "/leave":
                q.put("quit")
                app_message = write_app_message(username, "LEAVE", "left chat", channel)
                sender.sendto(app_message, (host, port))
                app_message = write_app_message(username, "QUIT", "left chat", channel)
                sender.sendto(app_message, ('', port))
                break
            elif user_message == "/who":
                app_message = write_app_message(username, "WHO", "whos this", channel)
                sender.sendto(app_message, ('', port))
            elif re.match('\/private (\w+)', user_message):
                search = re.search('\/private (\w+)', user_message)
                app_message = write_app_message(username, "PRIVATE-TALK", search.group(1), channel)
                sender.sendto(app_message, ('',port))
                print "send private message to " + search.group(1)
                user_message = raw_input()
                if user_message == "/leave":
                    q.put("quit")
                    app_message = write_app_message(username, "LEAVE", "left chat", channel)
                    sender.sendto(app_message, (host, port))
                    app_message = write_app_message(username, "QUIT", "left chat", channel)
                    sender.sendto(app_message, ('', port))
                    break
                app_message = write_app_message(username, "PRIVATE-TALK", user_message, channel)
                sender.sendto(app_message, ('', port))
            elif re.match('\/channel (\w+)', user_message):
                search = re.search('\/channel (\w+)', user_message)
                channel = search.group(1)
                app_message = write_app_message(username, "CHANNEL", "switching channels", channel)
                sender.sendto(app_message, ('', port))
            else:
                app_message = write_app_message(username, "TALK", user_message, channel)
                sender.sendto(app_message, (host, port))
    except error, msg:
        print msg
    finally:
        sender.close()

def run_receiver(username, host, port, q):
    receiver = socket(AF_INET, SOCK_DGRAM)
    receiver.bind((host, port))
    user_list = []
    pm_user = ""
    sending_pm = False
    default_channel = "GENERAL"
    try:
        while True:
            data, addr = receiver.recvfrom(1024)  # buffer size is 1024 bytes
            sender, channel, command, message = read_app_message(data)

            if command == "TALK":
                if channel == default_channel:
                    print "[{} #{}]: {}".format(sender, channel, message)
            elif command == "JOIN":
                if len(user_list) == 0 and username == sender:
                    user_list.append((sender, addr[0]))
                elif username == sender:
                    app_message = write_app_message(username, "DENY", "user already exists", channel)
                    receiver.sendto(app_message, (addr[0], port))
                else:
                    app_message = write_app_message(username, "PING", "PING", channel)
                    user_list.append((sender, addr[0]))
                    receiver.sendto(app_message, (addr[0], port))
                    print "{} joined!".format(sender)

            elif command == "LEAVE":
                user_list.remove((sender, addr[0]))
                print "{} left!".format(sender)
            elif command == "QUIT":
                print "closing chat application..."
                if not q.empty():
                    item = q.get(block=False, timeout=None)
                    if item == "quit":
                        q.task_done()
                        break
            elif command == "WHO":
                print "List of connected users:"
                for user in user_list:
                    print user[0]
            elif command == "PING":
                user_list.append((sender, addr[0]))
            elif command == "CHANNEL":
                default_channel = channel
                print "Channel changed to {}".format(channel)
            elif command == "DENY":
                q.put("quit")
                print "username already in use"
                break
            elif command == "PRIVATE-TALK":
                if sender == username:
                    if not sending_pm:
                        for user in user_list:
                            if user[0] == message:
                                pm_user = user
                        sending_pm = True
                    else:
                        sending_pm = False
                        app_message = write_app_message(username, "PRIVATE-TALK", message, channel)
                        receiver.sendto(app_message, (pm_user[1], port))
                else:
                    print "[{}] (PRIVATE): {}".format(sender, message)

    except error, msg:
        print msg
    finally:
        receiver.close()

def write_app_message(username, command, message, channel):
    return "user: {}\nchannel: {}\ncommand: {}\nmessage: {}\n\n".format(username,channel,command,message)

def read_app_message(data):
    search = re.search('user: (\w+)\s*channel: (\w+)\s*command: (TALK|JOIN|LEAVE|WHO|QUIT|PING|PRIVATE-TALK|CHANNEL|DENY)\s*message: ([\w \S]*)\n\n', data)
    return (search.group(1), search.group(2), search.group(3), search.group(4))

username = raw_input("Please choose a username: ")

q = Queue()

receiver = Thread(target=run_receiver, args=(username, '', 8081, q))
receiver.start()

sleep(1)

sender = Thread(target=run_sender, args=(username, '255.255.255.255', 8081, q))
sender.start()

q.join()
receiver.join()
sender.join()

