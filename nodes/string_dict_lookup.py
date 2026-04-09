# MLV_Nodes_V3/nodes/string_dict_lookup.py
# Node V3 — Lookup de string por tuplas key=value
# Licença: Proprietário — Meliva Online © 2026

from comfy_api.latest import io


class MLV_StringDictLookup(io.ComfyNode):
    """Lookup de string por lista de tuplas key=value.

    Widget 'pairs': multiline com formato "key=value" por linha.
    Input 'key': string de busca.
    Output 'value': valor correspondente ou default se não encontrado.
    Output 'found': BOOLEAN indicando se a chave foi encontrada.
    """

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MLV_StringDictLookup",
            display_name="String Dict Lookup",
            category="MLV/text",
            description="Busca uma string em lista de tuplas key=value. Retorna o valor correspondente ou default.",
            inputs=[
                io.String.Input(
                    "key",
                    display_name="Key",
                    tooltip="String de busca (comparação exata, case-sensitive)",
                ),
                io.String.Input(
                    "pairs",
                    display_name="Pairs (key=value)",
                    multiline=True,
                    default="generic_place=\npharmacy_inside=inside a pharmacy rdstyadrg store\npharmacy_outside=outside a pharmacy rdstyadrg store",
                    tooltip="Uma tupla key=value por linha. Separador: primeiro '=' da linha.",
                ),
                io.String.Input(
                    "default_value",
                    display_name="Default",
                    default="",
                    tooltip="Valor retornado se a key não for encontrada na lista.",
                ),
            ],
            outputs=[
                io.String.Output("value", display_name="Value"),
                io.Boolean.Output("found", display_name="Found"),
            ],
        )

    @classmethod
    def execute(cls, key: str, pairs: str, default_value: str) -> io.NodeOutput:
        lookup = {}
        for line in pairs.strip().split("\n"):
            line = line.strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            lookup[k.strip()] = v.strip()

        if key.strip() in lookup:
            return io.NodeOutput(lookup[key.strip()], True)
        return io.NodeOutput(default_value, False)
