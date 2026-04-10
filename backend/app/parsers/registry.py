from app.parsers.base import BankParser

_registry: list[BankParser] = []


def register(parser: BankParser):
    _registry.append(parser)


def get_registry() -> list[BankParser]:
    return _registry


def find_parser(sender: str) -> BankParser | None:
    for parser in _registry:
        if parser.matches(sender):
            return parser
    return None
