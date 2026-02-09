from django.core.management.base import BaseCommand

from hospital_game.models import Department, PatientCard


DEPARTMENTS = [
    {
        "key": "TRIAGE",
        "label": "Triagem",
        "base_upgrade_seconds": 60,
        "base_cost_energy": 20,
        "base_cost_supplies": 10,
        "max_level": 10,
    },
    {
        "key": "WARD",
        "label": "Enfermaria",
        "base_upgrade_seconds": 120,
        "base_cost_energy": 30,
        "base_cost_supplies": 15,
        "max_level": 10,
    },
    {
        "key": "OR",
        "label": "Centro cirúrgico",
        "base_upgrade_seconds": 180,
        "base_cost_energy": 50,
        "base_cost_supplies": 25,
        "max_level": 10,
    },
    {
        "key": "LAB",
        "label": "Laboratório",
        "base_upgrade_seconds": 150,
        "base_cost_energy": 40,
        "base_cost_supplies": 20,
        "max_level": 10,
    },
]

PATIENT_CARDS = [
    {"key": "common-1", "title": "Paciente Calmo", "rarity": "COMMON", "flavor_text": "Sempre agradece."},
    {"key": "common-2", "title": "Paciente Ansioso", "rarity": "COMMON", "flavor_text": "Precisa de atenção."},
    {"key": "common-3", "title": "Paciente Determinado", "rarity": "COMMON", "flavor_text": "Não perde a fé."},
    {"key": "common-4", "title": "Paciente Resiliente", "rarity": "COMMON", "flavor_text": "Segue firme."},
    {"key": "common-5", "title": "Paciente Atento", "rarity": "COMMON", "flavor_text": "Observa tudo."},
    {"key": "common-6", "title": "Paciente Optimista", "rarity": "COMMON", "flavor_text": "Acredita na cura."},
    {"key": "common-7", "title": "Paciente Carismático", "rarity": "COMMON", "flavor_text": "Eleva o moral."},
    {"key": "common-8", "title": "Paciente Persistente", "rarity": "COMMON", "flavor_text": "Nunca desiste."},
    {"key": "rare-1", "title": "Paciente Raro", "rarity": "RARE", "flavor_text": "Um caso curioso."},
    {"key": "rare-2", "title": "Paciente Investigado", "rarity": "RARE", "flavor_text": "Desafia diagnósticos."},
    {"key": "rare-3", "title": "Paciente Guardião", "rarity": "RARE", "flavor_text": "Protege a equipe."},
    {"key": "rare-4", "title": "Paciente Admirado", "rarity": "RARE", "flavor_text": "Inspira confiança."},
    {"key": "rare-5", "title": "Paciente Estrategista", "rarity": "RARE", "flavor_text": "Planeja cada passo."},
    {"key": "epic-1", "title": "Paciente Lendário", "rarity": "EPIC", "flavor_text": "Uma história única."},
    {"key": "epic-2", "title": "Paciente Visionário", "rarity": "EPIC", "flavor_text": "Vê além do óbvio."},
]


class Command(BaseCommand):
    help = "Seed initial hospital game data (departments and patient cards)."

    def handle(self, *args, **options):
        for dept in DEPARTMENTS:
            Department.objects.update_or_create(key=dept["key"], defaults=dept)

        for card in PATIENT_CARDS:
            PatientCard.objects.update_or_create(key=card["key"], defaults=card)

        self.stdout.write(self.style.SUCCESS("Hospital game data seeded."))
