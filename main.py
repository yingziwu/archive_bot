# archive bot

import logging

import archiveOrg
import db
import mstdn

logging.basicConfig(filename='archive_bot.log',
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(filename)s %(lineno)d %(message)s')


def get_urls():
    return mstdn.get_notification(db.get_max_nid())


def run():
    logging.info('Start.')
    url_dicts = get_urls()
    if len(url_dicts) == 0:
        return

    for k in url_dicts:
        sid, url_dict = k, url_dicts[k]
        origin_urls, resave_flag = url_dict['origin'], url_dict['resave_flag']

        if url_dict.get('nid'):
            nid = url_dict['nid']

        logging.info('sid: {}, origin_urls: {}, resave_flag: {}'
                     .format(str(sid), ' ,'.join(origin_urls), str(resave_flag)))
        # archive urls
        archive_map = {}
        for url in origin_urls:
            try:
                if resave_flag:
                    archive_url = archiveOrg.save_archive_url(url)
                    db.insert_archive_url(url, archive_url)
                elif db.get_archive_url(url):
                    archive_url = db.get_archive_url(url)[0]
                else:
                    archive_url = archiveOrg.get_archive_url(url)
                    db.insert_archive_url(url, archive_url)
            except archiveOrg.ArchiveError as e:
                logging.error(e)
                if url_dict.get('nid'):
                    db.insert_failed(nid, 0)
                continue
            except Exception as e:
                logging.error(e)
                if url_dict.get('nid'):
                    db.insert_failed(nid, 0)
                continue
            archive_map[url] = archive_url

        # generate toot text
        toot_text = ''
        logging.debug('generate toot text: {}'.format(str(archive_map)))
        for au in archive_map:
            toot_text = toot_text + '\n' + '\n'.join((au, archive_map[au])) + '\n'

        try:
            if len(archive_map) == 0:
                raise ValueError('Somewher error.')

            mstdn.post_reply_status(sid, toot_text)
            db.insert_finish(sid, archive_map, toot_text)
        except Exception as e:
            logging.error(e)
            if url_dict.get('nid'):
                db.insert_failed(nid, 0)


if __name__ == '__main__':
    run()
