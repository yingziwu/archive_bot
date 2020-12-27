# archive - archive.org

import logging
import os.path as path
import re
import time
from json import JSONDecodeError

import requests

from config import HEADERS, TIMEOUT
from lib import get_location


def get_archive_url(url):
    logging.info('get_archive_url: {}'.format(url))
    archive = ArchiveOrg(url)
    try:
        archive.query()
        logging.info('archive_url: {}'.format(archive.recent_version_url))
        return archive.recent_version_url
    except ArchiveError as e:
        logging.error(e)
        time.sleep(2)
        try:
            archive.archive()
        except Exception as e:
            logging.error(e)
            raise e

        logging.info('archive_url: {}'.format(archive.save_archive_url))
        return archive.save_archive_url


def save_archive_url(url):
    logging.info('save_archive_url: {}'.format(url))
    archive = ArchiveOrg(url)
    try:
        archive.archive()
    except Exception as e:
        raise e

    logging.info('archive_url: {}'.format(archive.save_archive_url))
    return archive.save_archive_url


class ArchiveError(ValueError):
    pass


class ArchiveOrg:
    """
    :param url: (str) URL to be archived
    """

    def __init__(self, url):
        self.url = url
        self._baseUrl = 'https://web.archive.org'

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        if any((value.startswith('http://'), value.startswith('https://'))):
            self._url = value
            return
        else:
            raise requests.exceptions.InvalidURL

    def query(self):
        def query_archive_url(url):
            """
            Query archive url from web archive
            :param url: (str) original url
            :returns locatioin: (str) archive url
            :returns timestamp: (str) archive version timestamp
            """
            logging.debug('Start query archive: {}'.format(url))
            status, resp, locatioin = get_location(url)
            if status and resp.headers.get('x-archive-redirect-reason'):
                redirect_reason = resp.headers['x-archive-redirect-reason']
                match = re.search(r'\d+$', redirect_reason)
                timestamp = match.group()
                return locatioin, timestamp
            else:
                raise ArchiveError('Not found archive')

        first_query = path.join(self._baseUrl, 'web', '0', self.url)
        recent_query = path.join(self._baseUrl, 'web', '2', self.url)

        try:
            self.first_version_url, self.first_version_timestamp = query_archive_url(first_query)
            self.recent_version_url, self.recent_version_timestamp = query_archive_url(recent_query)

            return (self.first_version_url, self.first_version_timestamp), \
                   (self.recent_version_url, self.recent_version_timestamp)
        except ArchiveError as e:
            logging.info('Not found archive')
            raise e

    def archive(self):
        s = requests.Session()
        s.headers = HEADERS
        s.get(path.join(self._baseUrl, 'save'), timeout=TIMEOUT)

        def submit():
            """
            submit archive post request
            :return resp: (requests.Response)
            """
            payload = {'url': self.url,
                       'capture_all': 'on'}
            logging.info('Submit archive url post.')
            resp = s.post(path.join(self._baseUrl, 'save', self.url),
                          headers={'Origin': self._baseUrl},
                          data=payload,
                          timeout=TIMEOUT)
            return resp

        def extract_uuid(html):
            """
            extract uuid from html textt
            :param html: (str) html text
            :return uuid: (str) job uuid
            """
            match = re.search(r'spn\.watchJob\("([\w\-]+)', html)
            if match:
                uuid = match.groups()[0]
                return uuid
            else:
                logging.error('Extracting uuid failed! Something went wrong.')
                logging.debug(html)
                raise ArchiveError('Extracting uuid failed! Something went wrong.')

        def extract_archive_url(uuid):
            """
            extract archive url from event url
            :param uuid: (str) job uuid
            :return:
            """
            status_url = path.join(self._baseUrl, 'save', 'status', uuid)
            current_status = 'pending'

            while current_status != 'success':
                time.sleep(2)
                resp = s.get(status_url,
                             params={'_t': int(time.time())},
                             headers={'X-Requested-With': 'XMLHttpRequest'},
                             timeout=TIMEOUT)
                try:
                    rj = resp.json()
                except JSONDecodeError:
                    time.sleep(2)
                    continue
                current_status = rj['status']
                if current_status == 'success':
                    if rj.get('first_archive'):
                        first_archive = True
                    else:
                        first_archive = False
                    timestamp = rj['timestamp']
                    duration_sec = rj['duration_sec']
                    original_url = rj['original_url']
                    archive_url = path.join(self._baseUrl, 'web', timestamp, original_url)

                    logging.info('{}: The archive is complete, it takes {} seconds. Is first archive? {}'.format(
                        original_url, duration_sec, first_archive))
                    return first_archive, archive_url
                elif current_status == 'error':
                    message = rj['message']
                    error_message = 'Archive failed! {}'.format(message)
                    logging.error(error_message)
                    raise ArchiveError(error_message)

        try:
            sresp = submit()
            time.sleep(3)
            if sresp.ok:
                event_uuid = extract_uuid(sresp.text)
                self.save_first_archive, self.save_archive_url = extract_archive_url(event_uuid)
            else:
                logging.error('Submit failed! ')
                raise ArchiveError('Submit failed! ' + str(sresp))
        except Exception as e:
            logging.error(e)
            raise e


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Get URL archvie.')
    parser.add_argument('url', type=str, help='URL')
    parser.add_argument('--resave', help='force resave webpage', action='store_true', default=False)
    args = parser.parse_args()


    def run(url, resave):
        if resave:
            print(save_archive_url(url))
        else:
            print(get_archive_url(url))


    run(args.url, args.resave)
