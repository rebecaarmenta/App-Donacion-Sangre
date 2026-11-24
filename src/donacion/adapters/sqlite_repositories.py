"""Repositorios y registro de alertas sobre SQLite.

Implementan los mismos puertos que los adaptadores en memoria (DonorRepository,
RequestRepository, AlertLog): los servicios no saben cuál se usa. Cada clase traduce entre
filas de la base de datos y objetos del dominio, que se reconstruyen con su método restore().
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime

from ..domain.alert import Alert
from ..domain.blood_request import BloodRequest, Hospital, RequestStatus, Urgency
from ..domain.blood_type import BloodType
from ..domain.donation import DonationRecord
from ..domain.donor import Donor
from ..domain.eligibility import EligibilityResult, EligibilityStatus
from ..domain.location import Location
from ..domain.response_history import ResponseHistory
from ..ports.alert_log import AlertLog
from ..ports.repositories import DonorRepository, RequestRepository
from .sqlite_database import SqliteDatabase


def _date(text: str | None) -> date | None:
    return date.fromisoformat(text) if text else None


def _datetime(text: str | None) -> datetime | None:
    return datetime.fromisoformat(text) if text else None


def _iso(value: date | datetime | None) -> str | None:
    return value.isoformat() if value else None


class SqliteDonorRepository(DonorRepository):
    def __init__(self, db: SqliteDatabase) -> None:
        self._db = db

    def save(self, donor: Donor) -> None:
        e, h = donor.eligibility, donor.response_history
        with self._db.transaction() as c:
            c.execute(
                """INSERT INTO donors (id, name, email, password_hash, birth_date, weight_kg, blood_type,
                       lat, lon, last_donation, eligibility, eligibility_reasons, eligible_from,
                       alerts_received, alerts_accepted)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                       name = excluded.name, email = excluded.email, password_hash = excluded.password_hash,
                       birth_date = excluded.birth_date, weight_kg = excluded.weight_kg,
                       blood_type = excluded.blood_type, lat = excluded.lat, lon = excluded.lon,
                       last_donation = excluded.last_donation, eligibility = excluded.eligibility,
                       eligibility_reasons = excluded.eligibility_reasons,
                       eligible_from = excluded.eligible_from, alerts_received = excluded.alerts_received,
                       alerts_accepted = excluded.alerts_accepted""",
                (donor.id, donor.name, donor.email, donor.password_hash, _iso(donor.birth_date),
                 donor.weight_kg, str(donor.blood_type), donor.location.lat, donor.location.lon,
                 _iso(donor.last_donation), e.status.value, json.dumps(list(e.reasons), ensure_ascii=False),
                 _iso(e.eligible_from), h.received, h.accepted))
            c.execute("DELETE FROM donations WHERE donor_id = ?", (donor.id,))
            c.executemany(
                "INSERT INTO donations (donor_id, position, day, request_id, hospital) VALUES (?, ?, ?, ?, ?)",
                [(donor.id, i, _iso(r.day), r.request_id, r.hospital) for i, r in enumerate(donor.donations)])

    def get(self, donor_id: str) -> Donor | None:
        return self._one("SELECT * FROM donors WHERE id = ?", (donor_id,))

    def find_by_email(self, email: str) -> Donor | None:
        return self._one("SELECT * FROM donors WHERE email = ?", (email.strip().lower(),))

    def list_all(self) -> list[Donor]:
        with self._db.transaction() as c:
            rows = c.execute("SELECT * FROM donors ORDER BY rowid").fetchall()
            return [self._to_donor(c, row) for row in rows]

    def _one(self, sql: str, params: tuple) -> Donor | None:
        with self._db.transaction() as c:
            row = c.execute(sql, params).fetchone()
            return self._to_donor(c, row) if row else None

    @staticmethod
    def _to_donor(c: sqlite3.Connection, row: sqlite3.Row) -> Donor:
        donations = tuple(
            DonationRecord(_date(d["day"]), d["request_id"], d["hospital"])
            for d in c.execute("SELECT * FROM donations WHERE donor_id = ? ORDER BY position", (row["id"],)))
        return Donor.restore(
            donor_id=row["id"], name=row["name"], email=row["email"], password_hash=row["password_hash"],
            birth_date=_date(row["birth_date"]), weight_kg=row["weight_kg"],
            blood_type=BloodType.parse(row["blood_type"]), location=Location(row["lat"], row["lon"]),
            last_donation=_date(row["last_donation"]),
            eligibility=EligibilityResult(EligibilityStatus(row["eligibility"]),
                                          tuple(json.loads(row["eligibility_reasons"])),
                                          _date(row["eligible_from"])),
            history=ResponseHistory(row["alerts_received"], row["alerts_accepted"]),
            donations=donations,
        )


class SqliteRequestRepository(RequestRepository):
    def __init__(self, db: SqliteDatabase) -> None:
        self._db = db

    def save(self, request: BloodRequest) -> None:
        with self._db.transaction() as c:
            c.execute(
                """INSERT INTO requests (id, requester_name, blood_type, units_needed, hospital_name,
                       hospital_lat, hospital_lon, urgency, deadline, created_at, status,
                       notified_donors, confirmed_donors, waves_sent, last_wave_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                       status = excluded.status, notified_donors = excluded.notified_donors,
                       confirmed_donors = excluded.confirmed_donors, waves_sent = excluded.waves_sent,
                       last_wave_at = excluded.last_wave_at""",
                (request.id, request.requester_name, str(request.blood_type), request.units_needed,
                 request.hospital.name, request.hospital.location.lat, request.hospital.location.lon,
                 request.urgency.value, _iso(request.deadline), _iso(request.created_at),
                 request.status.value, json.dumps(list(request.notified_donors)),
                 json.dumps(list(request.confirmed_donors)), request.waves_sent, _iso(request.last_wave_at)))

    def get(self, request_id: str) -> BloodRequest | None:
        with self._db.transaction() as c:
            row = c.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
        return self._to_request(row) if row else None

    def list_open(self) -> list[BloodRequest]:
        with self._db.transaction() as c:
            rows = c.execute("SELECT * FROM requests WHERE status = ? ORDER BY rowid",
                             (RequestStatus.OPEN.value,)).fetchall()
        return [self._to_request(row) for row in rows]

    @staticmethod
    def _to_request(row: sqlite3.Row) -> BloodRequest:
        return BloodRequest.restore(
            request_id=row["id"], requester_name=row["requester_name"],
            blood_type=BloodType.parse(row["blood_type"]), units_needed=row["units_needed"],
            hospital=Hospital(row["hospital_name"], Location(row["hospital_lat"], row["hospital_lon"])),
            urgency=Urgency(row["urgency"]), deadline=_datetime(row["deadline"]),
            created_at=_datetime(row["created_at"]), status=RequestStatus(row["status"]),
            notified_donors=tuple(json.loads(row["notified_donors"])),
            confirmed_donors=tuple(json.loads(row["confirmed_donors"])),
            waves_sent=row["waves_sent"], last_wave_at=_datetime(row["last_wave_at"]),
        )


class SqliteAlertLog(AlertLog):
    def __init__(self, db: SqliteDatabase) -> None:
        self._db = db

    def record(self, alert: Alert) -> None:
        with self._db.transaction() as c:
            c.execute("""INSERT INTO alerts (request_id, donor_id, donor_name, wave, score, message)
                         VALUES (?, ?, ?, ?, ?, ?)""",
                      (alert.request_id, alert.donor_id, alert.donor_name, alert.wave, alert.score, alert.message))

    def for_donor(self, donor_id: str) -> list[Alert]:
        return self._select("donor_id", donor_id)

    def for_request(self, request_id: str) -> list[Alert]:
        return self._select("request_id", request_id)

    def _select(self, column: str, value: str) -> list[Alert]:
        # column solo puede ser una de las dos constantes de arriba: no viene del usuario.
        with self._db.transaction() as c:
            rows = c.execute(f"SELECT * FROM alerts WHERE {column} = ? ORDER BY id", (value,)).fetchall()
        return [Alert(r["request_id"], r["donor_id"], r["donor_name"], r["wave"], r["score"], r["message"])
                for r in rows]
