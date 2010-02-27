# -*- coding: utf-8 -*-
# http://d.hatena.ne.jp/elecsta/20081125
import socket
import re

def CheckSpamIP(check_ip = False):
    # スパムIPアドレス
    spam_ip = "127.0.0.2"

    # IPアドレスが不当な場合はスパムとみなす
    # (単純にXXX.XXX.XXX.XXXかどうかだけチェック)
    if not re.compile("\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}").match(check_ip):
        return True

    # IPアドレス逆順並べ替え(AAA.BBB.CCC.DDD -> DDD.CCC.BBB.AAA)
    ip_rev = ".".join(reversed(check_ip.split(".")))

    # 検索ドメイン生成
    host = "%s.dnsbl.spam-champuru.livedoor.com" % ip_rev

    # ドメイン正引き
    try:
        ip = socket.gethostbyname(host)
    except:                    # 正引き失敗時はスパム元IPアドレス以外と判断
        return False


    # 正引き後アドレス判定
    if ip == spam_ip:          # スパム
        return True
    else:                      # スパム以外
        return False
