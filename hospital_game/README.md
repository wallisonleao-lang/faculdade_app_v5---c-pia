# Hospital Game (MVP)

Mini-jogo “Hospital Idle” integrado ao app de tarefas.

## Instalação

1. Adicione `hospital_game` ao `INSTALLED_APPS` (já incluído neste PR).
2. Inclua as URLs em `faculdade_tarefas/urls.py` (já incluído).
3. Rode as migrações:

```bash
python manage.py migrate
```

4. Crie os dados iniciais:

```bash
python manage.py seed_hospital_game
```

## Endpoints

- `GET /hospital/` dashboard HTML
- `GET /hospital/api/status/` status do hospital (totais, ledger do dia, setores)
- `POST /hospital/api/claim/` encerrar plantão (daily claim)
- `POST /hospital/api/department/<key>/start_upgrade/` iniciar upgrade
- `POST /hospital/api/department/<key>/finish_upgrade/` concluir upgrade
- `GET /hospital/collection/` coleção de Patient Cards

## Integração com conclusão de tarefas

O app possui signal em `hospital_game/signals.py` que observa `core.Task` e registra no ledger quando:
- `status == "DONE"` **e** `done_at` está preenchido.

Isso evita depender de uma view específica. A contagem é idempotente via `TaskCompletionLog` (unique por `task_id`).

Também contabilizamos:
- Aulas assistidas (`class_mark_watched_view`)
- Revisões P1/P2 (`class_mark_review_p1_view`, `class_mark_review_p2_view`)

Essas ações usam `record_activity_completion`, com ganhos padrão de MVP:
`energy +5`, `supplies +1`.

Se preferir integrar diretamente no fluxo atual, basta chamar:

```python
from hospital_game.services.ledger_service import record_task_completion
record_task_completion(task)
```

## Observações

- O Task atual não possui `difficulty` e `estimated_minutes`, então o cálculo usa defaults (`difficulty=1`, `estimated_minutes=10`).
- Se o modelo de tarefa mudar, ajuste a função `_get_task_user` ou o signal para localizar o usuário corretamente.

## Segurança e consistência

- Todos os endpoints são autenticados.
- Cada usuário só acessa seus próprios dados.
- Operações sensíveis usam `transaction.atomic()` e `select_for_update()`.
- Daily claim é idempotente (1x/dia por usuário).
