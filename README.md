# Reel Studio

> Facebook Reels automation with templating & human-in-the-loop workflow

Custom version of MoneyPrinterTurbo optimized for Facebook Reels (16:9), featuring:
- **Templating system** – define your script & prompt styles
- **Human-in-the-loop visuals** – AI generates prompts, you generate images, tool assembles video
- **Local-first** – 9router LLM, Whisper, moviepy, no paid APIs required
- **Web UI + CLI** – full control across interfaces
- **Cost-free** – zero ongoing costs (optional Pexels/GoogleFlow keys)

---

## Features

✅ **Script Templating** – Custom script structures (viral hook, educational, Zenn‑style)  
✅ **Prompt Templating** – Visual prompt styles (realistic, hand‑drawn, cinematic)  
✅ **Human‑in‑the‑Loop** – AI prompts → you generate images → tool assembles final video  
✅ **Multi‑Source Visuals** – AI‑generated images + stock footage (Pexels)  
✅ **Local LLM** – 9router all‑in‑one model (no API costs)  
✅ **Edge TTS** – Free text‑to‑speech with 4 Vietnamese voices  
✅ **Whisper Subtitle** – Local subtitle generation  
✅ **Web UI** – Streamlit interface with upload & preview  
✅ **CLI** – Command‑line for automation & scripting  
✅ **Resumable Workflow** – Stop at any stage, upload images, resume  
✅ **16:9 Landscape** – Optimized for Facebook Reels  

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/[YOUR_USERNAME]/reel-studio.git
cd reel-studio
uv sync --frozen
# or
pip install -r requirements.txt
```

### 2. Configure

Copy the example config:

```bash
cp config.example.toml config.toml
```

Edit `config.toml`:
```toml
[llm]
provider = "9router"
api_base = "http://host.docker.internal:20128/v1"
model = "all-in-one"

[tts]
provider = "edge"

[subtitle]
provider = "whisper"

[image]
provider = "none"  # prompts only – you generate images manually

[stock]
pexels_api_key = ""  # optional

[facebook]
enabled = false
```

### 3. Web UI

```bash
uv run streamlit run webui/Main.py
```

Open `http://localhost:8501` in your browser.

### 4. CLI

Generate a script & prompts:

```bash
uv run python cli.py --topic "Why successful people wake up at 5 AM" --stop-at visuals
```

You'll get a task folder with `prompts.txt`. Generate images, place them in `task_xxx/images/`, then resume:

```bash
uv run python cli.py --task-id xxx --resume
```

---

## Workflow

```
1. Input topic (or custom script)
2. AI generates script (using your template)
3. AI generates visual prompts (using your template)
4. ⏸️  YOU generate images (GoogleFlow, Midjourney, etc.)
5. Upload images (Web UI) or place in folder (CLI)
6. AI generates audio (Edge TTS)
7. AI generates subtitles (Whisper)
8. Tool assembles video (moviepy + ffmpeg)
9. ✅ Final 16:9 video ready
```

---

## Templating

### Script Templates

Place your templates in `templates/scripts/`.

Example `templates/scripts/viral_hook.md`:
```markdown
# Viral Hook Template

## Hook (0–3s)
{question}

## Problem (3–10s)
Most people think {common_misconception}, but actually {truth}.

## Twist (10–20s)
Here's what you're missing: {insight}.

## Solution (20–30s)
{actionable_tip}

## CTA (30–35s)
{call_to_action}
```

Use in CLI:
```bash
--script-template viral_hook
```

### Prompt Templates

Place your templates in `templates/prompts/`.

Example `templates/prompts/cinematic.txt`:
```
Cinematic, 16:9, realistic photo, dramatic lighting, {scene_description}, shallow depth of field, color grading warm
```

Use in CLI:
```bash
--prompt-template cinematic
```

### Style Configs

Create `styles/` YAML files to bundle templates & settings.

Example `styles/zenn.yaml`:
```yaml
script_template: "zenn_style"
prompt_template: "hand_drawn"
aspect: "16:9"
visual_source: "ai"
```

Use in CLI:
```bash
--style zenn
```

---

## API Keys (Optional)

| Service | Required? | Cost | How to Get |
|---------|-----------|------|------------|
| **9router** | **Yes** (local) | Free | Already configured in OpenClaw |
| **Edge TTS** | No | Free | Built‑in |
| **Whisper** | No | Free | Local model |
| **Pexels** | Optional | Free tier | [Pexels API](https://www.pexels.com/api/) |
| **Google AI Studio** | Optional | Free credits | [Google AI Studio](https://makersuite.google.com/app/apikey) |
| **Facebook Graph** | Optional | Free | [Facebook Developers](https://developers.facebook.com/) |

---

## Project Structure

```
reel-studio/
├── app/
│   ├── config/           # Configuration
│   ├── controllers/      # FastAPI endpoints
│   ├── models/           # Data schemas
│   ├── services/         # Core logic (LLM, TTS, video, etc.)
│   └── utils/            # Utilities
├── webui/                # Streamlit Web UI
├── templates/            # Script & prompt templates
├── styles/               # Style configs (YAML)
├── resource/             # Fonts, music, static assets
├── cli.py               # Command‑line interface
├── main.py              # FastAPI server
├── config.example.toml  # Example configuration
└── README.md
```

---

## License

MIT – based on MoneyPrinterTurbo (MIT license).

---

## Credits

- **MoneyPrinterTurbo** – original codebase & architecture
- **9router** – local LLM provider
- **Edge TTS** – free text‑to‑speech
- **OpenAI Whisper** – subtitle generation
- **MoviePy** – video editing
- **Streamlit** – Web UI framework
