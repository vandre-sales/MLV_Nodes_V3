# 🧬 MLV_Nodes_V3

> **Pack proprietário Meliva** — Custom nodes ComfyUI para o pipeline DCE (Drogasil Creative Engine) e workflows de automação com LoRA, LLM e lookup de strings.

[![API](https://img.shields.io/badge/API-ComfyUI%20Node%20V3-blue)](https://github.com/comfyanonymous/ComfyUI)
[![Licença](https://img.shields.io/badge/licen%C3%A7a-propriet%C3%A1ria-red)](https://meliva.ai)

---

## 📦 Nodes Incluídos

| Node | Class | Category | Descrição |
|---|---|---|---|
| **MLV LoRA Stack** | `MLV_LoraStack_V3` | `🧬MLV/🎨LoRA` | Aplica N LoRAs em cadeia com bypass global e por slot |
| **Ollama Generate (MLV)** | `MLV_OllamaGenerate` | `MLV/llm` | Inferência Ollama com vision, thinking mode e multi-turn context |
| **String Dict Lookup** | `MLV_StringDictLookup` | `MLV/text` | Lookup de string em lista de pares key=value |

---

## ⚙️ API

Este pack usa a **ComfyUI Node API V3** (`io.ComfyNode` + `define_schema` + `comfy_entrypoint()`). É diferente da API V1 legacy que usa `NODE_CLASS_MAPPINGS`.

```python
# Entrypoint V3 (obrigatório)
from comfy_api.latest import ComfyExtension

class MLV_Extension(ComfyExtension):
    async def get_node_list(self):
        return [MLV_LoraStack_V3, MLV_StringDictLookup, MLV_OllamaGenerate]

async def comfy_entrypoint():
    return MLV_Extension()
```

> ⚠️ **Requer ComfyUI com suporte à Node API V3** (versões recentes). Se o ComfyUI não tiver `comfy_api.latest`, este pack não carrega.

---

## 🔌 Dependências

| Dependência | Obrigatória | Instalação |
|---|---|---|
| `comfy_api.latest` | ✅ | Incluído no ComfyUI |
| `folder_paths`, `comfy.sd`, `comfy.utils` | ✅ | Incluído no ComfyUI |
| `ollama` (Python SDK) | ⚠️ Para `MLV_OllamaGenerate` | `pip install ollama` |
| `pillow` | ⚠️ Para vision em `MLV_OllamaGenerate` | `pip install Pillow` |

> `requirements.txt` está vazio — o `ollama` SDK deve ser instalado separadamente se for usar o node de LLM.

---

## 📥 Instalação

```bash
# Copiar o diretório para custom_nodes do ComfyUI
cp -r MLV_Nodes_V3 ComfyUI/custom_nodes/

# Instalar dependência opcional (se usar MLV_OllamaGenerate)
pip install ollama Pillow

# Reiniciar ComfyUI
sudo systemctl restart comfyui
```

---

## 🧬 Node Reference

---

### 1. `MLV_LoraStack_V3` — MLV LoRA Stack

Aplica até **8 LoRAs em cadeia** sobre MODEL + CLIP. Suporte a bypass global e por slot individual. Self-contained — zero dependências de packs externos.

#### Inputs

| Input | Tipo | Padrão | Obrigatório | Descrição |
|---|---|---|---|---|
| `model` | MODEL | — | ✅ | Saída de qualquer model loader (Flux, SDXL, SD1.5...) |
| `clip` | CLIP | — | ✅ | Saída de DualCLIPLoader ou equivalente |
| `enabled` | BOOLEAN | `True` | ✅ | **Bypass global** — se `False`, retorna MODEL+CLIP inalterados sem carregar nenhuma LoRA |
| `num_loras` | INT (1–8) | `1` | ✅ | Quantidade de slots ativos. Controla a visibilidade dinâmica no frontend |
| `lora_{i}_name` | COMBO | `None` | ⬜ opcional | LoRA do slot i — lista todos os `.safetensors` em `ComfyUI/models/loras/` |
| `lora_{i}_strength` | FLOAT (-10 a 10) | `0.85` | ⬜ opcional | Strength aplicado igualmente no model e no clip |
| `lora_{i}_enabled` | BOOLEAN | `True` | ⬜ opcional | **Bypass por slot** — pula este slot sem afetar os demais |

> `i` vai de `1` até `num_loras` (máximo 8 slots).

#### Outputs

| Output | Tipo | Descrição |
|---|---|---|
| `model` | MODEL | MODEL com todas as LoRAs ativas aplicadas em cadeia |
| `clip` | CLIP | CLIP com todas as LoRAs ativas aplicadas em cadeia |

#### Lógica de Execução

```
Para cada slot i de 1 até num_loras:
  Se enabled=False → retornar MODEL+CLIP sem processar
  Se lora_i_enabled=False → pular este slot
  Se lora_i_name="None" ou vazio → pular este slot
  Se path da LoRA não encontrado (deletada pós-boot) → pular sem erro
  Senão → carregar pesos + aplicar patch em cadeia
```

#### Frontend Dinâmico (`web/js/mlv_lora_stack.js`)

O arquivo JavaScript controla a **visibilidade dinâmica de slots** na UI:
- Slots acima de `num_loras` são ocultados automaticamente
- **Auto-increment:** selecionar uma LoRA no último slot visível incrementa `num_loras` automaticamente
- Compatível com Vue frontend (v1.42+) via `widget.hidden` e LiteGraph legacy via type swap

#### Notas Importantes

> ⚠️ **LoRA list é carregada no boot** — `folder_paths.get_filename_list("loras")` é executado no import. LoRAs adicionadas após o início do ComfyUI não aparecem na lista até um restart.

---

### 2. `MLV_OllamaGenerate` — Ollama Generate (MLV)

Inferência de texto com Ollama. Substituto drop-in para `OllamaGenerateV2` do `comfyui-ollama` com melhorias:
- Parâmetros de inferência inline (sem nó separado de Options)
- Suporte a **vision** (imagens como input)
- Suporte a **thinking mode** (modelos com raciocínio explícito)
- **Multi-turn context** persistido em memória de módulo
- Saída estruturada **JSON**
- Defensive error handling para campos ausentes na resposta

#### Inputs

| Input | Tipo | Padrão | Obrigatório | Descrição |
|---|---|---|---|---|
| `url` | STRING | `http://127.0.0.1:11434` | ✅ | URL do servidor Ollama |
| `model` | STRING | `qwen2.5:3b` | ✅ | Nome do modelo Ollama (ex: `llama3.2`, `qwen2.5:7b`) |
| `keep_alive` | INT (-1 a 120) | `5` | ✅ | Minutos para manter modelo carregado. `-1`=forever, `0`=descarregar imediatamente |
| `system` | STRING | `You are an AI assistant.` | ✅ | System prompt — define papel e comportamento do modelo |
| `prompt` | STRING | `""` | ✅ | Prompt do usuário |
| `think` | BOOLEAN | `False` | ✅ | Ativa thinking/reasoning antes da resposta (modelo deve suportar) |
| `keep_context` | BOOLEAN | `False` | ✅ | Persiste contexto de conversa entre execuções (módulo-level state) |
| `format` | COMBO | `text` | ✅ | `text` ou `json` — saída estruturada JSON |
| `debug` | BOOLEAN | `False` | ✅ | Imprime request/response no console para debugging |
| `images` | IMAGE | — | ⬜ opcional | Imagens para tarefas de visão. Modelo deve suportar multimodal |
| `context` | STRING | `""` | ⬜ opcional | Contexto anterior (ints separados por vírgula) para multi-turn |
| `temperature` | FLOAT (0–2) | `0.7` | ⬜ opcional | Temperatura de sampling |
| `num_ctx` | INT (256–131072) | `2048` | ⬜ opcional | Tamanho da janela de contexto em tokens |
| `seed` | INT (-1 a 2147483647) | `-1` | ⬜ opcional | Seed para reprodutibilidade. `-1` = aleatório |

#### Outputs

| Output | Tipo | Descrição |
|---|---|---|
| `result` | STRING | Texto gerado pelo modelo |
| `thinking` | STRING | Raciocínio interno (apenas se `think=True` e modelo suportar) |
| `context_out` | STRING | Contexto da conversa atual (ints separados por vírgula para reutilizar em multi-turn) |

#### Notas Importantes

> ⚠️ **`keep_context` usa variável global de módulo** — `_SAVED_CONTEXT` persiste durante toda a sessão do ComfyUI. Reset ao reiniciar o ComfyUI ou ao executar com `keep_context=False` + `context=""`.

> 💡 **Vision:** imagens são convertidas de float32 [0,1] BHWC → base64 PNG antes de enviar para a API Ollama. O modelo deve ter suporte a multimodal (ex: `llava`, `qwen2-vl`).

> 💡 **Multi-turn manual:** conectar `context_out` de uma execução ao input `context` da próxima preserva o histórico da conversa sem depender do estado global.

---

### 3. `MLV_StringDictLookup` — String Dict Lookup

Lookup de string em lista de pares `key=value`. Útil para mapear identificadores internos (ex: cenário de produto) para strings de prompt.

#### Inputs

| Input | Tipo | Padrão | Descrição |
|---|---|---|---|
| `key` | STRING | — | String de busca (comparação exata, case-sensitive) |
| `pairs` | STRING (multiline) | (exemplos) | Lista de pares `key=value`, um por linha. Separador: primeiro `=` da linha |
| `default_value` | STRING | `""` | Valor retornado se a key não for encontrada |

#### Outputs

| Output | Tipo | Descrição |
|---|---|---|
| `value` | STRING | Valor correspondente à key, ou `default_value` se não encontrado |
| `found` | BOOLEAN | `True` se key encontrada, `False` caso contrário |

#### Formato do campo `pairs`

```
generic_place=
pharmacy_inside=inside a pharmacy rdstyadrg store
pharmacy_outside=outside a pharmacy rdstyadrg store
```

- Uma entrada por linha
- Separador: **primeiro `=` da linha** (valores podem conter `=`)
- Linhas sem `=` são ignoradas
- Linhas vazias são ignoradas
- Comparação é **exata e case-sensitive**

#### Exemplo de Uso (DCE Pipeline)

```
[ComfyUI Workflow Context] ──→ key: "pharmacy_inside"
[String Dict Lookup]           pairs: (lista de cenários)
     │ value: "inside a pharmacy rdstyadrg store"
     │ found: True
     ▼
[CLIPTextEncode] → [KSampler]
```

---

## 🔄 Workflow Típico — LoRA Stack

```
[CheckpointLoader ou UNetLoader]
     │ model
     ▼
[MLV LoRA Stack]
  enabled: True
  num_loras: 3
  lora_1: mottu-lora-MOTTU_SPORT110I.safetensors (0.85)
  lora_2: rd-lora-Trigger_ilustrasil.safetensors (0.7)
  lora_3: uso-flux1-dit-lora-v1.safetensors (0.5)
     │ model (patched)   │ clip (patched)
     ▼                   ▼
[FluxGuidance]      [CLIPTextEncode]
```

---

## 🔄 Workflow Típico — Ollama + Dict Lookup (DCE)

```
[String Dict Lookup]
  key: cenario_atual
  pairs: (mapeamento cenário → descrição de cena)
     │ value (descrição do cenário)
     ▼
[MLV_OllamaGenerate]
  model: qwen2.5:7b
  system: "You are a prompt enhancer..."
  prompt: (valor do cenário)
  temperature: 0.7
     │ result (prompt enriquecido)
     ▼
[CLIPTextEncode] → [Flux Sampler]
```

---

## 🔧 Compatibilidade

| Requisito | Versão / Notas |
|---|---|
| ComfyUI Node API | **V3 obrigatória** — `comfy_api.latest.io.ComfyNode` + `comfy_entrypoint()` async |
| ComfyUI | Versões recentes (2025+) com suporte a V3 |
| Python | 3.10+ |
| `ollama` SDK | `pip install ollama` (apenas para `MLV_OllamaGenerate`) |
| `Pillow` | `pip install Pillow` (apenas para vision em `MLV_OllamaGenerate`) |
| Ollama server | Em execução em `http://127.0.0.1:11434` (padrão) |

> ⚠️ **V3 vs V1:** Este pack NÃO expõe `NODE_CLASS_MAPPINGS`. Se o ComfyUI não suportar V3, os nodes não aparecem. Verificar: `from comfy_api.latest import io` sem erro.

---

## 📋 Histórico

| Versão | Data | Nodes |
|---|---|---|
| **v0.24.0** | 2026-04-05 | Criação: `MLV_LoraStack_V3` (N slots, bypass global+slot, JS dinâmico) |
| **v0.25.0** | 2026-04-06 | Adição: `MLV_StringDictLookup`, `MLV_OllamaGenerate` |

---

## 📎 Referências Internas

| Artefato | Path |
|---|---|
| Custom fix docs | `PROTO_LOCAL/6_knowledge/aws-p5-sp-h100-custom-fix/nodes-MLV-Nodes-V3/` |
| Ciclo v0.24.0 | `PROTO_LOCAL/1_management/3_done/v0.24.0-MLV-LoraConditional-[BETA].md` |

---

*Pack proprietário — Meliva Online © 2026*
