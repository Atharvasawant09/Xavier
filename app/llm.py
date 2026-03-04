"""
llm.py — LLM inference interface.
Dev mode  (LLM_USE_STUB=true) : Groq API — llama-3.1-8b-instant
Prod mode (LLM_USE_STUB=false): llama-cpp-python — Qwen2.5-7B-Instruct Q4_K_M on Xavier

Strict grounding: model is instructed to answer ONLY from provided context.
"""

from app.config import (
    LLM_USE_STUB, GROQ_API_KEY, GROQ_MODEL,
    LLM_MAX_TOKENS, LLM_TEMPERATURE, LLM_CONTEXT_WINDOW,
    LLM_N_GPU_LAYERS, LLM_N_THREADS, MODEL_PATH
)
from app.utils import get_logger, log_memory, check_memory_safe

logger = get_logger("llm")

# ── Lazy model holder — loaded once, reused across queries ────────────────────
_llm = None


# ── System Prompt — Strict Grounding ─────────────────────────────────────────
SYSTEM_PROMPT = """You are a document assistant. Your job is to answer questions strictly based on the document context provided below.

Rules you must follow without exception:
1. Answer ONLY using information present in the provided context.
2. If the answer is not in the context, respond with exactly: "I cannot find this information in the uploaded documents."
3. Do not use any external knowledge, assumptions, or information from your training data.
4. Always cite your source as: [Source: <filename>, Page <page_number>]
5. Be concise and factual. Do not speculate or elaborate beyond what the context states.
6. If the context contains partial information, share what is available and note it is partial."""


def build_prompt(question: str, context: str) -> str:
    """
    Builds the full prompt combining system instruction, context, and question.
    Keeps total length within LLM_CONTEXT_WINDOW tokens.
    """
    return f"""DOCUMENT CONTEXT:
{context}

---

QUESTION: {question}

ANSWER (based strictly on the above context only):"""


# ── Groq API (Dev Stub) ───────────────────────────────────────────────────────

def load_groq():
    """Initialises Groq client. Lightweight — no model download needed."""
    global _llm
    if _llm is not None:
        return _llm
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set in .env. Cannot use stub LLM.")
    from groq import Groq
    _llm = Groq(api_key=GROQ_API_KEY)
    logger.info(f"Groq client ready — model: {GROQ_MODEL}")
    return _llm


def generate_groq(question: str, context: str) -> str:
    """Calls Groq API with grounding prompt. Returns answer string."""
    client = load_groq()
    prompt = build_prompt(question, context)

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system",  "content": SYSTEM_PROMPT},
                {"role": "user",    "content": prompt},
            ],
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq API call failed: {e}")
        raise


# ── llama-cpp-python (Production — Xavier) ────────────────────────────────────

def load_llamacpp():
    """
    Loads Qwen2.5-7B-Instruct Q4_K_M GGUF via llama-cpp-python.
    Called once on first query. Respects memory limits before loading.
    """
    global _llm
    if _llm is not None:
        return _llm

    check_memory_safe()
    log_memory("before_llm_load")

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"GGUF model not found at {MODEL_PATH}. "
            "Download Qwen2.5-7B-Instruct-Q4_K_M.gguf to the model path."
        )

    from llama_cpp import Llama
    logger.info(f"Loading LLM from {MODEL_PATH} ...")
    _llm = Llama(
        model_path=str(MODEL_PATH),
        n_ctx=LLM_CONTEXT_WINDOW,
        n_gpu_layers=LLM_N_GPU_LAYERS,   # tune on Xavier: start at 20
        n_threads=LLM_N_THREADS,          # ARM Carmel: 4 threads
        verbose=False,
    )
    log_memory("after_llm_load")
    logger.info("LLM loaded and ready.")
    return _llm


def unload_llm():
    """
    Explicitly unloads the LLM from memory.
    Call this after query if memory is tight — frees ~6GB on Xavier.
    """
    global _llm
    if _llm is not None:
        del _llm
        _llm = None
        import gc
        gc.collect()
        log_memory("after_llm_unload")
        logger.info("LLM unloaded from memory.")


def generate_llamacpp(question: str, context: str) -> str:
    """Runs inference via llama-cpp-python. Returns answer string."""
    llm = load_llamacpp()
    prompt = build_prompt(question, context)

    full_prompt = f"<|system|>\n{SYSTEM_PROMPT}\n<|user|>\n{prompt}\n<|assistant|>\n"

    try:
        log_memory("before_inference")
        output = llm(
            full_prompt,
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
            stop=["<|user|>", "<|system|>"],
            echo=False,
        )
        log_memory("after_inference")
        return output["choices"][0]["text"].strip()
    except Exception as e:
        logger.error(f"llama-cpp inference failed: {e}")
        raise


# ── Main Entry Point ──────────────────────────────────────────────────────────

def generate_answer(question: str, context: str) -> str:
    """
    Generates a grounded answer from context.
    Routes to Groq (dev) or llama-cpp-python (prod) based on LLM_USE_STUB flag.

    Args:
        question: the user's question
        context:  formatted context string from retrieval.py (chunks + sources)

    Returns:
        answer string with inline source citations
    """
    logger.info(f"Generating answer — stub={LLM_USE_STUB}")

    if LLM_USE_STUB:
        return generate_groq(question, context)
    else:
        return generate_llamacpp(question, context)
