"""Détection de langue pour les textes multilingues (Arabic, French, English).

Utilitaire simple basé sur les plages Unicode pour identifier la langue
d'un texte donné. Utilisé pour valider la conformité linguistique des
réponses générées (question en arabe → réponse en arabe, etc.).
"""


def detect_language(text: str) -> str:
    """Détecte la langue d'un texte parmi {ar, fr, en, unknown}.

    Utilise une heuristique basée sur les plages Unicode et l'analyse de mots :
    - Arabe : U+0600–U+06FF (+ U+0750–U+077F pour les variantes)
    - Latin/Français/Anglais : a-z, A-Z

    Args:
        text: Texte à analyser (peut être vide ou multilingue).

    Returns:
        "ar" si la majorité des mots contiennent des caractères arabes
        "fr"/"en" si la majorité des mots contiennent des caractères latins
        "unknown" sinon (ou texte vide).

    Examples:
        >>> detect_language("من هو رئيس")
        'ar'
        >>> detect_language("Qui est le président")
        'fr'
        >>> detect_language("Who is the president")
        'en'
        >>> detect_language("123 @#$")
        'unknown'
    """
    if not text or not text.strip():
        return "unknown"

    # Analyse par mots plutôt que par caractères
    # Cela permet de détecter correctement les textes mixtes
    # où un mot d'une langue se trouve dans un texte d'une autre
    import re

    # Extrait les mots (séquences alphabétiques)
    words = re.findall(r'\b\w+\b', text)

    if not words:
        return "unknown"

    arabic_words = 0
    latin_words = 0

    for word in words:
        has_arabic = any("؀" <= char <= "ۿ" or "ݐ" <= char <= "ݿ" for char in word)
        has_latin = any(("a" <= char <= "z") or ("A" <= char <= "Z") for char in word)

        # Classe le mot selon son contenu dominant
        if has_arabic and not has_latin:
            arabic_words += 1
        elif has_latin and not has_arabic:
            latin_words += 1
        # Si mixte dans le même mot (rare), compte les deux

    if arabic_words == 0 and latin_words == 0:
        return "unknown"

    arabic_ratio = arabic_words / (arabic_words + latin_words) if (arabic_words + latin_words) > 0 else 0
    latin_ratio = latin_words / (arabic_words + latin_words) if (arabic_words + latin_words) > 0 else 0

    # Si arabe dominant, retourne arabe
    if arabic_ratio > 0.5:
        return "ar"

    # Si latin dominant, détermine français vs anglais
    if latin_ratio > 0.5:
        text_lower = text.lower()
        french_words = ["le", "la", "de", "et", "est", "qui", "un", "une", "des", "pour", "que", "quel", "quelle"]
        french_count = sum(1 for word in french_words if word in text_lower)

        english_words = ["the", "is", "who", "and", "a", "of", "in", "to", "for", "that", "what", "which"]
        english_count = sum(1 for word in english_words if word in text_lower)

        if english_count > french_count:
            return "en"
        return "fr"

    # Mixte ou indéterminé
    return "unknown"
