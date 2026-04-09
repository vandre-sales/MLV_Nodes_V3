# MLV_Nodes_V3/nodes/lora_stack.py
# Node proprietário Meliva — LoRA Stack V3 com bypass condicional
# Pack: ComfyUI/custom_nodes/MLV_Nodes_V3
# API: ComfyUI Node API V3 (io.ComfyNode + define_schema + ComfyExtension)
# Licença: Proprietário — Meliva Online © 2026

import folder_paths
import comfy.sd
import comfy.utils
from comfy_api.latest import io

MAX_LORAS = 8
LORA_LIST = sorted(folder_paths.get_filename_list("loras"))
LORA_OPTIONS = ["None"] + LORA_LIST


class MLV_LoraStack_V3(io.ComfyNode):
    """Aplica N LoRAs em cadeia com bypass global e por slot.

    Recebe MODEL + CLIP, aplica LoRAs selecionadas internamente
    via comfy.sd.load_lora_for_models() e emite MODEL + CLIP patched.
    Self-contained — zero dependências de packs externos.
    """

    @classmethod
    def define_schema(cls):
        inputs = [
            io.Model.Input("model", tooltip="MODEL de qualquer loader (Flux, SDXL, etc.)"),
            io.Clip.Input("clip", tooltip="CLIP do DualCLIPLoader ou equivalente"),
            io.Boolean.Input(
                "enabled",
                default=True,
                tooltip="Ativa o processamento de LoRAs. Desligar retorna MODEL+CLIP inalterados",
            ),
            io.Int.Input(
                "num_loras",
                default=1,
                min=1,
                max=MAX_LORAS,
                tooltip="Quantidade de slots de LoRA a iterar (1–20)",
            ),
        ]

        # Gerar 20 triplas opcionais: name, strength, bypass
        for i in range(1, MAX_LORAS + 1):
            inputs.extend(
                [
                    io.Combo.Input(
                        f"lora_{i}_name",
                        options=LORA_OPTIONS,
                        default="None",
                        optional=True,
                        tooltip=f"LoRA do slot {i} — selecionar arquivo .safetensors",
                    ),
                    io.Float.Input(
                        f"lora_{i}_strength",
                        default=0.85,
                        min=-10.0,
                        max=10.0,
                        step=0.01,
                        optional=True,
                        tooltip=f"Strength do slot {i} (aplicado em model e clip igualmente)",
                    ),
                    io.Boolean.Input(
                        f"lora_{i}_enabled",
                        default=True,
                        optional=True,
                        tooltip=f"Ativa esta LoRA. Desligar pula este slot sem afetar demais",
                    ),
                ]
            )

        return io.Schema(
            node_id="MLV_LoraStack_V3",
            display_name="MLV LoRA Stack",
            category="\U0001f9ecMLV/\U0001f3a8LoRA",
            description="Aplica N LoRAs em cadeia com bypass global e por slot. Self-contained V3.",
            inputs=inputs,
            outputs=[
                io.Model.Output(display_name="model"),
                io.Clip.Output(display_name="clip"),
            ],
        )

    @classmethod
    def execute(cls, model, clip, enabled, num_loras, **kwargs):
        # Global desligado — retorna MODEL+CLIP inalterados
        if not enabled:
            return io.NodeOutput(model, clip)

        for i in range(1, num_loras + 1):
            lora_name = kwargs.get(f"lora_{i}_name", "None")
            strength = kwargs.get(f"lora_{i}_strength", 1.0)
            slot_enabled = kwargs.get(f"lora_{i}_enabled", True)

            # Skip: slot desligado, nome vazio ou "None"
            if not slot_enabled or not lora_name or lora_name == "None":
                continue

            # Guard Q1/D1: LoRA deletada pós-boot → path None → skip
            lora_path = folder_paths.get_full_path("loras", lora_name)
            if lora_path is None:
                continue

            # Carregar pesos e aplicar patches em cadeia
            lora_dict = comfy.utils.load_torch_file(lora_path, safe_load=True)
            model, clip = comfy.sd.load_lora_for_models(
                model, clip, lora_dict, strength, strength
            )

        return io.NodeOutput(model, clip)
