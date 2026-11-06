from datetime import datetime, timedelta

import pytest

from donacion.domain.blood_request import BloodRequest, Hospital, RequestStatus, Urgency
from donacion.domain.blood_type import BloodType
from donacion.domain.errors import ConflictError, ValidationError
from donacion.domain.location import Location

from .conftest import HOSPITAL, NOW


@pytest.mark.parametrize("donor, recipient, expected", [
    ("O-", "AB+", True), ("O-", "A-", True), ("O+", "A+", True), ("O+", "A-", False),
    ("A-", "A+", True), ("A+", "A-", False), ("A+", "B+", False), ("B+", "AB+", True),
    ("AB+", "A+", False), ("AB-", "AB+", True),
])
def test_compatibilidad_abo_rh(donor, recipient, expected):
    assert BloodType.parse(donor).can_donate_to(BloodType.parse(recipient)) is expected


def test_tipo_de_sangre_invalido():
    with pytest.raises(ValidationError):
        BloodType.parse("C+")


def test_distancia_entre_ubicaciones():
    tlaquepaque = Location(20.6400, -103.3100)
    assert 5 < HOSPITAL.distance_km(tlaquepaque) < 8


def _request(units=2):
    return BloodRequest("r1", "Familia", BloodType.parse("A+"), units, Hospital("HC", HOSPITAL),
                        Urgency.CRITICAL, NOW + timedelta(hours=24), NOW)


def test_solicitud_se_cubre_al_confirmar_todas_las_unidades():
    request = _request(units=2)
    request.register_wave(["d1", "d2"], NOW)
    request.confirm_unit("d1")
    assert request.status is RequestStatus.OPEN
    request.confirm_unit("d2")
    assert request.status is RequestStatus.COVERED


def test_no_confirma_quien_no_recibio_alerta_ni_dos_veces():
    request = _request()
    request.register_wave(["d1"], NOW)
    with pytest.raises(ConflictError):
        request.confirm_unit("d9")
    request.confirm_unit("d1")
    with pytest.raises(ConflictError):
        request.confirm_unit("d1")


def test_solicitud_vence():
    request = _request()
    request.expire_if_needed(NOW + timedelta(hours=25))
    assert request.status is RequestStatus.EXPIRED
    assert not request.is_open()


def test_fecha_limite_debe_ser_futura():
    with pytest.raises(ValidationError):
        BloodRequest("r", "F", BloodType.parse("O+"), 1, Hospital("H", HOSPITAL),
                     Urgency.NORMAL, NOW, NOW)
