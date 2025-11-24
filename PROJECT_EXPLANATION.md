# Osiris – AI‑Assisted Command‑Line “OS” Shell

Osiris is a team project that behaves like a smart, OS‑style command shell. It runs on top of your existing operating system (Windows + optional WSL) but aims to feel like its own little OS that can:

- Run normal shell commands.
- Monitor system health.
- Enforce safety rules.
- Interpret natural language (for example, “make a folder called test”) via Command R, a RAG‑style AI model.

This document explains the core pieces, how they fit together, and how a user actually experiences Osiris. Reading time: ~15 minutes.

---

## High‑Level Architecture

The project is organized into four main “team modules” plus shared infrastructure:

- `osiris_team.py` – Main entrypoint and orchestration shell.
- `iris_cli_framework/` – CLI UI: prompt, help, and parsing.
- `shiv_command_execution/` – Command execution (PowerShell/WSL) layer.
- `kshitij_safety_gate/` – Safety filter that blocks dangerous commands.
- `prabal_efficiency_metrics/` – System monitor: CPU, memory, disk, processes.
- `shared/` – Shared config, logging, history, Command R model, and optional RAG index.

Conceptually:

1. User types something at the `osiris>` prompt.
2. Iris parses it into a structured command.
3. If it’s a built‑in like `status` or `team`, Osiris handles it internally.
4. Otherwise:
   - Kshitij’s Safety Gate checks if it’s dangerous.
   - Prabal’s System Monitor checks current system load.
   - Shiv’s Command Executor runs it (PowerShell or WSL).
5. Output is shown back through Iris’s colorful interface.

On top of this, Command R lets the user talk in natural language via `r <text>`, and Osiris figures out the right shell command.

---

## Main Shell: `osiris_team.py`

`OsirisTeamShell` glues all modules together.

- Initialization
  - Loads configuration from `config.yaml` via `shared.OsirisConfig`.
  - Sets up logging (`shared.setup_logging`) and command history (`CommandHistory`).
  - Creates instances of:
    - `CLIFramework` (Iris).
    - `CommandExecutor` (Shiv).
    - `SafetyGate` (Kshitij).
    - `SystemMonitor` (Prabal).
    - `CommandRModel` (Command R).

- Main loop (`run`)
  - Shows a welcome panel plus a one‑line system status: CPU, memory, disk, process count.
  - Iterates over commands produced by `CLIFramework.start()`:
    1. Saves raw command to history.
    2. Routes built‑ins:
       - `exit` / `quit` / `help` handled by Iris.
       - `team`, `status`, `metrics`, `r` handled by the shell.
    3. For normal commands:
       - Run through Safety Gate.
       - Check resource pressure via System Monitor.
       - Execute using Command Executor.
       - Display success/error output.

- Special commands
  - `team` → renders a table of team members and their modules.
  - `status` → shows current CPU/memory/disk usage with “OK/HIGH” markers.
  - `metrics` → more detailed metrics view.
  - `r` → hands the request to Command R (see below).

The shell itself does minimal “heavy lifting”; it’s a coordinator.

---

## CLI & UX: `iris_cli_framework/cli_interface.py`

Iris provides the user‑facing shell.

- Welcome panel
  - Rich panel with Osiris name, version, and basic instructions.
- Prompt handling
  - Uses `rich.prompt.Prompt` to show a colored `osiris>` prompt.
- Parsing
  - Splits user input into:
    - `command` – first word.
    - `args` – the rest.
    - `raw` – original line.
    - `is_builtin` – whether it’s in `['exit','quit','help','team','status','metrics','r']`.
- Built‑ins
  - `help` shows structured help, including:
    - Built‑in commands.
    - Supported Linux‑style commands.
    - Command R usage (`r <text>`).
  - `exit` / `quit` print “Goodbye!” and stop the loop.

Iris does not execute commands itself; it just parses and delegates.

---

## Command Execution: `shiv_command_execution/command_executor.py`

Shiv’s module actually runs external commands.

- Configuration
  - `timeout` (default 300s).
  - `use_wsl` from `config.yaml`:
    - If `True`, Linux commands run via WSL.
- Linux→PowerShell translation
  - For common Linux commands (`ls`, `pwd`, `cat`, `mkdir`, `rm`, etc.), it can:
    - Detect them via `_is_linux_command`.
    - Translate to PowerShell equivalents when not using WSL.
- Execution
  - For Command R suggestions we explicitly force PowerShell (not WSL) for reliability.
  - Captures `stdout`, `stderr`, `exit_code`, timings; logs results.
- History
  - Keeps an in‑memory list of execution results for quick inspection.

The executor is the “hands” of Osiris, doing actual OS work safely.

---

## Safety Gate: `kshitij_safety_gate/`

Kshitij’s Safety Gate guards against dangerous operations.

- Configuration (`config.yaml`)
  - `enabled`, `sandbox_mode`.
  - `dangerous_commands` (e.g., `rm -rf /`, `mkfs`, etc.).
  - `sensitive_paths` (Linux and Windows system dirs).
  - `require_confirmation` for risky verbs (`rm`, `chmod`, `kill`, etc.).
- Evaluation
  - `evaluate_command(raw)` returns `allowed`, `risk_level`, `reason`, `warnings`.
- Integration
  - If blocked, Osiris prints `BLOCKED: <reason>` and does not execute.
  - Warnings show in yellow before execution.

Even AI‑generated commands from Command R are checked before running.

---

## System Monitor: `prabal_efficiency_metrics/system_monitor.py`

Prabal’s System Monitor gives Osiris situational awareness.

- Uses `psutil` to fetch CPU, memory, disk, and process count.
- Thresholds in `config.yaml` (`system_monitoring.thresholds`).
- Functions
  - `get_current_metrics()` – returns a metrics dict.
  - `check_resource_pressure(metrics)` – flags “HIGH” usage and adds warnings.
  - `format_metrics_display(metrics)` – short status line printed on start.

The shell uses this at startup and before/after running commands.

---

## Shared Infrastructure: `shared/`

Shared components provide the project “glue”:

- `utils.py`
  - `OsirisConfig` – loads and queries `config.yaml` with dot‑notation.
  - `setup_logging` – logs to `logs/osiris.log` + console.
  - `CommandHistory` – persists to `~/.osiris_history`.
- `command_r.py`
  - Defines `CommandRModel` and `CommandSuggestion`.
- `rag_index.py`
  - Optional RAG helper using ChromaDB + llama‑index to build a vector index over project docs, so Command R can retrieve relevant context.

---

## Command R – Natural Language “OS Brain”

Command R lets the user talk to Osiris in approximate natural language:

- Usage: `r <text>` at the `osiris>` prompt, e.g.:
  - `r make a folder hello`
  - `r present working directory`
  - `r remove the hello folder`

### How Command R works

1. Pattern layer (fast)
   - Simple patterns for common intents:
     - “make a folder …” → `mkdir <name>`
     - “list/show files” → `ls`
     - “where am i/current directory” → `pwd`
     - “delete/remove folder …” → `rm <name>`
   - Returns `CommandSuggestion` with explanation and confidence.

2. RAG + LLM fallback (optional)
   - If no pattern matches:
     - `rag_index.build_osiris_index()` builds a llama‑index / Chroma index over:
       - `README.md`
       - Each `COMPONENT_EXPLANATION.md`
     - Command R queries this index for context snippets.
     - Sends a prompt to a local Ollama server (`phi3:mini`) that:
       - Restricts suggestions to safe, allowed primitives (e.g., `pwd`, `ls`, `mkdir <name>`, `rm <name>`, `cat <file>`).
       - Returns a single JSON object: `{ "command": "...", "explanation": "..." }`.

3. Execution flow
   - Osiris shows the suggestion, asks for confirmation, then:
     - Runs the Safety Gate checks.
     - Executes via Command Executor (PowerShell for reliability).

This layered design lets Osiris understand fuzzy text and spelling mistakes while staying safe.

---

## Configuration: `config.yaml`

- `shell` – name, version, prompt, history.
- `safety` – Safety Gate rules.
- `system_monitoring` – CPU/memory/disk thresholds.
- `command_execution` – timeout, WSL usage.
- `command_r` – enable/disable and optional model/endpoint overrides.
- `logging` – level and log file.

---

## How a User Experiences Osiris

1. Start Osiris:

   ```powershell
   cd "C:\Users\...\Osiris_TeamProject"
   python osiris_team.py
   ```

2. See:
   - One‑line system status (CPU, MEM, DISK, Processes).
   - A Rich welcome panel.

3. At the prompt:
   - Run normal shell commands: `ls`, `pwd`, `cat file.txt`, etc.
   - Use built‑ins: `team`, `status`, `metrics`, `help`, `exit`.
   - Talk to Command R: `r make a folder test`, `r present working directory`.

Osiris is a collaborative, AI‑assisted shell that tries to feel more like a conversational “OS” than a traditional command line.
