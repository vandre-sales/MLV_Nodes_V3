# IS_PROTO_COMMAND: FALSE
# RESTRICTION: AGENT ONLY
# CHMOD_MODE: WRITABLE
# FILE: ComfyUI/custom_nodes/MLV_Nodes_V3/nodes/_jc_engine.py
# DESCRIPTION: Motor de inferencia JoyCaption GGUF autonomo para MLV_Nodes_V3.
#              Self-contained - zero dependencia de ComfyUI-JoyCaption upstream.
#              Inclui folder_paths fix permanente, cache proprio isolado,
#              e funcoes de prompt/clean migradas.
# MODULE: INFERENCE
# DOC_TYPE: SOURCE
# ROLE: GGUF Inference Engine
# STATUS: ACTIVE
# BINDING_SCOPE: LOCAL
# TAGS: [JOYCAPTION, GGUF, INFERENCE, MLV, V3, UAIGF]
# COMPLEXITY: HIGH
# OP_TYPE: ATOMIC
# RISK: SAFE
# SCHEMA: UAIGF V4
# LIFE_CYCLE: PERSISTENT
# DATE: 2026-04-21T09:58:00-03:00
# MLV_Nodes_V3/nodes/_jc_engine.py
# Motor de inferência JoyCaption GGUF autônomo — MLV_Nodes_V3
# Self-contained: zero sys.path.insert, zero deps em ComfyUI-JoyCaption
# Inclui folder_paths fix permanente (LLM path correto via extra_model_paths.yaml)
# Cache _MLV_MODEL_CACHE isolado — prefixo "mlv_v3_" evita colisão com upstream
# Licença: Proprietário — Meliva Online © 2026

import torch
import gc
import os
import re
import base64
import io as _io
import sys
import json
from pathlib import Path
from PIL import Image
from torchvision.transforms import ToPILImage
import folder_paths
from huggingface_hub import hf_hub_download
from llama_cpp import Llama
from llama_cpp.llama_chat_format import Llava15ChatHandler


# ─── Configurações de ambiente ───────────────────────────────────────────────

class ModelLoadError(Exception):
    pass


def suppress_output(func):
    """Decorator: suprime stdout/stderr durante inicialização do modelo GGUF."""
    def wrapper(*args, **kwargs):
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        try:
            sys.stdout = _io.StringIO()
            sys.stderr = _io.StringIO()
            return func(*args, **kwargs)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    return wrapper


os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

if torch.cuda.is_available():
    torch.backends.cudnn.benchmark = True
    if hasattr(torch.backends, 'cuda'):
        if hasattr(torch.backends.cuda, 'matmul'):
            torch.backends.cuda.matmul.allow_tf32 = True
        if hasattr(torch.backends.cuda, 'allow_tf32'):
            torch.backends.cuda.allow_tf32 = True
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:128"


# ─── Carregar configuração (jc_data.json) ────────────────────────────────────
# Path resolve() garante funcionamento mesmo quando carregado via symlink

_DATA_PATH = Path(__file__).resolve().parent / "jc_data.json"
with open(_DATA_PATH, "r", encoding="utf-8") as _f:
    _config = json.load(_f)
    CAPTION_TYPE_MAP = _config["caption_type_map"]
    EXTRA_OPTIONS = _config["extra_options"]
    MODEL_SETTINGS = _config["model_settings"]
    CAPTION_LENGTH_CHOICES = _config["caption_length_choices"]
    GGUF_MODELS = _config["gguf_models"]
    GGUF_SETTINGS = _config["gguf_settings"]


# ─── Cache próprio (isolado do upstream) ─────────────────────────────────────
# Prefixo "mlv_v3_" evita colisão com _MODEL_CACHE do ComfyUI-JoyCaption

_MLV_MODEL_CACHE: dict = {}


# ─── Classe de inferência GGUF ───────────────────────────────────────────────

class JC_GGUF_Models:
    """Wrapper Llama/LLaVA para inferência JoyCaption GGUF.

    Replica JC_GGUF_Models do upstream com folder_paths fix permanente:
    usa get_folder_paths("LLM") em vez de models_dir hardcoded,
    resolvendo o path correto via extra_model_paths.yaml (NVMe/EBS/S3).
    """

    def __init__(self, model: str, processing_mode: str):
        try:
            # Fix permanente: resolver via extra_model_paths.yaml
            llm_paths = folder_paths.get_folder_paths("LLM")
            if llm_paths:
                models_dir = Path(llm_paths[0]).resolve()
            else:
                models_dir = Path(folder_paths.models_dir).resolve() / "LLM"

            llm_models_dir = (models_dir / "GGUF").resolve()
            llm_models_dir.mkdir(parents=True, exist_ok=True)

            model_filename = Path(model).name
            local_path = llm_models_dir / model_filename

            if not local_path.exists():
                if "/" not in model:
                    raise ValueError("Invalid model path")
                repo_path, filename = model.rsplit("/", 1)
                local_path = Path(hf_hub_download(
                    repo_id=repo_path,
                    filename=filename,
                    local_dir=str(llm_models_dir),
                    local_dir_use_symlinks=False
                )).resolve()

            mmproj_filename = GGUF_SETTINGS["mmproj_filename"]
            mmproj_path = llm_models_dir / mmproj_filename
            if not mmproj_path.exists():
                mmproj_path = Path(hf_hub_download(
                    repo_id="concedo/llama-joycaption-beta-one-hf-llava-mmproj-gguf",
                    filename=mmproj_filename,
                    local_dir=str(llm_models_dir),
                    local_dir_use_symlinks=False
                )).resolve()

            n_ctx = MODEL_SETTINGS["context_window"]
            n_batch = 2048
            n_threads = max(4, MODEL_SETTINGS["cpu_threads"])
            if processing_mode == "Auto":
                n_gpu_layers = -1 if torch.cuda.is_available() else 0
            elif processing_mode == "GPU":
                n_gpu_layers = -1
            else:  # CPU
                n_gpu_layers = 0

            self.model = self._initialize_model(
                local_path, mmproj_path, n_ctx, n_batch, n_threads, n_gpu_layers
            )

        except Exception as e:
            raise ModelLoadError(f"Model initialization failed: {str(e)}")

    @suppress_output
    def _initialize_model(self, local_path, mmproj_path, n_ctx, n_batch, n_threads, n_gpu_layers):
        return Llama(
            model_path=str(local_path),
            n_ctx=n_ctx,
            n_batch=n_batch,
            n_threads=n_threads,
            n_gpu_layers=n_gpu_layers,
            verbose=False,
            chat_handler=Llava15ChatHandler(clip_model_path=str(mmproj_path)),
            offload_kqv=True,
            numa=True
        )

    def generate(
        self,
        image: Image.Image,
        system: str,
        prompt: str,
        max_new_tokens: int,
        temperature: float,
        top_p: float,
        top_k: int,
    ) -> str:
        try:
            if image.mode != 'RGB':
                image = image.convert('RGB')

            image = image.resize(GGUF_SETTINGS["default_image_size"], Image.Resampling.BILINEAR)

            img_buffer = _io.BytesIO()
            image.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
            data_uri = f"data:image/png;base64,{img_base64}"

            messages = [
                {"role": "system", "content": system.strip()},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt.strip()},
                        {"type": "image_url", "image_url": {"url": data_uri}}
                    ]
                }
            ]

            completion_params = {
                "messages": messages,
                "max_tokens": max_new_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "stop": ["</s>", "User:", "Assistant:"],
                "stream": False,
                "repeat_penalty": 1.1,
                "mirostat_mode": 0
            }

            if top_k > 0:
                completion_params["top_k"] = top_k

            response = self._create_completion(completion_params)
            del messages
            return response["choices"][0]["message"]["content"].strip()

        except Exception as e:
            return f"Generation error: {str(e)}"
        finally:
            gc.collect()

    @suppress_output
    def _create_completion(self, completion_params):
        return self.model.create_chat_completion(**completion_params)


# ─── Helper stateless — interface para nodes V3 ──────────────────────────────

def get_or_load_model(model_name: str, processing_mode: str) -> JC_GGUF_Models:
    """Retorna modelo do cache ou carrega novo. Isolado do cache upstream.

    Chave: f"mlv_v3_{model_name}_{processing_mode}"
    Prefixo "mlv_v3_" garante zero colisão com _MODEL_CACHE do JC_GGUF.py upstream.
    """
    cache_key = f"mlv_v3_{model_name}_{processing_mode}"
    if cache_key not in _MLV_MODEL_CACHE:
        _MLV_MODEL_CACHE[cache_key] = JC_GGUF_Models(model_name, processing_mode)
    return _MLV_MODEL_CACHE[cache_key]


def evict_model(model_name: str, processing_mode: str) -> None:
    """Remove modelo do cache e libera VRAM. Usado por memory_management='Clear After Run'."""
    cache_key = f"mlv_v3_{model_name}_{processing_mode}"
    if cache_key in _MLV_MODEL_CACHE:
        del _MLV_MODEL_CACHE[cache_key]
        torch.cuda.empty_cache()
        gc.collect()


# ─── Prompt builder (migrado de joycaption_gguf_mlv.py — sem alteração lógica) ─

def _build_mlv_prompt(
    extra_options: list | None,
    character_name: str,
    caption_style: str,
) -> str:
    """Monta prompt compacto (~150 tokens max) com LOCKED rules primeiro.

    Ordem de prioridade (atenção do LLM):
      1. LOCKED restrictions (highest attention)
      2. Pronoun instruction
      3. Core task (genérico, sem name_ref — anti-hallucination B3)
      4. Subject context (name_ref como contexto, não presunção)
      5. Scope instructions
    """
    name_ref = character_name.strip() if character_name.strip() else "a person"

    locked = []
    pronoun_instr = []
    other = []
    if extra_options:
        for opt in extra_options:
            # Suporte a ambos os formatos: dict (V3.2) e str (legado)
            if isinstance(opt, dict):
                text = opt.get("text", "")
                category = opt.get("category", "OTHER")
            else:
                text = opt
                category = "OTHER"

            if category == "LOCKED":
                locked.append(text)
            elif category == "STYLE" and any(
                kw in text.lower() for kw in ('pronoun', 'she/', 'he/', 'they/', "'the person'")
            ):
                pronoun_instr.append(text)
            else:
                other.append(text)

    prompt = ""

    if locked:
        prompt += " ".join(locked) + " "

    if pronoun_instr:
        prompt += " ".join(pronoun_instr) + " "

    if caption_style == "Booru tag-like":
        prompt += "Write booru-style tags for this image."
    else:
        prompt += "Describe this image in natural prose."

    if character_name.strip() and name_ref != "a person":
        prompt += f" The subject is called {name_ref}."

    if other:
        prompt += " " + " ".join(other)

    MAX_PROMPT_CHARS = 800  # ~200 tokens
    if len(prompt) > MAX_PROMPT_CHARS:
        core_end = -1
        for marker in ["in natural prose.", "for this image.", f"called {name_ref}."]:
            idx = prompt.find(marker)
            if idx > 0:
                core_end = max(core_end, idx + len(marker))
        if core_end <= 0:
            core_end = len(prompt) // 2
        truncated = prompt[:core_end]
        remaining_parts = prompt[core_end:].strip().split(". ")
        for part in remaining_parts:
            if not part.strip():
                continue
            candidate = truncated + " " + part.strip() + "."
            if len(candidate) <= MAX_PROMPT_CHARS:
                truncated = candidate
            else:
                break
        prompt = truncated.strip()

    return prompt.strip()


# ─── Caption cleaner (migrado de joycaption_gguf_mlv.py — sem alteração lógica) ─

def _clean_caption(text: str) -> str:
    """Post-processing: remove meta-conversation, LOCKED attributes, degeneration.

    7 camadas de limpeza:
      1. ASSISTANT: markers
      2. Meta-conversation phrases
      3. Revision separators
      4. [bracketed content] — mantém texto interno
      5. LOCKED attribute removal (hair pattern)
      6. Token degeneration (repeated periods)
      7. Meta lines
    """
    original_text = text

    # 1. Remove ASSISTANT: markers
    text = re.sub(r'(?i)\bASSISTANT\s*:\s*', '', text)
    # 2. Remove meta-conversation phrases
    text = re.sub(
        r'(?i)\b(Now I\'ll|Let me|Here is|Here\'s|I will|I\'ll|Note:|Disclaimer:)\b.*?[.!]\s*',
        '', text
    )
    # 3. Truncate at revision separators
    text = re.sub(
        r'\s*--+\s*(Here|Now|Let|I\'ll|Revised|Rewritten|Updated|Caption:).*$',
        '', text, flags=re.DOTALL
    )
    text = re.sub(r'\s*---+.*$', '', text, flags=re.DOTALL)
    # 4. Remove [bracketed content] — keep inner text
    text = re.sub(r'\[([^\]]*)\]', r'\1', text)
    # 5. Remove verbalized instructions
    text = re.sub(r'(?i)(The person is the subject with trigger word\.?\s*)', '', text)
    text = re.sub(r'(?i)(Periods separate each descriptive element\.?\s*)', '', text)
    # 5b. LOCKED ATTRIBUTE REMOVAL — hair references
    sentences = re.split(r'(?<=[.!?])\s+', text)
    clean_sentences = []
    hair_pattern = re.compile(
        r'\b(hair|hairs|hairstyle|hair\s*style|haircut|bald|balding|'
        r'curly|wavy|straight\s+hair|braids?|ponytail|bun|bangs|fringe|'
        r'blonde|brunette|redhead|auburn|gray\s*hair|grey\s*hair|'
        r'short\s*hair|long\s*hair|dark\s*hair|light\s*hair|'
        r'shoulder.length|bob\s*cut|pixie\s*cut|afro|dreadlocks?|'
        r'tied\s*(back|up)|pulled\s*back|loose\s*hair)\b',
        re.IGNORECASE
    )
    for sent in sentences:
        if not hair_pattern.search(sent):
            clean_sentences.append(sent)
    text = ' '.join(clean_sentences)
    # 6. Remove token degeneration (repeated periods)
    text = re.sub(r'(\.\s*){3,}', '. ', text)
    text = re.sub(r'\.(\s*\.)+', '.', text)
    text = re.sub(r'[^.!?]*$', '', text).strip()
    if not text.endswith(('.', '!', '?')):
        text = re.sub(r'(\.\s*){3,}', '. ', text).strip()
    # 7. Remove meta lines
    lines = text.split('\n')
    clean_lines = [
        l for l in lines
        if l.strip() and not re.match(r'(?i)^(note:|please |if you|warning:)', l.strip())
    ]
    text = ' '.join(clean_lines)
    # Collapse multiple spaces
    text = re.sub(r'  +', ' ', text)

    result = text.strip()
    if not result:
        if not re.match(r'(?i)^(ASSISTANT|Here is|Note:|Let me)', original_text.strip()):
            return original_text.strip()
        return "[CAPTION_EMPTY]"
    return result
