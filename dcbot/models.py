
#
# Models
#

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Boolean

from .db import Base


class Member(Base):
    __tablename__ = "members"

    id = Column(String(9), primary_key=True)
    name = Column(String(100))
    real_name = Column(String(100))
    display_name = Column(String(100))

    def __init__(self, id_, name, real_name, display_name):
        self.id = id_
        self.name = name
        self.real_name = real_name
        self.display_name = display_name

    def __repr__(self):
        return "<Member %s [%s]>" % (self.id, self.display_name)


class Group(Base):
    __tablename__ = "groups"

    id = Column(String(9), primary_key=True)
    name = Column(String(100))
    service_host_member_id = Column(String(9), ForeignKey('members.id'), nullable=True)
    archived = Column(Boolean(), default=False)

    def __init__(self, id_, name, archived=False):
        self.id = id_
        self.name = name
        self.archived = archived


class RecentMemberMessage(Base):
    __tablename__ = "recent_member_messages"

    member_id = Column(String(9), ForeignKey('members.id'), primary_key=True)
    group_id = Column(String(9), ForeignKey('groups.id'), primary_key=True)
    recent_post_at = Column(DateTime(), nullable=True)

    def __init__(self, member_id, group_id, recent_post_at=None):
        self.member_id = member_id
        self.group_id = group_id
        self.recent_post_at = recent_post_at


class CTFFloorStatus(Base):
    __tablename__ = "ctf_floor_status"

    member_id = Column(String(9), ForeignKey('members.id'), primary_key=True)
    status = Column(Integer())
    recent_on_floor_at = Column(DateTime(), nullable=True)

    def __init__(self, member_id, status):
        self.member_id = member_id
        self.status = status
        self.recent_on_floor_at = None
