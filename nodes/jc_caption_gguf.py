# IS_PROTO_COMMAND: FALSE
# RESTRICTION: AGENT ONLY
# CHMOD_MODE: WRITABLE
# FILE: ComfyUI/custom_nodes/MLV_Nodes_V3/nodes/jc_caption_gguf.py
# DESCRIPTION: Node V3 MLV_JCCaptionGGUF - Inferencia JoyCaption GGUF customizada
#              para LoRA training com protocolo LOCKED/UNLOCKED.
#              Self-contained: usa _jc_engine.py proprio, zero deps em upstream.
#              Lazy eval nativa V3: carrega modelo GGUF apenas quando imagem presente.
# MODULE: CAPTIONING
# DOC_TYPE: SOURCE
# ROLE: JoyCaption GGUF Caption V3 Node
# STATUS: ACTIVE
# BINDING_SCOPE: LOCAL
# TAGS: [JOYCAPTION, GGUF, CAPTION, MLV, V3, LAZY_EVAL, UAIGF]
# COMPLEXITY: HIGH
# OP_TYPE: ATOMIC
# RISK: SAFE
# SCHEMA: UAIGF V4
# LIFE_CYCLE: PERSISTENT
# DATE: 2026-04-21T10:05:00-03:00

# MLV_Nodes_V3/nodes/jc_caption_gguf.py
# Node V3: MLV_JCCaptionGGUF
# Inferencia JoyCaption GGUF com lazy eval nativa V3
# Licenca: Proprietario -- Meliva Online (c) 2026

import torch
import gc
from torchvision.transforms import ToPILImage
from comfy_api.latest import io, ui as comfy_ui

try:
    # Importacao relativa -- padrao ao carregar como pacote via ComfyUI
    from ._jc_engine import (
        GGUF_MODELS,
        MODEL_SETTINGS,
        get_or_load_model,
        evict_model,
        _build_mlv_prompt,
        _clean_caption,
    )
except ImportError:
    # Fallback absoluto -- usado em testes isolados (checkpoint / debug)
    from _jc_engine import (
        GGUF_MODELS,
        MODEL_SETTINGS,
        get_or_load_model,
        evict_model,
        _build_mlv_prompt,
        _clean_caption,
    )

# Tipo custom compativel com JOYCAPTION_EXTRA_OPTIONS
_JCOpts = io.Custom("JOYCAPTION_EXTRA_OPTIONS")

# Lista de modelos para o dropdown
_MODEL_LIST = list(GGUF_MODELS.keys())
# Default: modelo 11 (Q8_0 -- melhor qualidade/velocidade)
_DEFAULT_MODEL_IDX = min(11, len(_MODEL_LIST) - 1)

_DEFAULT_SYSTEM_PROMPT = (
    "You are a precise image captioner for AI training datasets. "
    "Output ONLY the caption -- no explanations, no meta-text, no assistant markers."
)


class MLV_JCCaptionGGUF(io.ComfyNode):
    """MLV JC Caption GGUF -- Inferencia customizada para LoRA training (V3).

    Diferencas vs V1 (JC_GGUF_MLV):
    - API V3 stateless: sem self.predictor, sem __init__
    - Lazy eval nativa: image marcada como lazy=True -- modelo nao carrega sem imagem
    - Cache via get_or_load_model() em _jc_engine._MLV_MODEL_CACHE (isolado do upstream)
    - folder_paths fix permanente em _jc_engine (sem patch externo)
    - LOCKED rules posicionadas no inicio do prompt (maior peso de atencao)
    - Post-processing: 7 camadas de limpeza via _clean_caption()
    """

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MLV_JCCaptionGGUF",
            display_name="MLV JC Caption GGUF",
            category="\U0001f9ecMLV/\U0001f4ddCaptioning",
            description=(
                "Inferencia JoyCaption GGUF para captions de LoRA training. "
                "LOCKED/UNLOCKED via MLV JC Extra Options. "
                "Lazy eval: modelo carregado apenas quando imagem conectada."
            ),
            is_output_node=True,
            inputs=[
                io.Combo.Input(
                    "model",
                    options=_MODEL_LIST,
                    default=_MODEL_LIST[_DEFAULT_MODEL_IDX],
                    tooltip="Modelo GGUF para captioning",
                ),
                io.Combo.Input(
                    "processing_mode",
                    options=["Auto", "GPU", "CPU"],
                    default="Auto",
                    tooltip="Auto: detecta melhor modo. GPU: mais rapido. CPU: economia de VRAM",
                ),
                io.Combo.Input(
                    "caption_style",
                    options=["Descriptive", "Straightforward", "Booru tag-like"],
                    default="Descriptive",
                    tooltip="Estilo do caption gerado",
                ),
                io.String.Input(
                    "system_prompt",
                    default=_DEFAULT_SYSTEM_PROMPT,
                    multiline=True,
                    tooltip="System prompt -- define comportamento do modelo",
                ),
                io.Int.Input(
                    "max_new_tokens",
                    default=256,
                    min=64,
                    max=512,
                    tooltip="Max tokens no output. 200 ideal para captions LoRA (50-200 tokens)",
                ),
                io.Float.Input(
                    "temperature",
                    default=0.3,
                    min=0.0,
                    max=2.0,
                    step=0.05,
                    tooltip="Menor = mais factual, menos alucinacao. 0.3 recomendado para LOCKED/UNLOCKED",
                ),
                io.Float.Input(
                    "top_p",
                    default=0.8,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip="Nucleus sampling. 0.8 restringe vocabulario, menos chances de violar LOCKED",
                ),
                io.Int.Input(
                    "top_k",
                    default=40,
                    min=0,
                    max=100,
                    tooltip="Top-K filtering. 40 limita escolhas, reduz violacoes criativas de LOCKED",
                ),
                io.Combo.Input(
                    "memory_management",
                    options=["Keep in Memory", "Clear After Run", "Global Cache"],
                    default="Global Cache",
                    tooltip="Global Cache: mais rapido para batch. Clear After Run: libera VRAM apos cada run",
                ),
                io.Boolean.Input(
                    "post_process",
                    default=True,
                    tooltip="Limpar output: remove ASSISTANT markers, brackets, meta-conversation",
                ),
                # Lazy eval nativa V3 -- modelo GGUF so carrega quando imagem presente
                io.Image.Input(
                    "image",
                    lazy=True,
                    optional=True,
                    tooltip="Imagem de referencia. Se ausente, retorna caption vazio sem carregar modelo.",
                ),
                # JOYCAPTION_EXTRA_OPTIONS -- conectar MLV JC Extra Options
                _JCOpts.Input(
                    "extra_options",
                    optional=True,
                    tooltip="Conectar MLV JC Extra Options para opcoes LOCKED/UNLOCKED",
                ),
            ],
            outputs=[
                io.String.Output(display_name="caption"),
                io.String.Output(display_name="prompt_used"),
            ],
        )

    @classmethod
    def check_lazy_status(cls, image=None, **kwargs) -> list:
        """Lazy eval V3: solicita avaliacao de image apenas quando necessario.

        Se image=None (nao conectada ou nao avaliada): retorna ["image"] para
        que o engine avalie o input antes de chamar execute().
        Se image já presente: retorna [] -- prosseguir para execute().

        Nota: lazy=True em inputs OPCIONAIS. Se image estiver conectada via link,
        o engine avalia primeiro, passa o tensor e retorna []. Se nao conectada,
        o tensor nunca chega e o node retorna caption vazio sem carregar LLM.
        """
        # Se image foi avaliada e passou como tensor: prosseguir para execute
        if image is not None:
            return []
        # Image nao avaliada ainda: pedir ao engine para avaliá-la
        # NOTA: se image nao estiver conectada, engine retorna None no execute
        return ["image"]

    @classmethod
    def execute(
        cls,
        model: str,
        processing_mode: str,
        caption_style: str,
        system_prompt: str,
        max_new_tokens: int,
        temperature: float,
        top_p: float,
        top_k: int,
        memory_management: str,
        post_process: bool,
        image=None,
        extra_options=None,
    ) -> io.NodeOutput:
        """Executa inferencia JoyCaption GGUF com LOCKED/UNLOCKED protocol.

        Stateless V3: sem self, sem __init__.
        Cache via get_or_load_model() em _jc_engine._MLV_MODEL_CACHE.
        """
        try:
            # Guard null-image (Devil R4 / lazy eval fallback)
            if image is None:
                return io.NodeOutput("", "")

            # Resolver nome do modelo GGUF
            model_name = GGUF_MODELS[model]["name"]

            # Carregar ou recuperar do cache (stateless -- cache no modulo _jc_engine)
            predictor = get_or_load_model(model_name, processing_mode)

            # Montar prompt com LOCKED rules primeiro
            opts_list = extra_options[0] if extra_options else []
            char_name = extra_options[1] if extra_options else ""
            prompt_text = _build_mlv_prompt(opts_list, char_name, caption_style)

            # Inferencia
            with torch.inference_mode():
                # Converter IMAGE (BHWC float32 [0,1]) para PIL
                pil_image = ToPILImage()(image[0].permute(2, 0, 1))
                response = predictor.generate(
                    image=pil_image,
                    system=system_prompt.strip(),
                    prompt=prompt_text,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                )

            # Post-processing (7 camadas de limpeza)
            if post_process:
                response = _clean_caption(response)

            # Gerenciamento de memoria
            if memory_management == "Clear After Run":
                evict_model(model_name, processing_mode)

            return io.NodeOutput(
                response,
                prompt_text,
                ui=comfy_ui.PreviewText(response),
            )

        except Exception as e:
            # Garantir limpeza mesmo em erro
            if memory_management == "Clear After Run":
                try:
                    model_name = GGUF_MODELS[model]["name"]
                    evict_model(model_name, processing_mode)
                except Exception:
                    pass
            err_msg = f"[CAPTION_ERROR] {str(e)}"
            return io.NodeOutput(
                err_msg,
                "",
                ui=comfy_ui.PreviewText(err_msg),
            )
