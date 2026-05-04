# MLV_Nodes_V3/nodes/json_file_batcher.py
# Node V3 — Leitura de arquivo JSON com lista de prompts para batch
# Licença: Proprietário — Meliva Online © 2026

import json
import os

from comfy_api.latest import io


class MLV_JsonFileBatcher(io.ComfyNode):
    """Lê um arquivo JSON do disco e emite lista de STRING para batch.

    Suporta dois formatos:
    - Lista de strings: ["p1", "p2", "p3"]
    - Lista de objetos: [{"prompt": "p1"}, {"prompt": "p2"}]

    Para lista de objetos, especificar o nome da chave no input 'key'.
    Em caso de erro (arquivo não encontrado, JSON inválido), retorna [""] sem travar o workflow.
    """

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MLV_JsonFileBatcher",
            display_name="📂 JSON File Batcher",
            category="MLV/batch",
            description="Lê arquivo JSON e emite lista de STRING para batch processing.",
            inputs=[
                io.String.Input(
                    "file_path",
                    display_name="File Path",
                    default="",
                    tooltip="Caminho para o arquivo .json. Absoluto ou relativo à pasta input/ do ComfyUI.",
                ),
                io.String.Input(
                    "key",
                    display_name="Key (opcional)",
                    default="",
                    tooltip="Chave a extrair se JSON for lista de objetos. Vazio = lista de strings puras.",
                ),
            ],
            outputs=[
                io.String.Output(
                    "prompt",
                    display_name="prompt",
                    is_output_list=True,
                    tooltip="Lista de prompts extraídos do arquivo JSON.",
                ),
            ],
        )

    @classmethod
    def execute(cls, file_path: str, key: str = "") -> io.NodeOutput:
        file_path = file_path.strip()
        key = key.strip()

        # Resolve path relative to ComfyUI input directory when not absolute
        if file_path and not os.path.isabs(file_path):
            import folder_paths  # noqa: PLC0415
            file_path = os.path.join(folder_paths.get_input_directory(), file_path)

        try:
            # utf-8-sig strips BOM marker present in files saved on Windows
            with open(file_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"[MLV_JsonFileBatcher] ⚠️ Arquivo não encontrado: {file_path}")
            return io.NodeOutput([""])
        except json.JSONDecodeError as e:
            print(f"[MLV_JsonFileBatcher] ⚠️ JSON inválido: {e}")
            return io.NodeOutput([""])

        if not isinstance(data, list) or len(data) == 0:
            print("[MLV_JsonFileBatcher] ⚠️ JSON não é lista ou está vazio")
            return io.NodeOutput([""])

        # Normalize: list of strings or list of dicts with a key
        if key and all(isinstance(x, dict) for x in data):
            prompts = [str(x.get(key, "")) for x in data]
        elif all(isinstance(x, str) for x in data):
            prompts = data
        else:
            print("[MLV_JsonFileBatcher] ⚠️ Formato não suportado. Use lista de strings ou lista de dicts com 'key'.")
            return io.NodeOutput([""])

        # Filter out blank prompts before returning
        prompts = [p for p in prompts if p.strip()]
        if not prompts:
            print("[MLV_JsonFileBatcher] ⚠️ Nenhum prompt válido encontrado")
            return io.NodeOutput([""])

        print(f"[MLV_JsonFileBatcher] ✅ {len(prompts)} prompts carregados de: {file_path}")
        return io.NodeOutput(prompts)
