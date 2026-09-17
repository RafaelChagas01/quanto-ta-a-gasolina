import re
import unicodedata

LOWER_WORDS = {"de", "da", "do", "das", "dos", "e", "d"}


def strip_accents(value: str) -> str:
    nfkd = unicodedata.normalize("NFKD", value)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def key(value: str) -> str:
    """Chave pra casar nomes da ANP (sem acento, maiusculo) com os do IBGE."""
    value = strip_accents(value).upper()
    value = re.sub(r"[^A-Z0-9 ]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def title_pt(value: str) -> str:
    words = value.lower().split()
    out = []
    for i, word in enumerate(words):
        if i > 0 and word in LOWER_WORDS:
            out.append(word)
        else:
            out.append(word[:1].upper() + word[1:])
    return " ".join(out)


def slugify(value: str) -> str:
    return key(value).lower().replace(" ", "-")
