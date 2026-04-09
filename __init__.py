# MLV_Nodes_V3/__init__.py
# Entrypoint ComfyUI V3 — registra nodes do pack Meliva
# API: ComfyExtension + comfy_entrypoint() (async obrigatório)
# Licença: Proprietário — Meliva Online © 2026

from comfy_api.latest import ComfyExtension
from .nodes.lora_stack import MLV_LoraStack_V3
from .nodes.string_dict_lookup import MLV_StringDictLookup
from .nodes.ollama_generate import MLV_OllamaGenerate

# Frontend JS extension — visibilidade dinâmica de slots
WEB_DIRECTORY = "./web/js"


class MLV_Extension(ComfyExtension):
    async def get_node_list(self):
        return [MLV_LoraStack_V3, MLV_StringDictLookup, MLV_OllamaGenerate]


async def comfy_entrypoint():
    return MLV_Extension()
