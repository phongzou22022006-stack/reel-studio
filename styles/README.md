# Style Configs

Place your custom style YAML files here.

**Format:**
```yaml
name: my_style
script_template: default
prompt_template: default
video_aspect: 16:9
visual_source: ai  # ai, stock, mix
tone: educational  # educational, shock, humor, motivational, storytelling
length: 30  # seconds
```

**Usage:**
```bash
# CLI
python cli.py --topic "..." --style-config my_style

# Or in config.toml
[templating]
style_config = "my_style"
```

**Examples:**
- `default.yaml` - Default educational style
- `zenn.yaml` - Zenn documentary clone
- `viral_hook.yaml` - Viral short-form style
