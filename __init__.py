# MLV_Nodes_V3/__init__.py
# Entrypoint ComfyUI V3 — registra nodes do pack Meliva
# API: ComfyExtension + comfy_entrypoint() (async obrigatorio)
# Licenca: Proprietario — Meliva Online (c) 2026

from comfy_api.latest import ComfyExtension
from .nodes.lora_stack import MLV_LoraStack_V3
from .nodes.string_dict_lookup import MLV_StringDictLookup
from .nodes.ollama_generate import MLV_OllamaGenerate
from .nodes.boolean_mapper import MLV_BooleanMapper
from .nodes.jc_extra_options import MLV_JCExtraOptions
from .nodes.jc_caption_gguf import MLV_JCCaptionGGUF
from .nodes.json_file_batcher import MLV_JsonFileBatcher

# Frontend JS extension — visibilidade dinamica de slots
WEB_DIRECTORY = "./web/js"


class MLV_Extension(ComfyExtension):
    async def get_node_list(self):
        return [
            MLV_LoraStack_V3,
            MLV_StringDictLookup,
            MLV_OllamaGenerate,
            MLV_BooleanMapper,
            MLV_JCExtraOptions,
            MLV_JCCaptionGGUF,
            MLV_JsonFileBatcher,
        ]


async def comfy_entrypoint():
    return MLV_Extension()
