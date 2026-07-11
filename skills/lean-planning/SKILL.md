---
name: lean-planning
description: Opera o lean-planning-mcp (MS Project, Primavera P6, Synchro) com fluxos corretos de AWP e Last Planner System. Usar quando o usuário carregar um cronograma, pedir lookahead, PPC, plano semanal, restrições, pacotes de trabalho (CWA/CWP/IWP/EWP/PWP), readiness, pull plan ou daily huddle. Garante a ordem certa das tools e as regras da metodologia que as tools sozinhas não explicam.
---

# Lean Planning — operando o lean-planning-mcp

Este MCP tem 49 tools em três camadas: núcleo de cronograma (leitura), AWP
(escopo em pacotes) e LPS (fluxo de compromissos). As camadas AWP e LPS são
independentes por design — sidecar separado, sem estado compartilhado. Use
uma, outra ou as duas.

## Regra zero

Sempre comece com `load_project`. Nenhuma outra tool funciona sem projeto
carregado. Formatos: `.xml` (MSPDI, sem dependência), `.mpp`, `.xer`,
`.pmxml`, `.sp`, `.pp` (esses exigem o extra `[mpp]` com Java). O arquivo
original nunca é modificado; tudo que AWP/LPS gravam vive em uma pasta
sidecar `<nome>.awp/` ao lado do arquivo.

## Fluxo AWP — setup na ordem certa

A ordem importa. Cada passo depende do anterior:

1. `awp_upsert_cwa` — criar áreas (CWA) primeiro.
2. `awp_upsert_cwp` — criar pacotes dentro de CWA existente.
3. `awp_assign_task_to_cwp` — vincular tarefas por UID (uma tarefa pertence
   a um único CWP; reatribuir move).
4. `awp_upsert_ewp` e `awp_upsert_pwp` — registrar pacotes de engenharia e
   suprimentos vinculados ao CWP.
5. `awp_set_cwp_requirements` — requisitos manuais (materiais, documentos,
   acessos).
6. `awp_set_path_of_construction` — o PoC é decisão do time de construção,
   um INPUT de planejamento. Só deixe derivar do cronograma se o usuário não
   tiver definido sequência (o resultado indica `mode`).
7. `awp_generate_iwps` — quebrar CWP em IWPs. Default 500h (1-2 semanas de
   um crew, dimensionamento CII). Sempre pergunte ou informe `discipline` e
   `crew`: IWP correto é disciplina única, equipe única, frente única.
   Regenerar preserva IWPs já ready/released/complete.
8. `awp_readiness_check` — verifica requisitos manuais + todos EWPs
   `issued` + todos PWPs `delivered`. O resultado fica gravado no CWP.
9. `awp_release_iwp` — só funciona com readiness check aprovado. Se falhar,
   mostre ao usuário o que falta (`missing`) em vez de tentar contornar.
10. `awp_update_iwp_progress` — avanço de campo; 100% marca complete e
    calcula horas ganhas.

Regra de ouro (WorkFace Planning): IWP vai pro campo 100% livre de
restrições. Nunca sugira pular o readiness check.

## Fluxo LPS — o ritual semanal

### Início de semana (ou na reunião de lookahead)

1. `lps_lookahead` (default 6 semanas) — o que vem e o que bloqueia.
   Preste atenção em `late_constraint_ids`: restrição com promessa de
   resolução DEPOIS do início da tarefa = make-ready atrasado, alertar.
2. `lps_snapshot_lookahead` — SEMPRE rodar junto com a revisão semanal do
   lookahead. Sem snapshot não existe TA/TMR depois. Este é o erro mais
   comum de operação.
3. `lps_register_constraint` para bloqueios novos identificados na reunião
   (tipos: material, document, information, design, labor, equipment,
   access, permit, prerequisite, other). Sempre com `owner` e `due_date`.
4. `lps_add_commitment` para montar o plano semanal (semana ISO
   `YYYY-Www`). A tool RECUSA tarefa com restrição aberta (shielding
   production, Ballard 1998). Se o usuário insistir, `allow_constrained=true`
   existe, mas explique que o compromisso fica marcado como risco. Prefira
   limpar a restrição antes (`lps_clear_constraint`).
5. `lps_workable_backlog` — monte o buffer reserva: tarefas ready não
   comprometidas que as equipes puxam se algo travar.

### Durante a semana

- `lps_log_daily` — registro do daily huddle por tarefa comprometida.
  `blocked=true` em bloqueio novo; registre também a restrição
  correspondente na hora.
- `lps_get_daily_log` para revisar o acumulado.

### Fim de semana (fechamento)

1. `lps_mark_complete` para cada compromisso. Binário: feito ou não feito,
   sem percentual parcial. Não concluído exige `variance_reason` e,
   idealmente, `corrective_action` (o que muda pra não repetir — fecha o
   PDCA).
2. `lps_ppc` — PPC da semana e série. 
3. `lps_reliability` — TA/TMR (exige snapshots acumulados).

### Pull planning (por fase)

`lps_upsert_phase` → `lps_set_pull_plan` (UIDs na ordem de execução,
construído de trás pra frente a partir do marco) → `lps_annotate_pull_plan`
para registrar handoff e condições de satisfação de cada entrega entre
equipes. Pull plan sem handoff anotado é só uma lista; a rede de promessas é
o que importa.

## Interpretação de métricas — o que dizer ao usuário

- **PPC < 80%**: não culpar equipes de imediato. Abrir o Pareto de
  `variance_reasons` no resultado do `lps_ppc` e atacar a causa dominante.
- **PPC alto + poucas tarefas comprometidas**: possível sandbagging; comparar
  com o lookahead pra ver o que ficou de fora.
- **TA baixo** (compromissos que o lookahead nunca viu): trabalho entrando
  no plano por fora do planejamento — indisciplina de processo.
- **TMR baixo** (antecipado mas não comprometido): make-ready não está
  limpando restrições a tempo. Problema do sistema, não das equipes.
- **`late_constraint_task_count` > 0 no lookahead**: escalar com o `owner`
  da restrição antes que vire variância.

## Erros comuns a evitar

- Rodar lookahead semanal sem `lps_snapshot_lookahead` (perde TA/TMR).
- Comprometer com `allow_constrained=true` como rotina — override é exceção.
- Gerar IWPs sem disciplina/crew definidos.
- Tratar `awp_path_of_construction` em modo `derived-from-schedule` como PoC
  real — é fallback; o PoC de verdade vem de `awp_set_path_of_construction`.
- Liberar IWP logo após editar EWP/PWP sem rodar `awp_readiness_check` de
  novo (o gate usa o último resultado gravado).
- Esquecer que semana é ISO: `2026-W07`, não data.

## Relatório de insights (sob demanda)

Quando o usuário pedir "insights", "como está o projeto", "resumo da
semana" ou "relatório pra reunião", monte a leitura cruzando as camadas —
nenhuma tool isolada entrega isso, a síntese é sua função:

1. `project_info` + `get_critical_path` — janela do projeto e exposição
   crítica.
2. `get_baseline_variance` — top desvios contra baseline (as 5 maiores
   variações merecem menção nominal).
3. `lps_ppc` (série) + `lps_reliability` — tendência de confiabilidade,
   não só o número da semana.
4. `lps_list_constraints(status="open")` — agrupar por tipo e por owner;
   destacar as vencidas (due_date no passado) e as de tarefas críticas.
5. `lps_lookahead` — ready vs blocked nas próximas semanas +
   `late_constraint_task_count`.
6. Se AWP em uso: `awp_list_cwp` + `awp_path_of_construction` — avanço por
   pacote (IWPs complete/released vs planned) e aderência ao PoC.
7. `find_overallocated_resources` — gargalos de recurso.

Formato do insight: afirmação + evidência numérica + ação sugerida. Exemplo:
"PPC caiu de 82% para 61% em 3 semanas; causa dominante é material_delay
(7 de 11 falhas); 4 restrições de material estão vencidas com o mesmo
fornecedor — antecipar a reunião de suprimentos." Nunca liste números sem
dizer o que fazer com eles. Feche sempre com os 3 riscos mais importantes
da próxima semana.

## Extras

- `generate_pbip_dashboard` — dashboard Power BI do cronograma carregado.
- `export_to_json` — export completo pra automação downstream.
- Cronograma de P6/Synchro carregado funciona idêntico: todas as camadas
  operam sobre task UIDs, independente da origem.
