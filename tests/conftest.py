from datetime import date, datetime

import pytest

from donacion.adapters.system_clock import ManualClock
from donacion.domain.blood_type import BloodType
from donacion.domain.donor import Donor
from donacion.domain.eligibility import EligibilityResult, EligibilityStatus
from donacion.domain.location import Location

HOSPITAL = Location(20.6866, -103.3496)
NOW = datetime(2026, 11, 6, 10, 0)


@pytest.fixture
def clock() -> ManualClock:
    return ManualClock(NOW)


def make_donor(donor_id="d1", blood="A+", lat=20.69, lon=-103.35, birth=date(1995, 1, 1),
               weight=65, last_donation=None, eligible=True) -> Donor:
    donor = Donor(donor_id, f"Donante {donor_id}", f"{donor_id}@demo.mx", "hash", birth, weight,
                  BloodType.parse(blood), Location(lat, lon), last_donation)
    if eligible:
        donor.update_eligibility(EligibilityResult(EligibilityStatus.ELIGIBLE))
    return donor
