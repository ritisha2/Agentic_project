# AI-Connex Offline LLM & Model Storage Registry

This directory serves as the local asset repository for offline LLM models, local GGUF/ONNX weights, and offline inference runtimes.

## Supported Offline Model Stack
1. **Qwen2.5-Coder-32B-Instruct / 3B-Instruct**: Local code generation & SQL schema compilation.
2. **Phi-4-mini**: Sensor telemetry reasoning & time-series physical interpretation.
3. **ONNX Runtime Models**: Compiled ML Studio pipeline models (`.onnx`).

## Git Governance
Model weights and large binary files (`.bin`, `.gguf`, `.onnx`, `.safetensors`, `.pt`) stored in `models/` are ignored in `.gitignore` to maintain source repository speed.
