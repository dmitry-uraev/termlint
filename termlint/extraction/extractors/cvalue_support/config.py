"""Configuration and rule constants for the C-Value extractor."""

DEFAULT_MODEL = "ru_core_news_sm"
DEFAULT_THRESHOLD = 0.25
DEFAULT_MIN_FREQ = 1
DEFAULT_MIN_LENGTH = 2
DEFAULT_MAX_LENGTH = 4

HEURISTIC_MAX_LENGTH = 2

TOKEN_PATTERN = r"\b[а-яёА-ЯЁa-zA-Z]{3,}\b|[.!?]+"

STOP_WORDS = {
    "и", "в", "на", "с", "по", "для", "не", "от", "за", "до", "из", "о", "об",
    "and", "in", "on", "for", "not", "with", "at", "to", "of", "a", "the",
}

SPACY_CANDIDATE_POS = {"ADJ", "NOUN", "PROPN"}
SPACY_BOUNDARY_POS = {
    "VERB", "AUX", "CCONJ", "SCONJ", "ADP",
    "DET", "PRON", "PART", "PUNCT", "ADV",
}

BAD_ENDINGS_EN = {
    "use", "uses", "using", "used",
    "process", "processes", "processing", "processed",
    "apply", "applies", "applying", "applied",
    "make", "makes", "making", "made",
    "perform", "performs", "performing", "performed",
}
