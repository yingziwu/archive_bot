# Mastodn related function

import logging

from lxml import etree
from mastodon import Mastodon, MastodonNotFoundError, MastodonIOError

from config import TOKEN, BASE_DOMAIN, MAX_TOOT_CHARS
from lib import domain_filter, text_split, update_notificationi_database

if not all((TOKEN, BASE_DOMAIN)):
    logging.error('Not Set access_token or api_base_domain')
    raise ValueError('Not Set access_token or api_base_domain')

m = Mastodon(
    access_token=TOKEN,
    api_base_url='https://{}'.format(BASE_DOMAIN)
)


def parse_urls(status, urls):
    content = status['content']
    tree = etree.HTML(content)
    a_nodes = tree.xpath('//a')
    for a_node in a_nodes:
        href = a_node.xpath('./@href')[0]
        _a_class = a_node.xpath('./@class')
        if len(_a_class) == 0:
            urls.append(href)
        else:
            a_class = set(_a_class[0].split(' '))
            bclass = {'mention', 'u-url', 'hashtag'}
            if len(bclass.intersection(a_class)) == 0:
                urls.append(href)

    if status.get('in_reply_to_id'):
        parent_id = status.get('in_reply_to_id')
        try:
            parent = m.status(parent_id)
        except MastodonNotFoundError:
            return urls
        else:
            return parse_urls(parent, urls)
    else:
        return urls


def urls_prehook(urls):
    urls = list(set(urls))
    urls = list(filter(domain_filter, urls))
    return urls


def get_notification(since_id=None):
    notifications = m.notifications(limit=100, since_id=since_id)
    notifications = tuple(filter(lambda x: x['type'] == 'mention', notifications))

    url_dict = {}
    for notification in notifications:
        resave_flag = False
        try:
            if '/resave' in notification['status']['content']:
                resave_flag = True
            origin_urls = urls_prehook(parse_urls(notification['status'], []))
            update_notificationi_database(notification, origin_urls, resave_flag)
        except MastodonIOError:
            origin_urls = MastodonIOError

        url_dict[notification['status']['id']] = {'origin': origin_urls, 'resave_flag': resave_flag,
                                                  'nid': notification['id']}

    return url_dict


def post_reply_status(sid, status_text):
    to_status = m.status(sid)
    if len(status_text) > MAX_TOOT_CHARS:
        chunks = text_split(status_text, MAX_TOOT_CHARS)
        for c in chunks:
            to_status = m.status_reply(to_status, c)
    else:
        m.status_reply(to_status, status_text)


if __name__ == '__main__':
    import argparse


    def run(sid):
        urls = urls_prehook(parse_urls(m.status(sid), []))
        for url in urls:
            print(url)


    parser = argparse.ArgumentParser(description='parse url from status.')
    parser.add_argument('sid', help='status id', type=int)
    args = parser.parse_args()
    run(args.sid)
