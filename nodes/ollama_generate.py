# ComfyUI/custom_nodes/MLV_Nodes_V3/nodes/ollama_generate.py
# MLV_OllamaGenerate — Node proprietário Meliva para inferência Ollama
# Feature parity com OllamaGenerateV2 (comfyui-ollama) + bug fixes
# Independente de qualquer dependência de terceiros (usa ollama SDK direto)
# API: Node V3 (io.ComfyNode + define_schema)
# Licença: Proprietário — Meliva Online © 2026

import base64
import numpy as np
from io import BytesIO
from PIL import Image
from pprint import pprint
from ollama import Client
from comfy_api.latest import io

# Module-level context storage for keep_context feature (V3 nodes are stateless)
_SAVED_CONTEXT: list[int] | None = None


class MLV_OllamaGenerate(io.ComfyNode):
    """Text generation with Ollama. Self-contained node with embedded connectivity.
    Supports vision tasks, multi-turn context, thinking mode, and JSON output.
    Drop-in replacement for OllamaGenerateV2 with defensive error handling."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MLV_OllamaGenerate",
            display_name="Ollama Generate (MLV)",
            category="MLV/llm",
            description=(
                "Text generation with Ollama. Self-contained: URL, model, and all "
                "inference parameters are direct inputs. Supports vision (images), "
                "multi-turn context, thinking mode, and JSON structured output. "
                "Defensive error handling for empty prompts and missing API fields."
            ),
            inputs=[
                # --- Connection ---
                io.String.Input(
                    "url",
                    display_name="Server URL",
                    default="http://127.0.0.1:11434",
                    multiline=False,
                    tooltip="URL of the Ollama server.",
                ),
                io.String.Input(
                    "model",
                    display_name="Model",
                    default="qwen2.5:3b",
                    multiline=False,
                    tooltip="Ollama model name for inference.",
                ),
                io.Int.Input(
                    "keep_alive",
                    display_name="Keep Alive (min)",
                    default=5,
                    min=-1,
                    max=120,
                    step=1,
                    tooltip="Minutes to keep model loaded. -1=forever, 0=unload immediately.",
                ),
                # --- Prompts ---
                io.String.Input(
                    "system",
                    display_name="System Prompt",
                    default="You are an AI assistant.",
                    multiline=True,
                    tooltip="System prompt — sets role and behavior of the model.",
                ),
                io.String.Input(
                    "prompt",
                    display_name="Prompt",
                    default="",
                    multiline=True,
                    tooltip="User prompt — question or task for the model.",
                ),
                # --- Options ---
                io.Boolean.Input(
                    "think",
                    display_name="Think",
                    default=False,
                    tooltip="Enable thinking/reasoning before answering (model must support it).",
                ),
                io.Boolean.Input(
                    "keep_context",
                    display_name="Keep Context",
                    default=False,
                    tooltip="Persist conversation context between executions.",
                ),
                io.Combo.Input(
                    "format",
                    options=["text", "json"],
                    display_name="Format",
                    default="text",
                    tooltip="Output format: plain text or structured JSON.",
                ),
                io.Boolean.Input(
                    "debug",
                    display_name="Debug Print",
                    default=False,
                    tooltip="Print request/response to console for debugging.",
                ),
                # --- Optional inputs ---
                io.Image.Input(
                    "images",
                    display_name="Images",
                    optional=True,
                    tooltip="Images for vision tasks. Model must support vision.",
                ),
                io.String.Input(
                    "context",
                    display_name="Context",
                    default="",
                    multiline=False,
                    optional=True,
                    tooltip="Previous context (comma-separated ints) for multi-turn conversations.",
                ),
                # --- Inference parameters (inline, no separate Options node needed) ---
                io.Float.Input(
                    "temperature",
                    display_name="Temperature",
                    default=0.7,
                    min=0.0,
                    max=2.0,
                    step=0.05,
                    optional=True,
                    tooltip="Sampling temperature. Higher = more creative, lower = more deterministic.",
                ),
                io.Int.Input(
                    "num_ctx",
                    display_name="Context Window",
                    default=2048,
                    min=256,
                    max=131072,
                    step=256,
                    optional=True,
                    tooltip="Context window size in tokens.",
                ),
                io.Int.Input(
                    "seed",
                    display_name="Seed",
                    default=-1,
                    min=-1,
                    max=2147483647,
                    step=1,
                    optional=True,
                    tooltip="Random seed for reproducibility. -1 = random.",
                ),
            ],
            outputs=[
                io.String.Output("result", display_name="Result"),
                io.String.Output("thinking", display_name="Thinking"),
                io.String.Output("context_out", display_name="Context"),
            ],
        )

    @classmethod
    def execute(cls, url, model, keep_alive, system, prompt, think, keep_context,
                format, debug, images=None, context=None, temperature=None,
                num_ctx=None, seed=None) -> io.NodeOutput:
        global _SAVED_CONTEXT

        # --- Build client ---
        client = Client(host=url)

        # --- Format handling ---
        api_format = '' if format == "text" else format

        # --- Context parsing (string → list[int]) ---
        parsed_context = None
        if context is not None and isinstance(context, str) and context.strip():
            try:
                parsed_context = [int(x.strip()) for x in context.split(',') if x.strip()]
            except ValueError:
                parsed_context = None

        if keep_context and parsed_context is None:
            parsed_context = _SAVED_CONTEXT

        # --- Keep alive ---
        request_keep_alive = f"{keep_alive}m"

        # --- Options ---
        request_options = {}
        if temperature is not None:
            request_options["temperature"] = temperature
        if num_ctx is not None:
            request_options["num_ctx"] = num_ctx
        if seed is not None and seed >= 0:
            request_options["seed"] = seed
        if not request_options:
            request_options = None

        # --- Image encoding (BHWC float32 [0,1] → base64 PNG) ---
        images_b64 = None
        if images is not None:
            images_b64 = []
            for batch_idx in range(images.shape[0]):
                img_np = (255.0 * images[batch_idx].cpu().numpy()).clip(0, 255).astype(np.uint8)
                img = Image.fromarray(img_np)
                buf = BytesIO()
                img.save(buf, format="PNG")
                images_b64.append(base64.b64encode(buf.getvalue()).decode('utf-8'))

        # --- Debug print request ---
        if debug:
            print(f"\n--- MLV Ollama Generate request ---\n"
                  f"url: {url}\n"
                  f"model: {model}\n"
                  f"system: {system[:100]}{'...' if len(system) > 100 else ''}\n"
                  f"prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}\n"
                  f"images: {0 if images_b64 is None else len(images_b64)}\n"
                  f"context: {'yes' if parsed_context else 'no'}\n"
                  f"think: {think}\n"
                  f"options: {request_options}\n"
                  f"keep_alive: {request_keep_alive}\n"
                  f"format: {api_format or 'text'}\n"
                  f"-----------------------------------")

        # --- Call Ollama API ---
        response = client.generate(
            model=model,
            system=system,
            prompt=prompt,
            images=images_b64,
            context=parsed_context,
            think=think,
            options=request_options,
            keep_alive=request_keep_alive,
            format=api_format,
        )

        # --- Debug print response ---
        if debug:
            print("\n--- MLV Ollama Generate response ---")
            pprint(dict(response))
            print("-----------------------------------")

        # --- Extract outputs with DEFENSIVE fallbacks ---
        result_text = response.get('response', '')
        thinking_text = response.get('thinking', '') if think else ''
        context_list = response.get('context', [])

        # --- Save context for multi-turn ---
        if keep_context and context_list:
            _SAVED_CONTEXT = context_list
            if debug:
                print("Context saved to module memory.")

        # --- Serialize context back to string (portable) ---
        context_str = ','.join(str(x) for x in context_list) if context_list else ''

        return io.NodeOutput(result_text, thinking_text, context_str)
