# PROJECT: ComfyUI Image Tools

## Vision

Custom node para ComfyUI que redimensiona imagens automaticamente para dimensões compatíveis com modelos de geração de imagem, evitando artefatos no KSampler.

## Problem Statement

Quando imagens com dimensões não-padrão são processadas pelo KSampler no ComfyUI, algumas linhas ou colunas acabam corrompidas com pixels incorretos. Isso é especialmente problemático em fluxos img-to-img.

## Solution

Um node que:
1. Recebe uma imagem de entrada
2. Identifica as dimensões padrão mais próximas para o modelo selecionado
3. Aplica crop centralizado para ajustar a imagem ao tamanho correto
4. Retorna a imagem pronta para processamento sem artefatos

## Requirements

### Functional
- **Seleção de modelo via dropdown**: Stable Diffusion, Flux, Z-Image Turbo
- **Crop centralizado**: Sempre cortar a partir do centro da imagem
- **Saída simples**: Apenas a imagem cropada (sem metadados extras)
- **Precisão na escolha de dimensões**: Priorizar dimensões ótimas para cada modelo

### Non-Functional
- Integração nativa com ComfyUI
- Performance adequada para uso em workflows
- Batch processing suportado

## Scope

### In Scope (v1)
- Node com dropdown para seleção de modelo (SD, Flux, Z-Turbo)
- Tabela de dimensões padrão para cada modelo
- Algoritmo de seleção de dimensão mais próxima
- Crop centralizado da imagem
- Retorno da imagem cropada

### Out of Scope (v1)
- Upscale/downscale (apenas crop)
- Modelos customizados (apenas os 3 pré-definidos)
- Detecção de faces/objetos para crop inteligente
- Múltiplas posições de crop (topo, base, etc.)

## Technical Context

### Stack
- Python (ComfyUI custom node)
- torch/PIL para manipulação de imagens
- Estrutura padrão de custom nodes ComfyUI

### Architecture
- Single node com:
  - Input: IMAGE
  - Widget: dropdown para modelo
  - Output: IMAGE

### Standard Dimensions Reference

**Stable Diffusion (múltiplos de 64):**
- 512x512, 512x768, 768x512
- 640x640, 768x768
- 512x896, 896x512

**Flux (múltiplos de 8, aspect ratios específicos):**
- 1024x1024 (1:1)
- 1152x896 (4:3)
- 896x1152 (3:4)
- 1216x832 (3:2)
- 832x1216 (2:3)
- 1344x768 (16:9)
- 768x1344 (9:16)

**Z-Image Turbo:**
- A ser pesquisado/confirmado

## Success Criteria

- [ ] Node aparece corretamente no ComfyUI
- [ ] Dropdown funciona com os 3 modelos
- [ ] Imagens são cropadas para dimensões corretas
- [ ] Nenhum artefato no KSampler após processamento
- [ ] Crop é centralizado corretamente
