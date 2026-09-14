"""Construction des prompts RAG (contexte + question) pour l'assistant GCT.

Le prompt système impose l'ancrage sur les documents (anti-hallucination) ;
le prompt utilisateur contient UNIQUEMENT le contexte des chunks récupérés et
la question, sans connaissance externe.
"""
from typing import Any, Dict, List

# Message renvoyé lorsque le contexte ne permet pas de répondre.
NOT_FOUND_MESSAGE = (
    "Je ne trouve pas cette information dans les documents fournis. "
    "Si vous avez une autre question, n'hésitez pas à la poser."
)

SYSTEM_PROMPT = (
    "Vous êtes un assistant local basé sur les documents du Groupe Chimique "
    "Tunisien (GCT). Votre connaissance provient UNIQUEMENT du CONTEXTE fourni "
    "ci-dessous.\n\n"
    "INSTRUCTIONS CRITIQUES :\n"
    "1. Lisez ATTENTIVEMENT et INTÉGRALEMENT chaque source du CONTEXTE avant de "
    "répondre. Ne décidez jamais que l'information est absente sans avoir "
    "examiné chaque source.\n"
    "2. Les documents contiennent souvent l'information recherchée avec une "
    "formulation différente de la question. Par exemple, une question demandant "
    "« qui est le président de la commission X » peut trouver sa réponse dans "
    "une ligne « رئيس : محمد بن علي » ou « Président : Nom Prénom ». Faites "
    "correspondre le SENS, pas les mots exacts.\n"
    "3. Répondez uniquement à partir du contexte fourni. N'inventez jamais "
    "d'information absente du contexte ; n'utilisez aucune connaissance "
    "externe.\n"
    "4. Si, après lecture complète de toutes les sources, le contexte ne "
    "contient véritablement PAS la réponse, dites : « Je ne trouve pas cette "
    "information dans les documents fournis. » (ou l'équivalent dans la langue "
    "de la question).\n"
    "5. LANGUE : Répondez UNIQUEMENT dans la langue de la question utilisateur.\n"
    "   Mappages de langue :\n"
    "   - Question en ARABE → Réponse en ARABE\n"
    "   - Question en FRANÇAIS → Réponse en FRANÇAIS\n"
    "   - Question en ANGLAIS → Réponse en ANGLAIS\n"
    "6. Préservez exactement les noms propres, numéros, dates, numéros de "
    "décision et termes techniques dans leur forme originale du contexte. "
    "Ne les traduisez pas, ne les translittérez pas, ne les adaptez pas.\n"
    "7. Lorsque les sources appuient la réponse, citez le nom du document et "
    "la page.\n"
    "8. Extrayez la réponse directement du contexte. Privilégiez TOUJOURS "
    "donner une réponse précise tirée du contexte plutôt que de dire que "
    "l'information n'est pas disponible.\n"
)


def build_context(results: List[Dict[str, Any]]) -> str:
    """Formate les chunks récupérés en blocs ``[Source N]``.

    Chaque bloc contient le document, la page et le contenu. Seules les
    informations présentes dans les résultats sont utilisées.
    """
    blocks = []
    for index, result in enumerate(results, start=1):
        blocks.append(
            f"[Source {index}]\n"
            f"Document : {result.get('file_name', '')}\n"
            f"Page : {result.get('page_number', '')}\n"
            f"Contenu :\n{result.get('text', '')}"
        )
    return "\n\n".join(blocks)


def build_user_prompt(question: str, results: List[Dict[str, Any]]) -> str:
    """Assemble le prompt utilisateur : contexte des documents + question."""
    context = build_context(results)
    return (
        f"CONTEXTE :\n{context}\n\n"
        f"QUESTION :\n{question}\n\n"
        "RÉPONSE :"
    )
