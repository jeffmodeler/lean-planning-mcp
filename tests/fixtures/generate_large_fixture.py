"""Generate a large MSPDI XML fixture (~200 tasks) for load/scale testing.

Usage:  python generate_large_fixture.py [output.xml]

Produces a realistic multi-block residential project: 4 blocks x 6 phases
x 8 activities, plus site-wide phases, milestones, FS links, 8 resources
and assignments. Deterministic output (no randomness).
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta

WORKDAY_START = "T08:00:00"
WORKDAY_END = "T17:00:00"

PHASES = [
    ("Fundacoes", ["Locacao", "Escavacao", "Apiloamento", "Armacao sapatas",
                   "Formas sapatas", "Concretagem sapatas", "Baldrames",
                   "Impermeabilizacao"]),
    ("Estrutura", ["Pilares terreo", "Vigas terreo", "Laje terreo",
                   "Pilares superior", "Vigas superior", "Laje superior",
                   "Escada", "Cura e desforma"]),
    ("Alvenaria", ["Marcacao", "Elevacao terreo", "Elevacao superior",
                   "Vergas e contravergas", "Encunhamento", "Requadros",
                   "Muretas", "Platibanda"]),
    ("Instalacoes", ["Hidraulica terreo", "Hidraulica superior",
                     "Eletrica terreo", "Eletrica superior", "Esgoto",
                     "Aguas pluviais", "Gas", "Testes de estanqueidade"]),
    ("Revestimentos", ["Chapisco", "Reboco interno", "Reboco externo",
                       "Contrapiso", "Ceramica pisos", "Ceramica paredes",
                       "Forro de gesso", "Peitoris e soleiras"]),
    ("Acabamentos", ["Massa corrida", "Pintura interna", "Pintura externa",
                     "Esquadrias", "Loucas e metais", "Bancadas",
                     "Limpeza fina", "Vistoria do bloco"]),
]

RESOURCES = [
    (1, "Equipe Fundacoes", 85), (2, "Equipe Estrutura", 95),
    (3, "Equipe Alvenaria", 75), (4, "Equipe Hidraulica", 90),
    (5, "Equipe Eletrica", 90), (6, "Equipe Revestimentos", 70),
    (7, "Equipe Acabamentos", 72), (8, "Mestre de Obras", 120),
]
# phase index -> resource uid
PHASE_RESOURCE = {0: 1, 1: 2, 2: 3, 3: 4, 4: 6, 5: 7}

DAYS_PER_ACTIVITY = 5  # one work-week each
HOURS = DAYS_PER_ACTIVITY * 8


def add_workdays(d: datetime, days: int) -> datetime:
    while days > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            days -= 1
    return d


def task_xml(uid, name, level, outline, summary, milestone, critical,
             start, finish, hours, preds, baseline_shift_days=0):
    lines = [
        "    <Task>",
        f"      <UID>{uid}</UID><ID>{uid}</ID>",
        f"      <Name>{name}</Name>",
        f"      <Type>{1 if summary else 0}</Type><IsNull>0</IsNull>",
        f"      <OutlineLevel>{level}</OutlineLevel><OutlineNumber>{outline}</OutlineNumber>",
        f"      <Summary>{1 if summary else 0}</Summary>"
        f"<Critical>{1 if critical else 0}</Critical>"
        f"<Milestone>{1 if milestone else 0}</Milestone>",
        f"      <Start>{start:%Y-%m-%d}{WORKDAY_START}</Start>"
        f"<Finish>{finish:%Y-%m-%d}{WORKDAY_END}</Finish>",
        f"      <Duration>PT{hours}H0M0S</Duration><Work>PT{hours * 2}H0M0S</Work>",
        "      <PercentComplete>0</PercentComplete><Priority>500</Priority>",
    ]
    for p in preds:
        lines.append(
            f"      <PredecessorLink><PredecessorUID>{p}</PredecessorUID>"
            "<Type>1</Type><LinkLag>0</LinkLag></PredecessorLink>"
        )
    if not summary and not milestone and baseline_shift_days >= 0:
        b_start = start
        b_finish = add_workdays(finish, -baseline_shift_days) if baseline_shift_days else finish
        lines.append(
            f"      <Baseline><Start>{b_start:%Y-%m-%d}{WORKDAY_START}</Start>"
            f"<Finish>{b_finish:%Y-%m-%d}{WORKDAY_END}</Finish>"
            f"<Duration>PT{hours}H0M0S</Duration></Baseline>"
        )
    lines.append("    </Task>")
    return "\n".join(lines)


def main(out_path: str, blocks: int = 4) -> None:
    start0 = datetime(2026, 8, 3)
    tasks, assignments = [], []
    uid = 0
    a_uid = 0

    project_start = start0
    # Placeholder for root; finish patched at the end
    root_index = len(tasks)
    tasks.append(None)
    uid += 1

    block_finish_uids = []
    project_finish = start0
    for b in range(1, blocks + 1):
        block_uid = uid
        block_start = add_workdays(start0, (b - 1) * 15)  # staggered blocks
        cursor = block_start
        block_task_index = len(tasks)
        tasks.append(None)  # placeholder for block summary
        uid += 1
        prev_phase_last = None
        for pi, (phase, acts) in enumerate(PHASES):
            phase_uid = uid
            phase_index = len(tasks)
            tasks.append(None)  # placeholder for phase summary
            uid += 1
            phase_start = cursor
            prev = prev_phase_last
            for ai, act in enumerate(acts):
                t_start = cursor
                t_finish = add_workdays(t_start, DAYS_PER_ACTIVITY - 1)
                preds = [prev] if prev else []
                critical = b == 1  # block 1 drives the critical path
                tasks.append(task_xml(
                    uid, f"B{b} - {act}", 3, f"{b}.{pi + 1}.{ai + 1}",
                    False, False, critical, t_start, t_finish, HOURS, preds,
                    baseline_shift_days=1 if (ai % 4 == 0) else 0,
                ))
                res = PHASE_RESOURCE[pi]
                a_uid += 1
                assignments.append(
                    f"    <Assignment><UID>{a_uid}</UID><TaskUID>{uid}</TaskUID>"
                    f"<ResourceUID>{res}</ResourceUID><Units>1</Units>"
                    f"<Work>PT{HOURS * 2}H0M0S</Work><Cost>{HOURS * 2 * 80}</Cost>"
                    f"<Start>{t_start:%Y-%m-%d}{WORKDAY_START}</Start>"
                    f"<Finish>{t_finish:%Y-%m-%d}{WORKDAY_END}</Finish></Assignment>"
                )
                prev = uid
                uid += 1
                cursor = add_workdays(t_finish, 1)
            prev_phase_last = prev
            tasks[phase_index] = task_xml(
                phase_uid, f"B{b} - {phase}", 2, f"{b}.{pi + 1}", True, False,
                b == 1, phase_start, add_workdays(cursor, -1),
                len(acts) * HOURS, [],
            )
        # block milestone
        m_finish = add_workdays(cursor, -1)
        tasks.append(task_xml(
            uid, f"Marco: Bloco {b} concluido", 2, f"{b}.7", False, True,
            b == 1, m_finish, m_finish, 0, [prev_phase_last],
        ))
        block_finish_uids.append(uid)
        uid += 1
        tasks[block_task_index] = task_xml(
            block_uid, f"Bloco {b}", 1, str(b), True, False, b == 1,
            block_start, m_finish, len(PHASES) * 8 * HOURS, [],
        )
        project_finish = max(project_finish, m_finish)

    # final delivery milestone depends on all blocks
    tasks.append(task_xml(
        uid, "Marco: Entrega do empreendimento", 1, "5", False, True, True,
        project_finish, project_finish, 0, block_finish_uids,
    ))
    uid += 1

    tasks[root_index] = task_xml(
        0, "Residencial Vila Verde - 4 Blocos", 0, "0", True, False, True,
        project_start, project_finish, 0, [],
    )

    res_xml = "\n".join(
        f"    <Resource><UID>{r}</UID><ID>{r}</ID><Name>{n}</Name><Type>1</Type>"
        f"<Initials>R{r}</Initials><MaxUnits>1</MaxUnits><StandardRate>{rate}</StandardRate>"
        f"<OverAllocated>{1 if r == 3 else 0}</OverAllocated><Work>PT0H0M0S</Work></Resource>"
        for r, n, rate in RESOURCES
    )

    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Project xmlns="http://schemas.microsoft.com/project">\n'
        "  <SaveVersion>14</SaveVersion>\n"
        "  <Title>Residencial Vila Verde - 4 Blocos</Title>\n"
        "  <Name>obra-grande.xml</Name>\n"
        "  <Author>Jeff Borges</Author>\n"
        "  <Company>Vila Verde Incorporadora</Company>\n"
        "  <Category>Construction</Category>\n"
        f"  <StartDate>{project_start:%Y-%m-%d}{WORKDAY_START}</StartDate>\n"
        f"  <FinishDate>{project_finish:%Y-%m-%d}{WORKDAY_END}</FinishDate>\n"
        "  <CurrencyCode>BRL</CurrencyCode>\n"
        "  <CurrencySymbol>R$</CurrencySymbol>\n"
        "  <Tasks>\n" + "\n".join(tasks) + "\n  </Tasks>\n"
        "  <Resources>\n" + res_xml + "\n  </Resources>\n"
        "  <Assignments>\n" + "\n".join(assignments) + "\n  </Assignments>\n"
        "</Project>\n"
    )
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(xml)
    print(f"{out_path}: {uid} tarefas, {len(assignments)} atribuicoes")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "obra-grande.xml", int(sys.argv[2]) if len(sys.argv) > 2 else 4)
