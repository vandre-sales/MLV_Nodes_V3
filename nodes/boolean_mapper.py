# MLV_Nodes_V3/nodes/boolean_mapper.py
# Node V3 — Boolean Fan-Out: 1 BOOLEAN → 5 BOOLEANs com toggle por output
# Licença: Proprietário — Meliva Online © 2026

from comfy_api.latest import io


class MLV_BooleanMapper(io.ComfyNode):
    """Fan-out de 1 BOOLEAN para 5 BOOLEANs configuráveis.

    boolean_in (forceInput): BOOLEAN de controle (obrigatório conectar).
    out_N_if_true / out_N_if_false: toggle widget para cada output (N=1..5).
    boolean_out_1..5: saídas BOOLEAN independentes.
    """

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MLV_BooleanMapper",
            display_name="Boolean Mapper",
            category="🧬MLV/⚡Logic",
            description="Fan-out de 1 BOOLEAN para 5 BOOLEANs — cada output configurável com toggle duplo (if_true / if_false).",
            inputs=[
                io.Boolean.Input(
                    "boolean_in",
                    display_name="boolean_in",
                    force_input=True,
                    tooltip="Input BOOLEAN de controle. Deve ser conectado a outro node — não possui widget.",
                ),
                # Output 1
                io.Boolean.Input("out_1_if_true",  display_name="out_1 if TRUE",  default=True),
                io.Boolean.Input("out_1_if_false", display_name="out_1 if FALSE", default=False),
                # Output 2
                io.Boolean.Input("out_2_if_true",  display_name="out_2 if TRUE",  default=False),
                io.Boolean.Input("out_2_if_false", display_name="out_2 if FALSE", default=False),
                # Output 3
                io.Boolean.Input("out_3_if_true",  display_name="out_3 if TRUE",  default=False),
                io.Boolean.Input("out_3_if_false", display_name="out_3 if FALSE", default=False),
                # Output 4
                io.Boolean.Input("out_4_if_true",  display_name="out_4 if TRUE",  default=True),
                io.Boolean.Input("out_4_if_false", display_name="out_4 if FALSE", default=False),
                # Output 5
                io.Boolean.Input("out_5_if_true",  display_name="out_5 if TRUE",  default=True),
                io.Boolean.Input("out_5_if_false", display_name="out_5 if FALSE", default=False),
            ],
            outputs=[
                io.Boolean.Output("boolean_out_1", display_name="boolean_out_1"),
                io.Boolean.Output("boolean_out_2", display_name="boolean_out_2"),
                io.Boolean.Output("boolean_out_3", display_name="boolean_out_3"),
                io.Boolean.Output("boolean_out_4", display_name="boolean_out_4"),
                io.Boolean.Output("boolean_out_5", display_name="boolean_out_5"),
            ],
        )

    @classmethod
    def execute(
        cls,
        boolean_in: bool,
        out_1_if_true: bool, out_1_if_false: bool,
        out_2_if_true: bool, out_2_if_false: bool,
        out_3_if_true: bool, out_3_if_false: bool,
        out_4_if_true: bool, out_4_if_false: bool,
        out_5_if_true: bool, out_5_if_false: bool,
    ) -> io.NodeOutput:
        def pick(if_true: bool, if_false: bool) -> bool:
            return if_true if boolean_in else if_false

        return io.NodeOutput(
            pick(out_1_if_true, out_1_if_false),
            pick(out_2_if_true, out_2_if_false),
            pick(out_3_if_true, out_3_if_false),
            pick(out_4_if_true, out_4_if_false),
            pick(out_5_if_true, out_5_if_false),
        )
