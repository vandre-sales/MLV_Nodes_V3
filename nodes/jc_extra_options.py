# IS_PROTO_COMMAND: FALSE
# RESTRICTION: AGENT ONLY
# CHMOD_MODE: WRITABLE
# FILE: ComfyUI/custom_nodes/MLV_Nodes_V3/nodes/jc_extra_options.py
# DESCRIPTION: Node V3.2 MLV_JCExtraOptions - Nomenclatura universal include_*.
#              Logica dual: toggle ON=description_on, OFF=description_off.
#              Breaking change: output list[dict] com description_on/off.
# MODULE: CAPTIONING
# DOC_TYPE: SOURCE
# ROLE: JoyCaption Extra Options V3.2 Node
# STATUS: ACTIVE
# BINDING_SCOPE: LOCAL
# TAGS: [JOYCAPTION, LOCKED_UNLOCKED, MLV, V3, CAPTIONING, UAIGF]
# COMPLEXITY: MEDIUM
# OP_TYPE: ATOMIC
# RISK: SAFE
# SCHEMA: UAIGF V4
# LIFE_CYCLE: PERSISTENT
# DATE: 2026-04-21T21:15:00-03:00

# MLV_Nodes_V3/nodes/jc_extra_options.py
# Node V3.2: MLV_JCExtraOptions
# Protocolo LOCKED/UNLOCKED (06-dataset-captioning.md)
# Output type: JOYCAPTION_EXTRA_OPTIONS (compativel com MLV_JCCaptionGGUF)
# V3.2: Nomenclatura universal include_* + logica dual (Skip/Describe)
# Regra canonica: toggle TRUE=include, FALSE=exclude
# Licenca: Proprietario -- Meliva Online (c) 2026

from comfy_api.latest import io

# Tipo custom JOYCAPTION_EXTRA_OPTIONS -- compativel com MLV_JCCaptionGGUF
_JCOpts = io.Custom("JOYCAPTION_EXTRA_OPTIONS")

# Opcoes LOCKED/UNLOCKED -- V3.2 nomenclatura universal
# Toggle TRUE = include = instrucao coletada (description_on)
# Toggle FALSE = exclude = instrucao coletada (description_off com imperativo Skip)
MLV_EXTRA_OPTIONS = {
    # === LOCKED (default FALSE) ===
    "include_identity_attributes": {
        "name": "Include: Identity Attributes",
        "description_on": "Describe visible physical traits: ethnicity indicators, age range, hair, skin tone, facial features, body structure.",
        "description_off": "Skip all physical appearance of the person including ethnicity, skin tone, age, hair (color/style/length), makeup, facial structure, body build, and any other appearance trait that could identify the person.",
        "default": False,
        "category": "LOCKED",
    },
    "include_permanent_accessories": {
        "name": "Include: Permanent Accessories",
        "description_on": "Describe all accessories visible: glasses, jewelry, bags, worn or carried objects.",
        "description_off": "Skip all accessories and objects including glasses, jewelry, bags, hats, carried or worn items.",
        "default": False,
        "category": "LOCKED",
    },
    "include_text_in_image": {
        "name": "Include: Text in Image",
        "description_on": "Describe visible text, logos and written content accurately.",
        "description_off": "Skip any visible text, logos or written content in the image.",
        "default": False,
        "category": "LOCKED",
    },
    "include_mood_feeling": {
        "name": "Include: Mood/Feeling",
        "description_on": "Describe mood, emotional atmosphere and feeling conveyed.",
        "description_off": "Skip mood, atmosphere and emotional interpretation.",
        "default": False,
        "category": "LOCKED",
    },
    # === UNLOCKED (default TRUE) ===
    "include_facial_expression": {
        "name": "Include: Facial Expression",
        "description_on": "Describe facial expression and emotion.",
        "description_off": "Skip facial expression and emotional state.",
        "default": True,
        "category": "UNLOCKED",
    },
    "include_pose_action": {
        "name": "Include: Pose & Action",
        "description_on": "Describe pose, body language and action.",
        "description_off": "Skip pose, body language and actions.",
        "default": True,
        "category": "UNLOCKED",
    },
    "include_composition": {
        "name": "Include: Composition & Framing",
        "description_on": "Specify camera framing and composition.",
        "description_off": "Skip composition and framing details.",
        "default": True,
        "category": "UNLOCKED",
    },
    "include_lighting": {
        "name": "Include: Lighting",
        "description_on": "Describe lighting type, quality and direction.",
        "description_off": "Skip lighting details.",
        "default": True,
        "category": "UNLOCKED",
    },
    "include_scenery": {
        "name": "Include: Scenery & Environment",
        "description_on": "Describe background scenery and environment.",
        "description_off": "Skip background and environment.",
        "default": True,
        "category": "UNLOCKED",
    },
    "include_clothing_detail": {
        "name": "Include: Clothing & Temp Accessories",
        "description_on": "Describe all clothing layers and temporary accessories in detail.",
        "description_off": "Skip clothing and temporary accessories.",
        "default": True,
        "category": "UNLOCKED",
    },
    # === STYLE (default TRUE) ===
    "include_natural_prose": {
        "name": "Include: Natural Prose",
        "description_on": "Write natural English prose with complete sentences.",
        "description_off": "Write as comma-separated tags.",
        "default": True,
        "category": "STYLE",
    },
    "include_direct_caption_only": {
        "name": "Include: Direct Caption Only",
        "description_on": "Output caption only. Skip assistant markers, meta-text and brackets.",
        "description_off": "Allow conversational text and meta-phrases.",
        "default": True,
        "category": "STYLE",
    },
    "include_flux_structure": {
        "name": "Include: Flux Structure",
        "description_on": "Order: subject, expression, clothing, pose, scenery, lighting.",
        "description_off": "Use free-form order.",
        "default": True,
        "category": "STYLE",
    },
    # === OPTIONAL (default FALSE) ===
    "include_camera_angle": {
        "name": "Include: Camera Angle",
        "description_on": "Include camera angle and vantage point.",
        "description_off": "Skip camera angle details.",
        "default": False,
        "category": "OPTIONAL",
    },
    "include_depth_of_field": {
        "name": "Include: Depth of Field",
        "description_on": "Specify depth of field and background blur.",
        "description_off": "Skip depth of field details.",
        "default": False,
        "category": "OPTIONAL",
    },
}


class MLV_JCExtraOptions(io.ComfyNode):
    """MLV JC Extra Options -- LOCKED/UNLOCKED options for LoRA training captions (V3.2).

    V3.2 nomenclatura universal include_* + logica dual description_on/off.
    Regra canonica: toggle TRUE=include=description_on, FALSE=exclude=description_off.

    Breaking change vs V3.0: output list[str] -> list[dict] com category.
    Apenas MLV_JCCaptionGGUF consome. V1 nodes nao afetados.
    """

    @classmethod
    def define_schema(cls):
        inputs = []

        # 15 toggles LOCKED/UNLOCKED/STYLE/OPTIONAL
        for key, value in MLV_EXTRA_OPTIONS.items():
            inputs.append(
                io.Boolean.Input(
                    key,
                    default=value["default"],
                    tooltip=value.get("description_on", ""),
                    display_name=value["name"],
                )
            )

        # Pronoun: Combo dropdown (fix UX vs V1 STRING force_input)
        inputs.append(
            io.Combo.Input(
                "pronoun",
                options=["Person (neutral)", "She/Her", "He/Him", "They/Them"],
                default="Person (neutral)",
                tooltip="Pronoun usado para referir ao sujeito nas captions.",
            )
        )

        # Character name: trigger word + class word
        inputs.append(
            io.String.Input(
                "character_name",
                default="",
                multiline=True,
                tooltip="Trigger word + class word (ex: rdpsnaiol woman)",
            )
        )

        return io.Schema(
            node_id="MLV_JCExtraOptions",
            display_name="MLV JC Extra Options",
            category="\U0001f9ecMLV/\U0001f4ddCaptioning",
            description=(
                "Opcoes LOCKED/UNLOCKED para captions de LoRA training. "
                "Protocolo 06-dataset-captioning.md. "
                "V3.2: true=include, false=exclude (logica dual)."
            ),
            inputs=inputs,
            outputs=[
                _JCOpts.Output(display_name="extra_options"),
            ],
        )

    @classmethod
    def execute(cls, character_name: str, pronoun: str, **kwargs) -> io.NodeOutput:
        """Converte toggles + pronoun + character_name em lista de dicts com logica dual.

        V3.2: Todos os 15 campos sempre geram instrucao (description_on OU description_off).
        Toggle TRUE -> description_on (descritivo)
        Toggle FALSE -> description_off (imperativo Skip)

        Breaking change: output list[str] -> list[dict] {"text": str, "category": str}.
        """
        ret_list = []

        # Coletar instrucoes com logica dual (R1: guard de tipo)
        for key, value in MLV_EXTRA_OPTIONS.items():
            # R1: Guard de tipo -- fail-fast se dict malformado
            if not isinstance(value, dict) or "description_on" not in value or "description_off" not in value:
                raise ValueError(f"Malformed MLV_EXTRA_OPTIONS entry: {key}")

            toggle_state = kwargs.get(key, value["default"])
            instruction = value["description_on"] if toggle_state else value["description_off"]

            ret_list.append({
                "text": instruction,
                "category": value["category"],
            })

        # Mapear pronoun para instrucao textual
        pronoun_map = {
            "She/Her": "Refer to the subject using she/her pronouns.",
            "He/Him": "Refer to the subject using he/him pronouns.",
            "They/Them": "Refer to the subject using they/them pronouns.",
            "Person (neutral)": "Refer to the subject as 'the person' without gendered pronouns.",
        }

        # Match exato ou parcial case-insensitive (fuzzy)
        pronoun_clean = pronoun.strip() if isinstance(pronoun, str) else "Person (neutral)"
        matched = pronoun_map.get(pronoun_clean)
        if not matched:
            pronoun_lower = pronoun_clean.lower()
            for key, val in pronoun_map.items():
                if key.lower() in pronoun_lower or pronoun_lower in key.lower():
                    matched = val
                    break
            if not matched:
                matched = pronoun_map["Person (neutral)"]  # fallback seguro

        ret_list.append({
            "text": matched,
            "category": "STYLE",
        })

        # Formato compativel com JOYCAPTION_EXTRA_OPTIONS: [lista_dicts, character_name]
        return io.NodeOutput([ret_list, character_name])
