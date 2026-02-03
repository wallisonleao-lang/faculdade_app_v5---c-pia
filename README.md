# Faculdade App — Dashboard de Estudos

Aplicação Django para organizar disciplinas, aulas, tarefas, provas, faltas e questões, com autenticação, multiusuário, instituição e sincronização de aulas.

## Recursos principais

- Login/cadastro (email/senha) + Google (allauth)
- Separação de dados por usuário
- Instituições (ex.: FMUSP) e base de aulas por instituição
- Sincronização de aulas da instituição para o usuário
- Usuário master com controle de recursos (feature flags)
- Planner semanal, faltas, questões, importação CSV e dashboard de prioridades

## Requisitos

- Python 3.11+ (testado com 3.14)
- SQLite (default)

## Setup rápido

```
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver
```

## Autenticação

- Login e cadastro em:
  - `/accounts/login/`
  - `/accounts/signup/`
- O email de confirmação é impresso no terminal (backend de email de console).

### Google Login (allauth)

1) Crie o Site em `/admin/sites/` (Site ID = 1).
2) Crie o SocialApp Google em `/admin/socialaccount/socialapp/` e associe ao Site.

## Usuário master

Defina o email do master:

```
export MASTER_EMAIL="seuemail@dominio.com"
```

Ou altere em `faculdade_tarefas/settings.py` (já tem fallback).

O master:
- Vê o botão **Master**
- Pode ligar/desligar recursos globais
- Tem bypass das flags (não perde acesso)

## Instituições e sincronização de aulas

### Base institucional

- `Institution`, `InstitutionCourse`, `InstitutionClass` são os dados base.
- O usuário escolhe a instituição em **Meu perfil**.
- O botão **Sincronizar aulas** cria aulas do usuário a partir da base.

### Espelhamento automático (master)

No **Meu perfil**, habilite:
- **Espelhamento automático de aulas**

Quando o master cria/edita/remove aulas, a base FMUSP é espelhada 100%.

## Migração dos dados antigos para o master (FMUSP)

Se você tinha dados antigos sem usuário:

```
./.venv/bin/python manage.py seed_master_fmusp
```

O comando:
- Atribui cursos sem usuário ao master
- Cria `InstitutionCourse` e vincula aos cursos
- Cria/atualiza `InstitutionClass` a partir das aulas do master
- Remove da base o que não existe mais no master (espelhamento 100%)

## Telas principais

- Dashboard: `/`
- Disciplinas: `/courses/`
- Planner semanal: `/planner/`
- Questões: `/questions/`
- Faltas: `/faltas/`
- Perfil: `/profile/`
- Master: `/master/`

## Importação de aulas por CSV

Na disciplina, use o bloco **Importar aulas (CSV)**.  
Cabeçalho esperado:

```
date,title,class_number
```

## Notas de desenvolvimento

- Feature flags ficam em `core/FeatureFlag`.
- Menu e views respeitam as flags (exceto master).
- Dados são sempre filtrados por `request.user`.
