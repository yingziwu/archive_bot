# Library function

import re

import requests
import tldextract

from config import TIMEOUT, HEADERS
from db import insert_notification, get_notificationi


def get_location(url):
    resp = requests.head(url, timeout=TIMEOUT, headers=HEADERS, allow_redirects=False)
    if (resp.status_code >= 300) and (resp.status_code < 400):
        return True, resp, resp.headers['location']
    else:
        return False, resp, None


def domain_filter(url):
    def get_registered_domain(href):
        domain = re.sub(r'^https?://', '', href).split('/')[0]
        rdomain = tldextract.extract(domain).registered_domain
        return rdomain

    archive_domain_list = {'archive.is', 'archive.ph', 'archive.st', 'perma.cc', 'megalodon.jp', 'archive.fo',
                           'archive.org', 'archive.li', 'archive.md', 'archive.vn', 'archive.today'}

    blacklist = archive_domain_list
    registered_domain = get_registered_domain(url)
    return registered_domain not in blacklist


def text_split(text, max_chas):
    tot, this, tmp = [], [], []
    linelist = text.splitlines()

    for line in linelist:
        if line != '':
            tmp.append(line)
        else:
            tmp.append(line)
            this.extend(tmp)
            tmp = []

        if len('\n'.join(this)) + len('\n'.join(tmp)) > max_chas:
            tot.append(this)
            this = []
    else:
        tot.append(this)

    out = []
    for t in tot:
        out.append('\n'.join(t))
    return out


def update_notificationi_database(notification, origin_urls, resave_flag):
    nid = notification['id']
    sid = notification['status']['id']
    ntype = notification['type']
    url_list = origin_urls
    resave_flag = resave_flag
    if not get_notificationi(nid):
        insert_notification(nid, sid, ntype, url_list, resave_flag)
