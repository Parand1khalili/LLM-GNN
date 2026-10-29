import time
import re
import hashlib
import os
import tiktoken
import openai
import json
import os.path as osp
import asyncio
from openail.asyncapi import process_api_requests_from_file
import torch
import logging
import ast
import matplotlib.pyplot as plt
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
) 







async def call_async_api(request_filepath, save_filepath, request_url, api_key, max_request_per_minute, max_tokens_per_minute, sp, ss):
    await process_api_requests_from_file(
            requests_filepath=request_filepath,
            save_filepath=save_filepath,
            request_url=request_url,
            api_key=api_key,
            max_requests_per_minute=float(max_request_per_minute),
            max_tokens_per_minute=float(max_tokens_per_minute),
            token_encoding_name='cl100k_base',
            max_attempts=int(2),
            logging_level=int(logging.INFO),
            seconds_to_pause=sp,
            seconds_to_sleep=ss
        )


def set_endpoints(openai_key, openai_endpoints):
    openai.api_key = openai_key
    openai.api_base = openai_endpoints



@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def openai_text_api_with_backoff(*args, **kwargs):
    return openai_text_api(*args, **kwargs)



def _gapgpt_independent_chat_completions(
    input_text,
    api_key,
    model_name,
    n=1,
    temperature=None,
    top_p=None,
):
    """
    GapGPT adapter for independent sampling.

    The gateway may return only one choice even when n > 1, so
    self-consistency samples are requested independently with n=1.

    Transient provider/network failures are retried with bounded
    exponential backoff. The function either returns exactly `n`
    choices or raises an exception.
    """
    requested_n = int(n)

    if requested_n < 1:
        raise ValueError("n must be >= 1")

    merged_choices = []
    first_response = None

    # Six retries means at most seven attempts for one sample.
    # Backoff: 1, 2, 4, 8, 16, 32 seconds.
    max_retries = 6

    def is_transient_error(exc):
        status = getattr(exc, "http_status", None)

        if status is None:
            status = getattr(exc, "status_code", None)

        try:
            if status is not None:
                status = int(status)

                if status == 429:
                    return True

                if 500 <= status <= 599:
                    return True
        except Exception:
            pass

        class_name = exc.__class__.__name__

        if class_name in {
            "APIConnectionError",
            "Timeout",
            "RateLimitError",
            "ServiceUnavailableError",
        }:
            return True

        # Old OpenAI SDK APIError messages may contain the HTTP
        # status only in their text, e.g. "HTTP code 520 ...".
        message = str(exc)

        # GapGPT/gpt-6-luna has intermittently returned an
        # InvalidRequestError claiming that temperature=0.7 is
        # unsupported, even though the same endpoint/model accepts
        # temperature=0.7 on other requests. Treat ONLY this exact
        # routing/provider anomaly as transient. Other
        # InvalidRequestError instances must still fail immediately.
        message_lower = message.lower()

        if (
            class_name == "InvalidRequestError"
            and "unsupported value" in message_lower
            and "temperature" in message_lower
            and "does not support 0.7" in message_lower
            and "only the default (1) value is supported"
            in message_lower
        ):
            return True

        match = re.search(
            r"(?:HTTP\s+code|status(?:\s+code)?)"
            r"\s*[:=]?\s*(\d{3})",
            message,
            flags=re.IGNORECASE,
        )

        if match is not None:
            code = int(match.group(1))

            if code == 429 or 500 <= code <= 599:
                return True

        return False

    for sample_idx in range(requested_n):

        kwargs = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": input_text,
                }
            ],
            "api_key": api_key,
            "n": 1,
        }

        if temperature is not None:
            kwargs["temperature"] = temperature

        if top_p is not None:
            kwargs["top_p"] = top_p

        attempt = 0

        while True:
            try:
                response = openai.ChatCompletion.create(
                    **kwargs
                )
                break

            except Exception as exc:
                transient = is_transient_error(exc)

                if (not transient) or attempt >= max_retries:
                    raise

                delay = min(
                    60.0,
                    float(2 ** attempt),
                )

                print(
                    "[GapGPT retry] "
                    f"sample={sample_idx + 1}/{requested_n}, "
                    f"retry={attempt + 1}/{max_retries}, "
                    f"wait={delay:.0f}s, "
                    f"error={exc.__class__.__name__}"
                )

                time.sleep(delay)
                attempt += 1

        choices = response.get("choices", [])

        if len(choices) != 1:
            raise RuntimeError(
                "GapGPT adapter expected exactly 1 choice "
                "from an n=1 request, but received "
                f"{len(choices)} "
                f"(sample {sample_idx + 1}/"
                f"{requested_n})."
            )

        if first_response is None:
            first_response = response

        merged_choices.append(
            choices[0]
        )

    if len(merged_choices) != requested_n:
        raise RuntimeError(
            "Multi-sample adapter produced "
            f"{len(merged_choices)} choices; "
            f"expected {requested_n}."
        )

    first_response["choices"] = merged_choices

    return first_response

def openai_text_api(
    input_text,
    api_key,
    model_name="gpt-6-luna",
    temperature=0,
    n=1
):
    openai.api_base = "https://api.gapapi.com/v1"

    return _gapgpt_independent_chat_completions(
        input_text=input_text,
        api_key=api_key,
        model_name=model_name,
        temperature=temperature,
        n=n,
    )


def openai_text_api_with_top_p(
    input_text,
    api_key,
    model_name="gpt-6-luna",
    top_p=1,
    n=1
):
    openai.api_base = "https://api.gapapi.com/v1"

    return _gapgpt_independent_chat_completions(
        input_text=input_text,
        api_key=api_key,
        model_name=model_name,
        top_p=top_p,
        n=n,
    )


def generate_chat_input_file(input_text, model_name = 'gpt-6-luna', temperature = 0, n = 1):
    jobs = []
    for i, text in enumerate(input_text):
        obj = {}
        obj['model'] = model_name
        obj['messages'] = [
            {
                'role': 'user',
                'content': text 
            }
        ]
        obj['temperature'] = temperature
        # GapGPT/Luna may ignore n>1. Each provider request is
        # therefore explicitly a single independent sample.
        obj['n'] = 1
        jobs.append(obj)
    return jobs 



def efficient_openai_text_api(
    input_text,
    filename,
    savepath,
    sp,
    ss,
    api_key="change_this_to_your_key",
    request_url="https://api.gapapi.com/v1/chat/completions",
    rewrite=True,
    temperature=0,
    n=1,
):
    requested_n = int(n)

    if requested_n < 1:
        raise ValueError("n must be >= 1")

    # This mapping must exist regardless of whether the async stage
    # is newly executed or an existing output file is reused.
    non_empty_results = [
        i
        for i, prompt in enumerate(input_text)
        if prompt != ""
    ]

    # --------------------------------------------------------------
    # Stage A — first independent sample via existing async pipeline.
    #
    # IMPORTANT:
    # rewrite=False now REALLY means reuse the existing async output.
    # --------------------------------------------------------------
    if not osp.exists(savepath) or rewrite:

        jobs = generate_chat_input_file(
            input_text,
            model_name="gpt-6-luna",
            temperature=temperature,
            n=requested_n,
        )

        with open(
            filename,
            "w",
            encoding="utf-8",
        ) as f:

            for job in jobs:

                if (
                    job["messages"][0]["content"]
                    == ""
                ):
                    continue

                f.write(
                    json.dumps(job)
                    + "\n"
                )

        asyncio.run(
            call_async_api(
                filename,
                save_filepath=savepath,
                request_url=request_url,
                api_key=api_key,
                max_request_per_minute=100000000,
                max_tokens_per_minute=9000000000,
                sp=sp,
                ss=ss,
            )
        )

    if not osp.exists(savepath):
        raise RuntimeError(
            "Async output file does not exist after "
            f"first-sample stage: {savepath}"
        )

    # --------------------------------------------------------------
    # Fingerprint the exact sparse prompt set.
    # --------------------------------------------------------------
    prompt_hasher = hashlib.sha256()

    for idx, prompt in enumerate(input_text):
        if prompt == "":
            continue

        prompt_hasher.update(
            str(idx).encode("utf-8")
        )
        prompt_hasher.update(b"\0")
        prompt_hasher.update(
            prompt.encode("utf-8")
        )
        prompt_hasher.update(b"\0")

    input_fingerprint = (
        prompt_hasher.hexdigest()
    )

    # Fingerprint the exact async output containing sample #1.
    output_hasher = hashlib.sha256()

    with open(savepath, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            output_hasher.update(chunk)

    async_output_fingerprint = (
        output_hasher.hexdigest()
    )

    # --------------------------------------------------------------
    # Sidecar checkpoint.
    #
    # Only EXTRA samples are stored here.
    # Async sample #1 remains authoritative in `savepath`.
    # --------------------------------------------------------------
    checkpoint_path = (
        savepath
        + ".multisample_checkpoint.json"
    )

    expected_metadata = {
        "version": 1,
        "model": "gpt-6-luna",
        "temperature": temperature,
        "requested_n": requested_n,
        "input_fingerprint": input_fingerprint,
        "async_output_fingerprint":
            async_output_fingerprint,
    }

    def atomic_save_checkpoint(obj):
        tmp_path = checkpoint_path + ".tmp"

        with open(
            tmp_path,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                obj,
                f,
                ensure_ascii=False,
                indent=2,
            )
            f.flush()
            os.fsync(f.fileno())

        os.replace(
            tmp_path,
            checkpoint_path,
        )

    # A deliberate rewrite means a new async sample #1 was created,
    # therefore an old sidecar must NOT be silently reused.
    if rewrite:

        checkpoint = dict(
            expected_metadata
        )
        checkpoint["samples"] = {}

        atomic_save_checkpoint(
            checkpoint
        )

    elif osp.exists(checkpoint_path):

        with open(
            checkpoint_path,
            "r",
            encoding="utf-8",
        ) as f:
            checkpoint = json.load(f)

        for key, expected_value in (
            expected_metadata.items()
        ):
            actual_value = checkpoint.get(key)

            if actual_value != expected_value:
                raise RuntimeError(
                    "Multi-sample checkpoint metadata "
                    f"mismatch for {key!r}: "
                    f"expected {expected_value!r}, "
                    f"found {actual_value!r}. "
                    "Refusing to mix responses from "
                    "different runs."
                )

        if not isinstance(
            checkpoint.get("samples"),
            dict,
        ):
            raise RuntimeError(
                "Invalid multi-sample checkpoint: "
                "'samples' must be a dict."
            )

    else:

        checkpoint = dict(
            expected_metadata
        )
        checkpoint["samples"] = {}

        # Create metadata checkpoint before paid extra samples start.
        atomic_save_checkpoint(
            checkpoint
        )

    # --------------------------------------------------------------
    # Parse authoritative async sample #1 records.
    # --------------------------------------------------------------
    async_records = []

    with open(
        savepath,
        "r",
        encoding="utf-8",
    ) as f:

        for line_no, line in enumerate(
            f,
            start=1,
        ):

            line = line.strip()

            if not line:
                continue

            try:
                json_obj = json.loads(line)

            except Exception as exc:
                raise RuntimeError(
                    "Invalid JSON in async output "
                    f"at line {line_no}: {exc}"
                )

            async_records.append(
                json_obj
            )

    if len(async_records) != len(
        non_empty_results
    ):
        raise RuntimeError(
            "Async output record count does not "
            "match number of non-empty prompts: "
            f"{len(async_records)} vs "
            f"{len(non_empty_results)}."
        )

    openai_result = []

    # --------------------------------------------------------------
    # Stage B — obtain ONLY missing independent samples.
    # Each successful extra sample is checkpointed immediately.
    # --------------------------------------------------------------
    for record_idx, json_obj in enumerate(
        async_records
    ):

        if not isinstance(json_obj, list):
            raise RuntimeError(
                "Unexpected async output record type "
                f"at record {record_idx}: "
                f"{type(json_obj).__name__}"
            )

        if len(json_obj) < 2:
            raise RuntimeError(
                "Unexpected async output record "
                f"length at record {record_idx}: "
                f"{len(json_obj)}"
            )

        request_obj = json_obj[0]
        content = json_obj[1]
        idx = json_obj[-1]

        base_choices = []

        if content == "":
            # Preserve legacy empty-result behavior.
            openai_result.append(
                ("", idx)
            )
            continue

        if isinstance(idx, int):

            if not isinstance(content, dict):
                raise RuntimeError(
                    "Successful async record does not "
                    f"contain a dict response: {idx}"
                )

            response_choices = content.get(
                "choices",
                [],
            )

            base_choices = [
                x["message"]["content"]
                for x in response_choices
            ]

            # The async job is explicitly n=1.
            if len(base_choices) != 1:
                raise RuntimeError(
                    "Async GapGPT n=1 request "
                    f"returned {len(base_choices)} "
                    "choices; expected exactly 1."
                )

        else:
            # Preserve the original processor's failure-record
            # interpretation. No valid async sample is available.
            if len(json_obj) < 3:
                raise RuntimeError(
                    "Cannot recover request index from "
                    f"failed async record {record_idx}."
                )

            idx = json_obj[-2]

            if not isinstance(idx, int):
                raise RuntimeError(
                    "Failed async record has invalid "
                    f"request index: {idx!r}"
                )

            base_choices = []

        if not isinstance(request_obj, dict):
            raise RuntimeError(
                f"Invalid request object for index {idx}."
            )

        messages = request_obj.get(
            "messages",
            [],
        )

        if (
            not isinstance(messages, list)
            or len(messages) < 1
            or not isinstance(
                messages[0],
                dict,
            )
            or "content" not in messages[0]
        ):
            raise RuntimeError(
                "Invalid request messages for "
                f"index {idx}."
            )

        request_prompt = (
            messages[0]["content"]
        )

        request_model = request_obj.get(
            "model",
            "gpt-6-luna",
        )

        request_temperature = (
            request_obj.get(
                "temperature",
                temperature,
            )
        )

        missing_count = (
            requested_n
            - len(base_choices)
        )

        if missing_count < 0:
            raise RuntimeError(
                f"Too many base choices for index {idx}."
            )

        sample_key = str(idx)

        extras = checkpoint[
            "samples"
        ].get(
            sample_key,
            [],
        )

        if not isinstance(extras, list):
            raise RuntimeError(
                "Checkpoint sample entry must be "
                f"a list for index {idx}."
            )

        if len(extras) > missing_count:
            raise RuntimeError(
                "Checkpoint contains too many extra "
                f"samples for index {idx}: "
                f"{len(extras)} > {missing_count}."
            )

        # Resume exactly where the previous process stopped.
        while len(extras) < missing_count:

            extra_result = openai_text_api(
                request_prompt,
                api_key,
                model_name=request_model,
                temperature=request_temperature,
                n=1,
            )

            extra_choices = [
                x["message"]["content"]
                for x in extra_result["choices"]
            ]

            if len(extra_choices) != 1:
                raise RuntimeError(
                    "Extra independent n=1 request "
                    f"returned {len(extra_choices)} "
                    "choices; expected exactly 1."
                )

            text = extra_choices[0]

            if (
                not isinstance(text, str)
                or not text.strip()
            ):
                raise RuntimeError(
                    "Extra independent sample "
                    f"for index {idx} is empty."
                )

            extras.append(text)

            checkpoint[
                "samples"
            ][sample_key] = extras

            # Critical recovery guarantee:
            # commit immediately after every paid success.
            atomic_save_checkpoint(
                checkpoint
            )

            print(
                "[GapGPT checkpoint] "
                f"request={idx}, "
                f"extra={len(extras)}/"
                f"{missing_count}"
            )

        choices = (
            base_choices
            + extras
        )

        if len(choices) != requested_n:
            raise RuntimeError(
                "Provider adapter produced "
                f"{len(choices)} choices for "
                f"index {idx}; expected "
                f"{requested_n}."
            )

        openai_result.append(
            (
                choices,
                idx,
            )
        )

    openai_result = sorted(
        openai_result,
        key=lambda x: x[-1],
    )

    if len(openai_result) != len(
        non_empty_results
    ):
        raise RuntimeError(
            "Final multi-sample result count "
            "does not match non-empty prompts."
        )

    results = [
        ("", idx)
        for idx in range(
            len(input_text)
        )
    ]

    for i, r in enumerate(
        openai_result
    ):
        results[
            non_empty_results[i]
        ] = r

    return results

def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-3.5-turbo":
        print("Warning: gpt-3.5-turbo may change over time. Returning num tokens assuming gpt-3.5-turbo-0301.")
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301")
    elif model == "gpt-4":
        print("Warning: gpt-4 may change over time. Returning num tokens assuming gpt-4-0314.")
        return num_tokens_from_messages(messages, model="gpt-4-0314")
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif model == "gpt-4-0314":
        tokens_per_message = 3
        tokens_per_name = 1
    else:
        raise NotImplementedError(f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens.""")
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


def num_tokens_from_string(string: str, model = "text-davinci-003") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def load_partial_openai_result(data_path, dataset_name, prompt_key):
    file_name = osp.join(data_path, f"{dataset_name}_openai.pt")
    if osp.exists(file_name):
        return torch.load(file_name, map_location='cpu')
    else:
        return None



def save_partial_openai_result(data_path, dataset_name, data, key = 'zero_shot', load_pre_existing = None, num_of_elements = -1, rewrite = True):
    if not osp.exists(osp.join(data_path, f"{dataset_name}_openai.pt")):
        ## create new datastore
        datastore = {}
        datastore['zero_shot'] = ["" for _ in range(num_of_elements)]
        if load_pre_existing != None:
            pre_existing = torch.load(osp.join(data_path, pre_existing))
            datastore['zero_shot'] = pre_existing
    else:
        datastore = load_partial_openai_result(data_path, dataset_name, key)
        if datastore == None:
            datastore = {}
            datastore['zero_shot'] = ["" for _ in range(num_of_elements)]
            if load_pre_existing != None:
                pre_existing = torch.load(osp.join(data_path, pre_existing))
                datastore['zero_shot'] = pre_existing

    if datastore.get(key) == None:
        datastore[key] = ["" for _ in range(num_of_elements)]

    for i in range(len(data)):
        if (data[i] != "" and datastore[key][i] == "") or (rewrite and data[i] != ""):
            datastore[key][i] = data[i]
    torch.save(datastore, osp.join(data_path, f"{dataset_name}_openai.pt"))

        

def load_mapping_2():
    # arxiv_mapping = {
    # 'arxiv cs ai': 'cs.AI',
    # 'arxiv cs cl': 'cs.CL',
    # 'arxiv cs cc': 'cs.CC',
    # 'arxiv cs ce': 'cs.CE',
    # 'arxiv cs cg': 'cs.CG',
    # 'arxiv cs gt': 'cs.GT',
    # 'arxiv cs cv': 'cs.CV',
    # 'arxiv cs cy': 'cs.CY',
    # 'arxiv cs cr': 'cs.CR',
    # 'arxiv cs ds': 'cs.DS',
    # 'arxiv cs db': 'cs.DB',
    # 'arxiv cs dl': 'cs.DL',
    # 'arxiv cs dm': 'cs.DM',
    # 'arxiv cs dc': 'cs.DC',
    # 'arxiv cs et': 'cs.ET',
    # 'arxiv cs fl': 'cs.FL',
    # 'arxiv cs gl': 'cs.GL',
    # 'arxiv cs gr': 'cs.GR',
    # 'arxiv cs ar': 'cs.AR',
    # 'arxiv cs hc': 'cs.HC',
    # 'arxiv cs ir': 'cs.IR',
    # 'arxiv cs it': 'cs.IT',
    # 'arxiv cs lo': 'cs.LO',
    # 'arxiv cs lg': 'cs.LG',
    # 'arxiv cs ms': 'cs.MS',
    # 'arxiv cs ma': 'cs.MA',
    # 'arxiv cs mm': 'cs.MM',
    # 'arxiv cs ni': 'cs.NI',
    # 'arxiv cs ne': 'cs.NE',
    # 'arxiv cs na': 'cs.NA',
    # 'arxiv cs os': 'cs.OS',
    # 'arxiv cs oh': 'cs.OH',
    # 'arxiv cs pf': 'cs.PF',
    # 'arxiv cs pl': 'cs.PL',
    # 'arxiv cs ro': 'cs.RO',
    # 'arxiv cs si': 'cs.SI',
    # 'arxiv cs se': 'cs.SE',
    # 'arxiv cs sd': 'cs.SD',
    # 'arxiv cs sc': 'cs.SC',
    # 'arxiv cs sy': 'cs.SY'
    # }

    arxiv_mapping = {'arxiv cs ai': 'Artificial Intelligence', 'arxiv cs cl': 'Computation and Language', 'arxiv cs cc': 'Computational Complexity', 'arxiv cs ce': 'Computational Engineering, Finance, and Science', 'arxiv cs cg': 'Computational Geometry', 'arxiv cs gt': 'Computer Science and Game Theory', 'arxiv cs cv': 'Computer Vision and Pattern Recognition', 'arxiv cs cy': 'Computers and Society', 'arxiv cs cr': 'Cryptography and Security', 'arxiv cs ds': 'Data Structures and Algorithms', 'arxiv cs db': 'Databases', 'arxiv cs dl': 'Digital Libraries', 'arxiv cs dm': 'Discrete Mathematics', 'arxiv cs dc': 'Distributed, Parallel, and Cluster Computing', 'arxiv cs et': 'Emerging Technologies', 'arxiv cs fl': 'Formal Languages and Automata Theory', 'arxiv cs gl': 'General Literature', 'arxiv cs gr': 'Graphics', 'arxiv cs ar': 'Hardware Architecture', 'arxiv cs hc': 'Human-Computer Interaction', 'arxiv cs ir': 'Information Retrieval', 'arxiv cs it': 'Information Theory', 'arxiv cs lo': 'Logic in Computer Science', 'arxiv cs lg': 'Machine Learning', 'arxiv cs ms': 'Mathematical Software', 'arxiv cs ma': 'Multiagent Systems', 'arxiv cs mm': 'Multimedia', 'arxiv cs ni': 'Networking and Internet Architecture', 'arxiv cs ne': 'Neural and Evolutionary Computing', 'arxiv cs na': 'Numerical Analysis', 'arxiv cs os': 'Operating Systems', 'arxiv cs oh': 'Other Computer Science', 'arxiv cs pf': 'Performance', 'arxiv cs pl': 'Programming Languages', 'arxiv cs ro': 'Robotics', 'arxiv cs si': 'Social and Information Networks', 'arxiv cs se': 'Software Engineering', 'arxiv cs sd': 'Sound', 'arxiv cs sc': 'Symbolic Computation', 'arxiv cs sy': 'Systems and Control'}
    citeseer_mapping = {
        "Agents": "Agents",
        "ML": "Machine Learning",
        "IR": "Information Retrieval",
        "DB": "Database",
        "HCI": "Human Computer Interaction",
        "AI": "Artificial Intelligence"
    }
    pubmed_mapping = {
        'Diabetes Mellitus, Experimental': 'Diabetes Mellitus Experimental',
        'Diabetes Mellitus Type 1': 'Diabetes Mellitus Type 1',
        'Diabetes Mellitus Type 2': 'Diabetes Mellitus Type 2'
    }
    cora_mapping = {
        'Rule_Learning': "Rule_Learning",
        'Neural_Networks': "Neural_Networks",
        'Case_Based': "Case_Based",
        'Genetic_Algorithms': "Genetic_Algorithms",
        'Theory': "Theory",
        'Reinforcement_Learning': "Reinforcement_Learning",
        'Probabilistic_Methods': "Probabilistic_Methods"
    }

    products_mapping = {'Home & Kitchen': 'Home & Kitchen',
        'Health & Personal Care': 'Health & Personal Care',
        'Beauty': 'Beauty',
        'Sports & Outdoors': 'Sports & Outdoors',
        'Books': 'Books',
        'Patio, Lawn & Garden': 'Patio, Lawn & Garden',
        'Toys & Games': 'Toys & Games',
        'CDs & Vinyl': 'CDs & Vinyl',
        'Cell Phones & Accessories': 'Cell Phones & Accessories',
        'Grocery & Gourmet Food': 'Grocery & Gourmet Food',
        'Arts, Crafts & Sewing': 'Arts, Crafts & Sewing',
        'Clothing, Shoes & Jewelry': 'Clothing, Shoes & Jewelry',
        'Electronics': 'Electronics',
        'Movies & TV': 'Movies & TV',
        'Software': 'Software',
        'Video Games': 'Video Games',
        'Automotive': 'Automotive',
        'Pet Supplies': 'Pet Supplies',
        'Office Products': 'Office Products',
        'Industrial & Scientific': 'Industrial & Scientific',
        'Musical Instruments': 'Musical Instruments',
        'Tools & Home Improvement': 'Tools & Home Improvement',
        'Magazine Subscriptions': 'Magazine Subscriptions',
        'Baby Products': 'Baby Products',
        'label 25': 'label 25',
        'Appliances': 'Appliances',
        'Kitchen & Dining': 'Kitchen & Dining',
        'Collectibles & Fine Art': 'Collectibles & Fine Art',
        'All Beauty': 'All Beauty',
        'Luxury Beauty': 'Luxury Beauty',
        'Amazon Fashion': 'Amazon Fashion',
        'Computers': 'Computers',
        'All Electronics': 'All Electronics',
        'Purchase Circles': 'Purchase Circles',
        'MP3 Players & Accessories': 'MP3 Players & Accessories',
        'Gift Cards': 'Gift Cards',
        'Office & School Supplies': 'Office & School Supplies',
        'Home Improvement': 'Home Improvement',
        'Camera & Photo': 'Camera & Photo',
        'GPS & Navigation': 'GPS & Navigation',
        'Digital Music': 'Digital Music',
        'Car Electronics': 'Car Electronics',
        'Baby': 'Baby',
        'Kindle Store': 'Kindle Store',
        'Buy a Kindle': 'Buy a Kindle',
        'Furniture & D&#233;cor': 'Furniture & Decor',
        '#508510': '#508510'}

    wikics_mapping = {
        'Computational linguistics': 'Computational linguistics',
        'Databases': 'Databases',
        'Operating systems': 'Operating systems',
        'Computer architecture': 'Computer architecture',
        'Computer security': 'Computer security',
        'Internet protocols': 'Internet protocols',
        'Computer file systems': 'Computer file systems',
        'Distributed computing architecture': 'Distributed computing architecture',
        'Web technology': 'Web technology',
        'Programming language topics': 'Programming language topics'
    }

    tolokers_mapping = {
        'not banned': 'not banned',
        'banned': 'banned'
    }

    twenty_newsgroup_mapping = {'alt.atheism': 'News about atheism.', 'comp.graphics': 'News about computer graphics.', 'comp.os.ms-windows.misc': 'News about Microsoft Windows.', 'comp.sys.ibm.pc.hardware': 'News about IBM PC hardware.', 'comp.sys.mac.hardware': 'News about Mac hardware.', 'comp.windows.x': 'News about the X Window System.', 'misc.forsale': 'Items for sale.', 'rec.autos': 'News about automobiles.', 'rec.motorcycles': 'News about motorcycles.', 'rec.sport.baseball': 'News about baseball.', 'rec.sport.hockey': 'News about hockey.', 'sci.crypt': 'News about cryptography.', 'sci.electronics': 'News about electronics.', 'sci.med': 'News about medicine.', 'sci.space': 'News about space and astronomy.', 'soc.religion.christian': 'News about Christianity.', 'talk.politics.guns': 'News about gun politics.', 'talk.politics.mideast': 'News about Middle East politics.', 'talk.politics.misc': 'News about miscellaneous political topics.', 'talk.religion.misc': 'News about miscellaneous religious topics.'}



    return {
        'arxiv': arxiv_mapping, 
        'citeseer': citeseer_mapping, 
        'pubmed': pubmed_mapping, 
        'cora': cora_mapping, 
        'products': products_mapping,
        'wikics': wikics_mapping,
        'tolokers': tolokers_mapping,
        '20newsgroup': twenty_newsgroup_mapping
    }





def load_mapping():
    arxiv_mapping = {
    'arxiv cs ai': 'cs.AI',
    'arxiv cs cl': 'cs.CL',
    'arxiv cs cc': 'cs.CC',
    'arxiv cs ce': 'cs.CE',
    'arxiv cs cg': 'cs.CG',
    'arxiv cs gt': 'cs.GT',
    'arxiv cs cv': 'cs.CV',
    'arxiv cs cy': 'cs.CY',
    'arxiv cs cr': 'cs.CR',
    'arxiv cs ds': 'cs.DS',
    'arxiv cs db': 'cs.DB',
    'arxiv cs dl': 'cs.DL',
    'arxiv cs dm': 'cs.DM',
    'arxiv cs dc': 'cs.DC',
    'arxiv cs et': 'cs.ET',
    'arxiv cs fl': 'cs.FL',
    'arxiv cs gl': 'cs.GL',
    'arxiv cs gr': 'cs.GR',
    'arxiv cs ar': 'cs.AR',
    'arxiv cs hc': 'cs.HC',
    'arxiv cs ir': 'cs.IR',
    'arxiv cs it': 'cs.IT',
    'arxiv cs lo': 'cs.LO',
    'arxiv cs lg': 'cs.LG',
    'arxiv cs ms': 'cs.MS',
    'arxiv cs ma': 'cs.MA',
    'arxiv cs mm': 'cs.MM',
    'arxiv cs ni': 'cs.NI',
    'arxiv cs ne': 'cs.NE',
    'arxiv cs na': 'cs.NA',
    'arxiv cs os': 'cs.OS',
    'arxiv cs oh': 'cs.OH',
    'arxiv cs pf': 'cs.PF',
    'arxiv cs pl': 'cs.PL',
    'arxiv cs ro': 'cs.RO',
    'arxiv cs si': 'cs.SI',
    'arxiv cs se': 'cs.SE',
    'arxiv cs sd': 'cs.SD',
    'arxiv cs sc': 'cs.SC',
    'arxiv cs sy': 'cs.SY'
    }

    # arxiv_mapping = {'arxiv cs ai': 'Artificial Intelligence', 'arxiv cs cl': 'Computation and Language', 'arxiv cs cc': 'Computational Complexity', 'arxiv cs ce': 'Computational Engineering, Finance, and Science', 'arxiv cs cg': 'Computational Geometry', 'arxiv cs gt': 'Computer Science and Game Theory', 'arxiv cs cv': 'Computer Vision and Pattern Recognition', 'arxiv cs cy': 'Computers and Society', 'arxiv cs cr': 'Cryptography and Security', 'arxiv cs ds': 'Data Structures and Algorithms', 'arxiv cs db': 'Databases', 'arxiv cs dl': 'Digital Libraries', 'arxiv cs dm': 'Discrete Mathematics', 'arxiv cs dc': 'Distributed, Parallel, and Cluster Computing', 'arxiv cs et': 'Emerging Technologies', 'arxiv cs fl': 'Formal Languages and Automata Theory', 'arxiv cs gl': 'General Literature', 'arxiv cs gr': 'Graphics', 'arxiv cs ar': 'Hardware Architecture', 'arxiv cs hc': 'Human-Computer Interaction', 'arxiv cs ir': 'Information Retrieval', 'arxiv cs it': 'Information Theory', 'arxiv cs lo': 'Logic in Computer Science', 'arxiv cs lg': 'Machine Learning', 'arxiv cs ms': 'Mathematical Software', 'arxiv cs ma': 'Multiagent Systems', 'arxiv cs mm': 'Multimedia', 'arxiv cs ni': 'Networking and Internet Architecture', 'arxiv cs ne': 'Neural and Evolutionary Computing', 'arxiv cs na': 'Numerical Analysis', 'arxiv cs os': 'Operating Systems', 'arxiv cs oh': 'Other Computer Science', 'arxiv cs pf': 'Performance', 'arxiv cs pl': 'Programming Languages', 'arxiv cs ro': 'Robotics', 'arxiv cs si': 'Social and Information Networks', 'arxiv cs se': 'Software Engineering', 'arxiv cs sd': 'Sound', 'arxiv cs sc': 'Symbolic Computation', 'arxiv cs sy': 'Systems and Control'}
    citeseer_mapping = {
        "Agents": "Agents",
        "ML": "Machine Learning",
        "IR": "Information Retrieval",
        "DB": "Database",
        "HCI": "Human Computer Interaction",
        "AI": "Artificial Intelligence"
    }
    pubmed_mapping = {
        'Diabetes Mellitus, Experimental': 'Diabetes Mellitus Experimental',
        'Diabetes Mellitus Type 1': 'Diabetes Mellitus Type 1',
        'Diabetes Mellitus Type 2': 'Diabetes Mellitus Type 2'
    }
    cora_mapping = {
        'Rule_Learning': "Rule_Learning",
        'Neural_Networks': "Neural_Networks",
        'Case_Based': "Case_Based",
        'Genetic_Algorithms': "Genetic_Algorithms",
        'Theory': "Theory",
        'Reinforcement_Learning': "Reinforcement_Learning",
        'Probabilistic_Methods': "Probabilistic_Methods"
    }

    products_mapping = {'Home & Kitchen': 'Home & Kitchen',
        'Health & Personal Care': 'Health & Personal Care',
        'Beauty': 'Beauty',
        'Sports & Outdoors': 'Sports & Outdoors',
        'Books': 'Books',
        'Patio, Lawn & Garden': 'Patio, Lawn & Garden',
        'Toys & Games': 'Toys & Games',
        'CDs & Vinyl': 'CDs & Vinyl',
        'Cell Phones & Accessories': 'Cell Phones & Accessories',
        'Grocery & Gourmet Food': 'Grocery & Gourmet Food',
        'Arts, Crafts & Sewing': 'Arts, Crafts & Sewing',
        'Clothing, Shoes & Jewelry': 'Clothing, Shoes & Jewelry',
        'Electronics': 'Electronics',
        'Movies & TV': 'Movies & TV',
        'Software': 'Software',
        'Video Games': 'Video Games',
        'Automotive': 'Automotive',
        'Pet Supplies': 'Pet Supplies',
        'Office Products': 'Office Products',
        'Industrial & Scientific': 'Industrial & Scientific',
        'Musical Instruments': 'Musical Instruments',
        'Tools & Home Improvement': 'Tools & Home Improvement',
        'Magazine Subscriptions': 'Magazine Subscriptions',
        'Baby Products': 'Baby Products',
        'label 25': 'label 25',
        'Appliances': 'Appliances',
        'Kitchen & Dining': 'Kitchen & Dining',
        'Collectibles & Fine Art': 'Collectibles & Fine Art',
        'All Beauty': 'All Beauty',
        'Luxury Beauty': 'Luxury Beauty',
        'Amazon Fashion': 'Amazon Fashion',
        'Computers': 'Computers',
        'All Electronics': 'All Electronics',
        'Purchase Circles': 'Purchase Circles',
        'MP3 Players & Accessories': 'MP3 Players & Accessories',
        'Gift Cards': 'Gift Cards',
        'Office & School Supplies': 'Office & School Supplies',
        'Home Improvement': 'Home Improvement',
        'Camera & Photo': 'Camera & Photo',
        'GPS & Navigation': 'GPS & Navigation',
        'Digital Music': 'Digital Music',
        'Car Electronics': 'Car Electronics',
        'Baby': 'Baby',
        'Kindle Store': 'Kindle Store',
        'Buy a Kindle': 'Buy a Kindle',
        'Furniture & D&#233;cor': 'Furniture & Decor',
        '#508510': '#508510'}

    wikics_mapping = {
        'Computational linguistics': 'Computational linguistics',
        'Databases': 'Databases',
        'Operating systems': 'Operating systems',
        'Computer architecture': 'Computer architecture',
        'Computer security': 'Computer security',
        'Internet protocols': 'Internet protocols',
        'Computer file systems': 'Computer file systems',
        'Distributed computing architecture': 'Distributed computing architecture',
        'Web technology': 'Web technology',
        'Programming language topics': 'Programming language topics'
    }

    tolokers_mapping = {
        'not banned': 'not banned',
        'banned': 'banned'
    }

    twenty_newsgroup_mapping = {'alt.atheism': 'News about atheism.', 'comp.graphics': 'News about computer graphics.', 'comp.os.ms-windows.misc': 'News about Microsoft Windows.', 'comp.sys.ibm.pc.hardware': 'News about IBM PC hardware.', 'comp.sys.mac.hardware': 'News about Mac hardware.', 'comp.windows.x': 'News about the X Window System.', 'misc.forsale': 'Items for sale.', 'rec.autos': 'News about automobiles.', 'rec.motorcycles': 'News about motorcycles.', 'rec.sport.baseball': 'News about baseball.', 'rec.sport.hockey': 'News about hockey.', 'sci.crypt': 'News about cryptography.', 'sci.electronics': 'News about electronics.', 'sci.med': 'News about medicine.', 'sci.space': 'News about space and astronomy.', 'soc.religion.christian': 'News about Christianity.', 'talk.politics.guns': 'News about gun politics.', 'talk.politics.mideast': 'News about Middle East politics.', 'talk.politics.misc': 'News about miscellaneous political topics.', 'talk.religion.misc': 'News about miscellaneous religious topics.'}



    return {
        'arxiv': arxiv_mapping, 
        'citeseer': citeseer_mapping, 
        'pubmed': pubmed_mapping, 
        'cora': cora_mapping, 
        'products': products_mapping,
        'wikics': wikics_mapping,
        'tolokers': tolokers_mapping,
        '20newsgroup': twenty_newsgroup_mapping
    }

def retrieve_dict(clean_t):
    start = clean_t.find('[')
    end = clean_t.find(']', start) + 1  # +1 to include the closing bracket
    list_str = clean_t[start:end]
    result = ast.literal_eval(list_str)
    return result


def compute_ece(confidences, predictions, labels, n_bins=10):
    """
    Compute Expected Calibration Error.
    
    Parameters:
    - confidences (Tensor): Tensor of predicted confidences
    - predictions (Tensor): Tensor of predicted classes
    - labels (Tensor): Tensor of true labels
    - n_bins (int): Number of bins to use for calibration

    Returns:
    - ece (float): Expected Calibration Error
    """
    
    bin_boundaries = torch.linspace(0, 1, n_bins + 1)
    bin_lowers = bin_boundaries[:-1]
    bin_uppers = bin_boundaries[1:]

    ece = 0.0
    for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
        in_bin = (confidences > bin_lower.item()) * (confidences <= bin_upper.item())
        prop_in_bin = in_bin.float().mean()
        
        if prop_in_bin.item() > 0:
            accuracy_in_bin = (predictions[in_bin] == labels[in_bin]).float().mean()
            avg_confidence_in_bin = confidences[in_bin].mean()
            ece += torch.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin * ((bin_lower + bin_upper) / 2.0)

    return ece

# Example usage:
# confidences = torch.tensor([...])  # Replace with your confidence values
# predictions = torch.tensor([...])  # Replace with your predicted class labels
# labels = torch.tensor([...])  # Replace with your true labels

# ece = compute_ece(confidences, predictions, labels, n_bins=10)
# print(f"Expected Calibration Error: {ece:.2%}")




def plot_calibration_curve(confidences, predictions, labels, data_name = 'cora', method = 'zero_shot', n_bins=10):
    """
    Plots the calibration curve.
    
    Parameters:
    - confidences (Tensor): Tensor of predicted confidences.
    - predictions (Tensor): Tensor of predicted classes.
    - labels (Tensor): Tensor of true labels.
    - n_bins (int): Number of bins to use for calibration.
    """
    
    bin_boundaries = torch.linspace(0, 1, n_bins + 1)
    bin_lowers = bin_boundaries[:-1]
    bin_uppers = bin_boundaries[1:]

    bin_confidences = []
    bin_accuracies = []

    for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
        in_bin = (confidences > bin_lower.item()) & (confidences <= bin_upper.item())
        if in_bin.sum().item() > 0:
            bin_confidence = confidences[in_bin].mean().item()
            bin_accuracy = (predictions[in_bin] == labels[in_bin]).float().mean().item()

            # bin_confidences.append(bin_confidence)
            bin_confidences.append(bin_lower.item())
            bin_accuracies.append(bin_accuracy)

    # Plotting
    plt.bar(bin_confidences, bin_accuracies, width=0.01, edgecolor="black", alpha=0.6, label="Model Accuracy")
    plt.plot([0, 1], [0, 1], linestyle="--", color="red", label="Perfect Calibration")
    plt.xlabel("Average Confidence of Bins")
    plt.ylabel("Accuracy")
    plt.title("Calibration Curve")
    plt.legend()
    plt.savefig("{}_{}_calibration_curve.png".format(data_name, method))
    plt.clf()

# Example usage:
# confidences = torch.tensor([...])  # Replace with your confidence values
# predictions = torch.tensor([...])  # Replace with your predicted class labels
# labels = torch.tensor([...])  # Replace with your true labels

# plot_calibration_curve(confidences, predictions, labels, n_bins=10)
