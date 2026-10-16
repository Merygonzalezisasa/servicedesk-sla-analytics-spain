"""
reloj_sla.py — El reloj del SLA de Brújula Soporte IT (Ficha §0.1).

Dos relojes:
    · 24x7     (P1): cuenta todos los minutos.
    · laboral  (P2–P4): solo de lunes a viernes, 09:00–18:00, sin los festivos de Madrid.

Truco para que sea rápido: cada instante se traduce a una "posición" = minutos de reloj transcurridos
desde el inicio del calendario. Sumar tiempo de SLA es sumar a la posición, y la diferencia entre dos
posiciones son los minutos de SLA consumidos. Fuera de horario la posición no avanza.

Simplificación declarada: las horas son locales de Madrid y no se corrige el cambio de hora (un P1 que
cruza la noche del cambio puede ganar o perder 60 minutos).
"""

from bisect import bisect_left
from datetime import date, datetime, time, timedelta

HORA_INICIO, HORA_FIN = 9, 18
MIN_DIA = (HORA_FIN - HORA_INICIO) * 60  # 540 minutos laborables por día


class RelojLaboral:
    """Reloj de L–V 09:00–18:00 sin festivos. `laborables` = días que cuentan."""

    def __init__(self, laborables: set[date], desde: date, hasta: date):
        self.d0 = desde
        self.dias = [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]
        self.es_lab = [d in laborables for d in self.dias]
        # Minutos de reloj acumulados al empezar cada día.
        self.cum, total = [], 0
        for lab in self.es_lab:
            self.cum.append(total)
            total += MIN_DIA if lab else 0
        self.lab_idx = [i for i, lab in enumerate(self.es_lab) if lab]
        self.lab_cum = [self.cum[i] for i in self.lab_idx]

    def pos(self, dt: datetime) -> int:
        """Minutos de reloj desde el inicio del calendario hasta dt."""
        i = (dt.date() - self.d0).days
        if not self.es_lab[i]:
            return self.cum[i]
        dentro = (dt.hour - HORA_INICIO) * 60 + dt.minute
        return self.cum[i] + min(max(dentro, 0), MIN_DIA)

    def instante(self, p: int) -> datetime:
        """Inverso de pos. Un final de jornada exacto se lee como las 18:00 (no las 09:00 siguientes)."""
        k = max(bisect_left(self.lab_cum, p) - 1, 0)
        dia = self.dias[self.lab_idx[k]]
        return datetime.combine(dia, time(HORA_INICIO)) + timedelta(minutes=p - self.lab_cum[k])

    def sumar(self, dt: datetime, minutos: int) -> datetime:
        return self.instante(self.pos(dt) + minutos)

    def minutos(self, desde: datetime, hasta: datetime) -> int:
        return self.pos(hasta) - self.pos(desde)


class Reloj24x7:
    """Reloj que no se detiene nunca (P1). Misma interfaz que RelojLaboral."""

    def __init__(self, desde: date):
        self.t0 = datetime.combine(desde, time(0))

    def pos(self, dt: datetime) -> int:
        return int((dt - self.t0).total_seconds() // 60)

    def instante(self, p: int) -> datetime:
        return self.t0 + timedelta(minutes=p)

    def sumar(self, dt: datetime, minutos: int) -> datetime:
        return dt + timedelta(minutes=minutos)

    def minutos(self, desde: datetime, hasta: datetime) -> int:
        return self.pos(hasta) - self.pos(desde)


if __name__ == "__main__":
    # Pregunta de control de la Ficha §0.1: P2 abierto el viernes a las 17:30 con el lunes festivo
    # → el martes a las 10:00 lleva 1 h 30 min. (Viernes 2024-03-15; lunes 18 tratado como festivo.)
    lab = {date(2024, 3, 15), date(2024, 3, 19)}
    reloj = RelojLaboral(lab, date(2024, 3, 15), date(2024, 3, 20))
    consumido = reloj.minutos(datetime(2024, 3, 15, 17, 30), datetime(2024, 3, 19, 10, 0))
    assert consumido == 90, consumido
    assert reloj.sumar(datetime(2024, 3, 15, 17, 30), 90) == datetime(2024, 3, 19, 10, 0)
    assert reloj.sumar(datetime(2024, 3, 15, 20, 0), 30) == datetime(2024, 3, 19, 9, 30)
    print(f"Ejemplo de control: {consumido // 60} h {consumido % 60} min consumidos (OK)")
