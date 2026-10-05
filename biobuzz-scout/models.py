from sqlalchemy import Column, Integer, String, Boolean, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(120), default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    scout_entries = relationship("ScoutEntry", back_populates="team")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    location = Column(String(200), default="")
    date = Column(String(50), default="")  # simple string for flexibility
    created_at = Column(DateTime, default=datetime.utcnow)

    matches = relationship("Match", back_populates="event", cascade="all, delete-orphan")


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    match_number = Column(Integer, nullable=False)
    match_type = Column(String(20), default="Qual")  # Qual, Practice, Elim
    red1 = Column(Integer, nullable=False)
    red2 = Column(Integer, nullable=False)
    blue1 = Column(Integer, nullable=False)
    blue2 = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="matches")
    scout_entries = relationship("ScoutEntry", back_populates="match", cascade="all, delete-orphan")


class ScoutEntry(Base):
    __tablename__ = "scout_entries"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    alliance = Column(String(10), nullable=False)  # red / blue
    scout_name = Column(String(80), default="")

    # Autonomous
    auto_leave = Column(Boolean, default=False)
    auto_park = Column(Boolean, default=False)
    auto_hive_tips = Column(Integer, default=0)
    auto_pollen = Column(Integer, default=0)
    auto_nectar = Column(Integer, default=0)

    # Teleop
    tele_hive_tips = Column(Integer, default=0)
    tele_pollen = Column(Integer, default=0)
    tele_nectar = Column(Integer, default=0)
    flower_owned = Column(Integer, default=0)  # number of flowers owned
    bottom_nectar_bonus = Column(Integer, default=0)  # 5 pts each
    garden_scored = Column(Integer, default=0)
    tele_park = Column(Boolean, default=False)

    # Reliability / "Robot Deaths"
    robot_deaths = Column(Integer, default=0)
    death_reasons = Column(Text, default="")  # e.g. "battery, code crash"
    disabled_time_sec = Column(Integer, default=0)

    # Qualitative
    driver_skill = Column(Integer, default=3)  # 1-5
    consistency = Column(Integer, default=3)  # 1-5
    intake_reliability = Column(Integer, default=3)
    notes = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow)

    match = relationship("Match", back_populates="scout_entries")
    team = relationship("Team", back_populates="scout_entries")

    @property
    def estimated_points(self) -> int:
        """Rough point contribution based on BIOBUZZ scoring."""
        pts = 0
        if self.auto_leave:
            pts += 3
        if self.auto_park:
            pts += 5
        pts += self.auto_hive_tips * 20
        # remaining in cell scored at end, but we approximate with auto elements * 2 if no tip
        pts += (self.auto_pollen + self.auto_nectar) * 2
        pts += self.tele_hive_tips * 20
        pts += (self.tele_pollen + self.tele_nectar) * 2  # cell remaining approx
        pts += self.flower_owned * 0  # ownership points are per element
        pts += self.bottom_nectar_bonus * 5
        pts += self.garden_scored * 1
        if self.tele_park:
            pts += 5
        return pts
