# database related function
import json
import re
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, TypeDecorator
from sqlalchemy import create_engine, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

engine = create_engine('sqlite:///cache.db', echo=False)
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()
schema_version = 1


class JSON(TypeDecorator):
    impl = String

    def process_bind_param(self, value, dialect):
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        return json.loads(value)


class URL(Base):
    __tablename__ = 'url'

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, index=True)
    archive_url = Column(String)
    info = Column(JSON)
    time_created = Column(TIMESTAMP, nullable=False, default=datetime.now())

    def __repr__(self):
        return "<URL(url='{}', archive_url='{}')>".format(self.url, self.archive_url)


class NOTIFICATIONS(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nid = Column(Integer, nullable=False, index=True)
    sid = Column(Integer, nullable=False, index=True)
    ntype = Column(String, nullable=False, index=True)
    url_list = Column(JSON, nullable=True)
    resave_flag = Column(Boolean, nullable=False)
    time_created = Column(TIMESTAMP, nullable=False, default=datetime.now())

    def __repr__(self):
        return "<Notification (nid={}, url_list={})>".format(self.nid, self.url_list.as_string())


class FAILED(Base):
    __tablename__ = 'failed'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nid = Column(Integer, nullable=False, index=True)
    retry_times = Column(Integer, default=0)
    time_created = Column(TIMESTAMP, nullable=False, default=datetime.now())
    time_updated = Column(TIMESTAMP, nullable=True, default=None)


class FINISH(Base):
    __tablename__ = 'finish'

    id = Column(Integer, primary_key=True, autoincrement=True)
    sid = Column(Integer, nullable=False, index=True)
    url_dict = Column(JSON, nullable=True)
    toot_text = Column(String, nullable=True)
    time_created = Column(TIMESTAMP, nullable=False, default=datetime.now())
    time_updated = Column(TIMESTAMP, nullable=True, default=None)


class MEAT(Base):
    __tablename__ = 'meta'

    meta_name = Column(String, primary_key=True)
    meta_content = Column(String)


def insert_notification(nid, sid, ntype, url_list, resave_flag):
    notification = NOTIFICATIONS(nid=nid, sid=sid, ntype=ntype, url_list=url_list, resave_flag=resave_flag)
    session.add(notification)
    session.commit()


def get_max_nid():
    try:
        return session.query(NOTIFICATIONS.nid).order_by(desc(NOTIFICATIONS.nid)).first()
    except NoResultFound:
        return None


def get_notificationi(nid):
    try:
        return session.query(NOTIFICATIONS.sid, NOTIFICATIONS.ntype, NOTIFICATIONS.url_list, NOTIFICATIONS.resave_flag) \
            .filter(NOTIFICATIONS.nid == nid).one()
    except NoResultFound:
        return None


def insert_archive_url(url, archive_url, info=None):
    url = re.sub(r'^https?://', '', url)
    url_ob = URL(url=url, archive_url=archive_url, info=info)
    session.add(url_ob)
    session.commit()


def get_archive_url(url):
    url = re.sub(r'^https?://', '', url)
    try:
        return session.query(URL.archive_url).filter(URL.url == url) \
            .order_by(desc(URL.time_created)).first()
    except NoResultFound:
        return None


def insert_failed(nid, retry_times):
    failed = FAILED(nid=nid, retry_times=retry_times)
    session.add(failed)
    session.commit()


def get_failed():
    try:
        return session.query(FAILED.nid, NOTIFICATIONS.ntype, NOTIFICATIONS.sid, NOTIFICATIONS.url_list,
                             NOTIFICATIONS.url_list) \
            .filter(FAILED.nid == NOTIFICATIONS.nid) \
            .all()
    except NoResultFound:
        return []


def insert_finish(sid, url_dict, toot_text):
    finish = FINISH(sid=sid, url_dict=url_dict, toot_text=toot_text)
    session.add(finish)
    session.commit()


def get_finish_by_sid(sid):
    try:
        return session.query(FINISH.sid, FINISH.url_dict).filter(FAILED.sid == sid) \
            .order_by(desc(URL.time_created)).first()
    except NoResultFound:
        return None


if __name__ == '__main__':
    import argparse


    def create_schema():
        Base.metadata.create_all(engine)
        session.add(MEAT(meta_name='version', meta_content=str(schema_version)))
        session.commit()


    parser = argparse.ArgumentParser()
    parser.add_argument('--init', help='init database schema', action="store_true")
    args = parser.parse_args()
    if args.init:
        create_schema()
