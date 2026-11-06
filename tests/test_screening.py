from datetime import date, timedelta

from donacion.domain.eligibility import EligibilityStatus, ScreeningAnswers
from donacion.screening.evaluator import ScreeningEvaluator
from donacion.screening.rules import (AgeRule, DonationIntervalRule, MedicationRule, PermanentExclusionRule,
                                      SurgeryRule, TattooRule, WeightRule)

from .conftest import make_donor

TODAY = date(2026, 11, 6)
EVALUATOR = ScreeningEvaluator([AgeRule(), WeightRule(), TattooRule(), SurgeryRule(), MedicationRule(),
                                DonationIntervalRule(), PermanentExclusionRule()])


def evaluate(donor=None, **answers):
    return EVALUATOR.evaluate(donor or make_donor(eligible=False), ScreeningAnswers(**answers), TODAY)


def test_donante_sin_impedimentos_es_apto():
    assert evaluate().status is EligibilityStatus.ELIGIBLE


def test_menor_de_edad_queda_diferido_hasta_cumplir_18():
    result = evaluate(make_donor(birth=date(2009, 3, 1), eligible=False))
    assert result.status is EligibilityStatus.DEFERRED
    assert result.eligible_from == date(2027, 3, 1)


def test_mayor_de_65_no_es_apto():
    assert evaluate(make_donor(birth=date(1950, 1, 1), eligible=False)).status is EligibilityStatus.INELIGIBLE


def test_peso_menor_a_50_no_es_apto():
    assert evaluate(make_donor(weight=49, eligible=False)).status is EligibilityStatus.INELIGIBLE


def test_tatuaje_reciente_difiere_12_meses():
    result = evaluate(tattoo_or_piercing_date=date(2026, 8, 6))
    assert result.status is EligibilityStatus.DEFERRED
    assert result.eligible_from == date(2027, 8, 6)


def test_tatuaje_de_hace_mas_de_un_anio_no_afecta():
    assert evaluate(tattoo_or_piercing_date=date(2025, 1, 1)).status is EligibilityStatus.ELIGIBLE


def test_varios_diferimientos_toma_la_fecha_mas_lejana():
    result = evaluate(surgery_date=date(2026, 10, 1), medication_end_date=TODAY - timedelta(days=1))
    assert result.status is EligibilityStatus.DEFERRED
    assert result.eligible_from == date(2027, 4, 1)
    assert len(result.reasons) == 2


def test_donacion_reciente_difiere_56_dias():
    result = evaluate(make_donor(last_donation=TODAY - timedelta(days=10), eligible=False))
    assert result.eligible_from == TODAY + timedelta(days=46)


def test_exclusion_permanente_gana_sobre_diferimiento():
    result = evaluate(permanent_exclusion=True, tattoo_or_piercing_date=TODAY)
    assert result.status is EligibilityStatus.INELIGIBLE


def test_ningun_diferido_aparece_como_apto_el_dia_anterior():
    result = evaluate(medication_end_date=TODAY)
    assert not result.allows_donation_on(TODAY + timedelta(days=4))
    assert result.allows_donation_on(TODAY + timedelta(days=5))
