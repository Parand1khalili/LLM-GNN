"""Owner-approved exact GapGPT aliases, not proof of upstream equivalence."""
VERSION = "sara.gapgpt.identity.exact_alias_revision.v1"
MODELS = ("gpt-6-luna", "gpt-6-luna-2026-09-22")


def allowed(provider, endpoint, requested, returned, settings):
    return (provider == "GapGPT" and endpoint == "https://api.gapgpt.app/v1/chat/completions"
            and requested == "gpt-6-luna" and type(returned) is str and returned in MODELS
            and type(settings) is dict and all(type(settings.get(k)) is int for k in ("temperature","n","max_tokens"))
            and settings == {"temperature": 1, "n": 1, "max_tokens": 512,
                             "reasoning_effort": "OMITTED"})
