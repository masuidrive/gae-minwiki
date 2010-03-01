# -*- coding: utf-8 -*-
# http://d.hatena.ne.jp/elecsta/20081125
import socket
import re

def CheckSpamIP(check_ip = False):
    spam_ip = "127.0.0.2"
    if not re.compile("\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}").match(check_ip):
        return True
    ip_rev = ".".join(reversed(check_ip.split(".")))
    host = "%s.dnsbl.spam-champuru.livedoor.com" % ip_rev

    try:
        ip = socket.gethostbyname(host)
    except:
        return False


    if ip == spam_ip:
        return True
    else: 
        return False
