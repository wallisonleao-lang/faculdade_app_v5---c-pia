import random

from django.core.management.base import BaseCommand
from django.db import transaction

from study.models import StudyQuestion, StudySource, StudyTag


class Command(BaseCommand):
    help = "Seed study module with sample tags, sources, and questions."

    def handle(self, *args, **options):
        tags = [
            ("Clínica", "Cardio", "Insuficiência"),
            ("Clínica", "Infecto", "Antibióticos"),
            ("Cirurgia", "Abdome", "Hérnias"),
            ("Ortop", "Trauma", "Fraturas"),
            ("GO", "Pré-natal", "Diabetes gestacional"),
            ("Pediatria", "Neonatologia", "Icterícia"),
            ("Preventiva", "Epidemiologia", "Indicadores"),
        ]

        sources = [
            ("USP", "Residência Clínica", 2024),
            ("UNIFESP", "Prova Geral", 2023),
            ("UNESP", "Residência", 2022),
        ]

        with transaction.atomic():
            tag_objs = []
            for area, tema, subtema in tags:
                tag, _ = StudyTag.objects.get_or_create(area=area, tema=tema, subtema=subtema)
                tag_objs.append(tag)

            source_objs = []
            for instituicao, prova_nome, ano in sources:
                src, _ = StudySource.objects.get_or_create(
                    instituicao=instituicao,
                    prova_nome=prova_nome,
                    ano=ano,
                )
                source_objs.append(src)

            existing = StudyQuestion.objects.count()
            target = 40
            to_create = max(0, target - existing)

            for idx in range(to_create):
                tag = random.choice(tag_objs)
                source = random.choice(source_objs)
                stem = f"Questão exemplo {existing + idx + 1}: {tag.tema} / {tag.subtema}."
                choices = [
                    "Conduta A",
                    "Conduta B",
                    "Conduta C",
                    "Conduta D",
                    "Conduta E",
                ]
                correct_choice = random.choice(["A", "B", "C", "D", "E"])
                StudyQuestion.objects.create(
                    tag=tag,
                    source=source,
                    enunciado=stem,
                    choice_a=choices[0],
                    choice_b=choices[1],
                    choice_c=choices[2],
                    choice_d=choices[3],
                    choice_e=choices[4],
                    correct_choice=correct_choice,
                    explanation="Comentário breve sobre a resposta correta.",
                    difficulty=random.choice(["EASY", "MEDIUM", "HARD"]),
                    source_page=random.randint(1, 150),
                    source_snippet=stem[:200],
                )

        self.stdout.write(self.style.SUCCESS("Seed do módulo study concluído."))
