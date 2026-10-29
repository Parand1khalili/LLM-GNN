
import tiktoken


STRUCTURAL_BUDGET = 256


COMMON_INSTRUCTION = (
    "\n\nUsage instruction:\n"
    "Treat neighborhood information only as auxiliary evidence. "
    "Infer the topic primarily from the target paper. "
    "If neighborhood evidence conflicts with the target text, "
    "prioritize the target text."
)


def get_tokenizer():
    try:
        return tiktoken.encoding_for_model("gpt-3.5-turbo")
    except Exception:
        return tiktoken.get_encoding("cl100k_base")


ENC = get_tokenizer()


def count_tokens(text):
    return len(ENC.encode(text))


def truncate_tokens(text, max_tokens):
    if max_tokens <= 0:
        return ""

    ids = ENC.encode(text)

    if len(ids) <= max_tokens:
        return text

    return ENC.decode(ids[:max_tokens])


def _fit_with_suffix(prefix, body, suffix, budget):
    """
    Preserve prefix + suffix and allocate remaining budget to body.
    """

    fixed = (
        count_tokens(prefix)
        + count_tokens(suffix)
    )

    remaining = max(
        0,
        budget - fixed
    )

    shortened = truncate_tokens(
        body,
        remaining
    )

    result = (
        prefix
        + shortened
        + suffix
    )

    # Final tokenizer safety check.
    while count_tokens(result) > budget and shortened:
        ids = ENC.encode(shortened)
        shortened = ENC.decode(ids[:-1])

        result = (
            prefix
            + shortened
            + suffix
        )

    if count_tokens(result) > budget:
        raise RuntimeError(
            "Fixed prompt overhead exceeds token budget."
        )

    return result


def build_rep1(
    representative_text,
    budget=STRUCTURAL_BUDGET
):
    """
    M1-Rep1:
    highest-relevance semantic 1-hop neighbor only.
    """

    prefix = (
        "LOCAL NEIGHBORHOOD EVIDENCE\n\n"
        "Representative direct 1-hop neighbor:\n"
    )

    return _fit_with_suffix(
        prefix=prefix,
        body=representative_text,
        suffix=COMMON_INSTRUCTION,
        budget=budget,
    )


def build_consensus(
    representative_text,
    support_count,
    selected_count,
    budget=STRUCTURAL_BUDGET
):
    """
    M1-Cons:
    same representative as Rep1
    + additional semantic-support count.

    support_count includes the representative itself.
    The prompt reports only OTHER supporting neighbors,
    which avoids the tautological 1-of-k formulation.
    """

    additional_support = max(
        0,
        support_count - 1
    )

    other_count = max(
        0,
        selected_count - 1
    )

    prefix = (
        "LOCAL NEIGHBORHOOD EVIDENCE\n\n"
        "Representative direct 1-hop neighbor:\n"
    )

    consensus_block = (
        "\n\nAdditional semantic support:\n"
        f"{additional_support} of the {other_count} other retrieved "
        "direct neighbors are semantically consistent with "
        "the representative neighbor."
    )

    suffix = (
        consensus_block
        + COMMON_INSTRUCTION
    )

    return _fit_with_suffix(
        prefix=prefix,
        body=representative_text,
        suffix=suffix,
        budget=budget,
    )


def build_raw3(
    neighbor_texts,
    budget=STRUCTURAL_BUDGET
):
    """
    M1-Raw3:
    up to three semantic 1-hop neighbors separately,
    under the same total structural token ceiling.
    """

    neighbor_texts = list(
        neighbor_texts[:3]
    )

    if not neighbor_texts:
        return ""

    title = (
        "LOCAL NEIGHBORHOOD EVIDENCE\n\n"
    )

    headers = [
        f"Direct 1-hop neighbor N{i}:\n"
        for i in range(
            1,
            len(neighbor_texts) + 1
        )
    ]

    separator = "\n\n"

    fixed_tokens = (
        count_tokens(title)
        + count_tokens(COMMON_INSTRUCTION)
    )

    for h in headers:
        fixed_tokens += count_tokens(h)

    fixed_tokens += (
        max(0, len(headers) - 1)
        * count_tokens(separator)
    )

    available = max(
        0,
        budget - fixed_tokens
    )

    per_neighbor = (
        available // len(neighbor_texts)
    )

    parts = []

    for i, text in enumerate(
        neighbor_texts,
        start=1
    ):
        shortened = truncate_tokens(
            text,
            per_neighbor
        )

        parts.append(
            f"Direct 1-hop neighbor N{i}:\n"
            f"{shortened}"
        )

    result = (
        title
        + separator.join(parts)
        + COMMON_INSTRUCTION
    )

    # Tokenizer-safe final trim of neighbor contents if needed.
    if count_tokens(result) > budget:

        overflow = (
            count_tokens(result)
            - budget
        )

        # Remove excess conservatively from last neighbor text.
        while (
            count_tokens(result) > budget
            and parts
        ):
            last_idx = len(parts) - 1

            header = (
                f"Direct 1-hop neighbor N{last_idx + 1}:\n"
            )

            body = parts[last_idx][
                len(header):
            ]

            ids = ENC.encode(body)

            if not ids:
                break

            body = ENC.decode(
                ids[:-1]
            )

            parts[last_idx] = (
                header + body
            )

            result = (
                title
                + separator.join(parts)
                + COMMON_INSTRUCTION
            )

    if count_tokens(result) > budget:
        raise RuntimeError(
            "Raw3 exceeded structural token budget."
        )

    return result
