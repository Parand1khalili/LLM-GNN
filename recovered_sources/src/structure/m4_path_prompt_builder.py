from .prompt_builder import (
    STRUCTURAL_BUDGET,
    COMMON_INSTRUCTION,
    ENC,
    count_tokens,
    truncate_tokens,
)

TEMPLATE_VERSION = "m4a_path_v1"

TITLE = "LOCAL GRAPH PATH EVIDENCE\n\n"

PATH_HEADER = "Path {index}: TARGET -- H1 -- H2\n"
H1_HEADER = "H1 paper:\n"
H2_HEADER = "\nH2 paper:\n"

PATH_SEPARATOR = "\n\n"


def _assemble(slot_texts, path_count):
    parts = []
    cursor = 0

    for index in range(1, path_count + 1):
        h1_text = slot_texts[cursor]
        h2_text = slot_texts[cursor + 1]
        cursor += 2

        parts.append(
            PATH_HEADER.format(index=index)
            + H1_HEADER
            + h1_text
            + H2_HEADER
            + h2_text
        )

    return (
        TITLE
        + PATH_SEPARATOR.join(parts)
        + COMMON_INSTRUCTION
    )


def build_path_prompt(
    path_node_texts,
    budget=STRUCTURAL_BUDGET,
):
    paths = list(path_node_texts)

    if not paths:
        return ""

    if len(paths) > 3:
        raise ValueError(
            "M4-A allows at most three paths."
        )

    for pair in paths:
        if (
            not isinstance(pair, (tuple, list))
            or len(pair) != 2
        ):
            raise TypeError(
                "Each path must contain exactly "
                "(hop1_text, hop2_text)."
            )

        if not all(
            isinstance(text, str)
            for text in pair
        ):
            raise TypeError(
                "All auxiliary node texts must be strings."
            )

    path_count = len(paths)
    slot_count = 2 * path_count

    empty_slots = [
        ""
        for _ in range(slot_count)
    ]

    fixed_prompt = _assemble(
        empty_slots,
        path_count,
    )

    fixed_tokens = count_tokens(
        fixed_prompt
    )

    if fixed_tokens > budget:
        raise RuntimeError(
            "M4-A fixed prompt overhead exceeds "
            "the structural token budget."
        )

    available_tokens = (
        budget
        - fixed_tokens
    )

    per_slot_budget = (
        available_tokens
        // slot_count
    )

    slot_texts = []

    for hop1_text, hop2_text in paths:
        slot_texts.append(
            truncate_tokens(
                hop1_text,
                per_slot_budget,
            )
        )

        slot_texts.append(
            truncate_tokens(
                hop2_text,
                per_slot_budget,
            )
        )

    result = _assemble(
        slot_texts,
        path_count,
    )

    # BPE token counts are not perfectly additive across
    # concatenation boundaries. If necessary, trim one token
    # at a time from auxiliary slots in deterministic reverse
    # round-robin order until the exact budget is satisfied.
    trim_index = len(slot_texts) - 1

    while count_tokens(result) > budget:
        found_nonempty = False

        for _ in range(len(slot_texts)):
            if slot_texts[trim_index]:
                ids = ENC.encode(
                    slot_texts[trim_index]
                )

                if ids:
                    slot_texts[trim_index] = (
                        ENC.decode(ids[:-1])
                    )
                else:
                    slot_texts[trim_index] = ""

                found_nonempty = True

                trim_index = (
                    trim_index - 1
                ) % len(slot_texts)

                break

            trim_index = (
                trim_index - 1
            ) % len(slot_texts)

        if not found_nonempty:
            break

        result = _assemble(
            slot_texts,
            path_count,
        )

    final_tokens = count_tokens(
        result
    )

    if final_tokens > budget:
        raise RuntimeError(
            "M4-A path prompt still exceeds "
            "the structural token budget."
        )

    return result
