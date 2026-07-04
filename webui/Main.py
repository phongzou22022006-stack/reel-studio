#!/usr/bin/env python3
"""
Reel Studio Web UI – Streamlit interface
Run with: streamlit run webui/Main.py
"""

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import streamlit as st

# Add parent to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import config as app_config
from app.models.schema import VideoParams
from app.services import task as tm
from app.services import templating, state as sm

# ─── Page config ───
st.set_page_config(
    page_title="Reel Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Session state init ───
if "task_id" not in st.session_state:
    st.session_state.task_id = ""
if "step" not in st.session_state:
    st.session_state.step = "input"
if "script" not in st.session_state:
    st.session_state.script = ""
if "prompts" not in st.session_state:
    st.session_state.prompts = []
if "images_uploaded" not in st.session_state:
    st.session_state.images_uploaded = 0

# ─── Sidebar ───
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/video-editing.png", width=64)
    st.title("Reel Studio")
    st.caption("Facebook Reels automation")
    
    st.divider()
    
    st.subheader("Workflow")
    steps = [
        ("input", "📝 Input & Templates"),
        ("prompts", "🎨 Generate Prompts"),
        ("images", "🖼️ Upload Images"),
        ("generate", "🎬 Generate Video"),
        ("result", "✅ Done"),
    ]
    
    for i, (key, label) in enumerate(steps):
        if st.session_state.step == key:
            st.markdown(f"**→ {label}**")
        elif steps.index((key, label)) < steps.index(
            [(s, l) for s, l in steps if s == st.session_state.step][0]
        ):
            st.markdown(f"~~{label}~~ ✅")
        else:
            st.markdown(label)
    
    st.divider()
    
    with st.expander("⚙️ Settings"):
        api_base = st.text_input(
            "9router API Base",
            value=app_config.llm.api_base,
            help="Local 9router endpoint",
        )
        voice = st.selectbox(
            "Voice",
            options=[
                "vi-VN-HoaiMyNeural",
                "vi-VN-NamMinhNeural",
                "vi-VN-VanMinhNeural",
                "vi-VN-ThuHangNeural",
                "en-US-AriaNeural",
                "en-US-GuyNeural",
            ],
            index=0,
        )
        aspect = st.selectbox(
            "Aspect Ratio",
            options=["16:9", "9:16", "1:1"],
            index=0,
        )
    
    st.divider()
    st.caption("v0.1.0 — Reel Studio")

# ─── Main content ───
# --- STEP 1: INPUT ---
if st.session_state.step == "input":
    st.title("🎬 Reel Studio")
    st.markdown("Generate Facebook Reels with AI script, prompts, and video assembly.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.form("input_form"):
            topic = st.text_input(
                "Video Topic",
                placeholder="e.g., Why successful people wake up at 5 AM",
                help="The main subject of your video",
            )
            
            st.markdown("#### Options")
            col_lang, col_tone = st.columns(2)
            with col_lang:
                language = st.selectbox(
                    "Language",
                    options=["vi", "en"],
                    index=0,
                )
            with col_tone:
                tone = st.selectbox(
                    "Tone",
                    options=["educational", "shock", "humor", "motivational", "storytelling"],
                    index=0,
                )
            
            col_len, col_hook = st.columns(2)
            with col_len:
                length = st.slider("Video Length (s)", 15, 90, 30, 15)
            with col_hook:
                hook_type = st.selectbox(
                    "Hook Type",
                    options=["question", "shock", "story", "number_list"],
                    index=0,
                )
            
            # Custom script or AI-generated
            use_custom_script = st.checkbox("Use custom script instead of AI generation")
            custom_script = ""
            if use_custom_script:
                custom_script = st.text_area(
                    "Paste your script here",
                    height=200,
                    placeholder="Write your video script...",
                )
            
            # Templates
            st.markdown("#### Templates")
            col_s, col_p = st.columns(2)
            with col_s:
                script_templates = templating.engine.list_script_templates()
                script_template_names = [t.name for t in script_templates]
                script_template = st.selectbox(
                    "Script Template",
                    options=script_template_names,
                    index=0,
                )
            with col_p:
                prompt_templates = templating.engine.list_prompt_templates()
                prompt_template_names = [t.name for t in prompt_templates]
                prompt_template = st.selectbox(
                    "Prompt Template",
                    options=prompt_template_names,
                    index=0,
                )
            
            submitted = st.form_submit_button(
                "🚀 Generate Script & Prompts",
                type="primary",
                use_container_width=True,
            )
            
            if submitted:
                if not topic and not custom_script:
                    st.error("Please enter a topic or custom script.")
                else:
                    with st.spinner("Generating script and visual prompts..."):
                        # Build params
                        params = VideoParams(
                            video_subject=topic,
                            video_script=custom_script,
                            language=language,
                            tone=tone,
                            length=length,
                            hook_type=hook_type,
                            script_template=script_template,
                            prompt_template=prompt_template,
                            video_aspect=aspect,
                            stop_at="prompts",
                        )
                        
                        # Create task
                        task_id = str(uuid.uuid4())[:8]
                        result = tm.start(task_id=task_id, params=params, stop_at="prompts")
                        
                        if result:
                            st.session_state.task_id = task_id
                            st.session_state.script = result.get("script", "")
                            st.session_state.prompts = result.get("prompts", [])
                            st.session_state.step = "prompts"
                            st.rerun()
                        else:
                            st.error("Failed to generate. Check 9router connection.")
    
    with col2:
        st.markdown("#### Quick Tips")
        st.info(
            """
            **Best practices:**
            - Keep topics specific, not vague
            - Educational content performs best
            - 30s is the sweet spot for Reels
            - Vietnamese hooks with 'Bạn có biết...' work well
            
            **Workflow:**
            1. Enter topic
            2. AI generates script + prompts
            3. You upload images
            4. Tool renders video
            """
        )
        
        st.markdown("#### Recent Tasks")
        tasks = sm.state.list_tasks(limit=5)
        if tasks:
            for t in tasks:
                st.caption(f"`{t['task_id']}` — {t['status']}")
        else:
            st.caption("No tasks yet")

# --- STEP 2: PROMPTS ---
elif st.session_state.step == "prompts":
    st.title("🎨 Visual Prompts Generated")
    
    task_id = st.session_state.task_id
    
    st.success(f"Task `{task_id}` — Script and prompts ready!")
    
    with st.expander("📝 View Script", expanded=False):
        st.text(st.session_state.script[:2000] + "..." if len(st.session_state.script) > 2000 else st.session_state.script)
    
    st.markdown("### 📋 Prompts for Image Generation")
    st.caption("Copy these prompts to GoogleFlow, Midjourney, or any image generator. Then upload the images in the next step.")
    
    prompts = st.session_state.prompts
    
    if prompts:
        for i, prompt in enumerate(prompts):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text_area(
                    f"Prompt {i+1:02d}",
                    value=prompt,
                    height=80,
                    key=f"prompt_{i}",
                    label_visibility="collapsed",
                )
            with col2:
                st.button(
                    "📋 Copy",
                    key=f"copy_{i}",
                    help="Copy to clipboard (Ctrl+C)",
                    on_click=lambda p=prompt: st.write(f"`{p}`"),
                )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🖼️ Go to Image Upload", type="primary", use_container_width=True):
            st.session_state.step = "images"
            st.rerun()
    with col2:
        if st.button("⬅️ Back to Input", use_container_width=True):
            st.session_state.step = "input"
            st.rerun()

# --- STEP 3: IMAGE UPLOAD ---
elif st.session_state.step == "images":
    st.title("🖼️ Upload Images")
    
    task_id = st.session_state.task_id
    task_dir = Path(app_config.storage.task_dir) / task_id
    images_dir = task_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    st.markdown(f"**Task:** `{task_id}`")
    st.markdown(f"**Image folder:** `{images_dir}`")
    
    # Show prompts for reference
    with st.expander("📋 Show prompts for reference"):
        for i, p in enumerate(st.session_state.prompts, 1):
            st.caption(f"{i:02d}: {p}")
    
    st.markdown("---")
    st.markdown("### Upload your generated images")
    st.caption("Upload in order matching the prompts above (001 = prompt 1, 002 = prompt 2, ...)")
    
    uploaded_files = st.file_uploader(
        "Choose image files",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        help="Upload images in prompt order",
    )
    
    if uploaded_files:
        n_uploaded = len(uploaded_files)
        
        # Save files
        for i, uploaded_file in enumerate(uploaded_files, 1):
            if uploaded_file.size > 10 * 1024 * 1024:  # 10MB max
                st.warning(f"File {uploaded_file.name} is too large (>10MB), skipped.")
                continue
                
            ext = Path(uploaded_file.name).suffix
            save_path = images_dir / f"{i:03d}{ext}"
            
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
        
        st.session_state.images_uploaded = len(list(images_dir.glob("*")))
        
        st.success(f"{len(uploaded_files)} images uploaded!")
    
    # Show existing images
    existing = sorted(images_dir.glob("*"))
    if existing:
        st.markdown(f"**Images in folder ({len(existing)}):**")
        cols = st.columns(min(4, len(existing)))
        for i, img_path in enumerate(existing):
            col = cols[i % len(cols)]
            with col:
                st.image(str(img_path), caption=img_path.name, use_container_width=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("⬅️ Back to Prompts", use_container_width=True):
            st.session_state.step = "prompts"
            st.rerun()
    with col2:
        if st.button("🖼️ Refresh", use_container_width=True):
            st.rerun()
    with col3:
        images_count = len(existing)
        if images_count > 0:
            if st.button(
                f"🎬 Generate Video ({images_count} images)",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.step = "generate"
                st.rerun()
        else:
            st.button(
                "🎬 Generate Video",
                disabled=True,
                use_container_width=True,
            )

# --- STEP 4: GENERATE ---
elif st.session_state.step == "generate":
    st.title("🎬 Generating Video...")
    
    task_id = st.session_state.task_id
    
    progress_bar = st.progress(0, text="Starting generation...")
    
    def update_progress(current, total, msg):
        pct = int(current / total * 100)
        progress_bar.progress(min(pct, 99), text=msg)
    
    # Resume task to generate video
    try:
        update_progress(1, 10, "Loading task data...")
        time.sleep(0.5)
        
        result = tm.resume_task(task_id=task_id)
        
        if result:
            update_progress(10, 10, "✅ Video generated!")
            progress_bar.progress(100, text="Complete!")
            
            st.session_state.result = result
            st.session_state.step = "result"
            st.rerun()
        else:
            st.error("Failed to generate video. Check logs.")
            if st.button("⬅️ Back to Upload"):
                st.session_state.step = "images"
                st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")
        if st.button("⬅️ Back to Upload"):
            st.session_state.step = "images"
            st.rerun()

# --- STEP 5: RESULT ---
elif st.session_state.step == "result":
    st.title("✅ Video Generated!")
    
    result = st.session_state.get("result", {})
    task_id = st.session_state.task_id
    task_dir = Path(app_config.storage.task_dir) / task_id
    
    videos = result.get("videos", [])
    
    if videos:
        for i, video_path in enumerate(videos):
            st.video(str(video_path))
            
            col1, col2 = st.columns(2)
            with col1:
                with open(video_path, "rb") as f:
                    st.download_button(
                        f"⬇️ Download Video {i+1}",
                        data=f.read(),
                        file_name=Path(video_path).name,
                        mime="video/mp4",
                        use_container_width=True,
                    )
    
    st.markdown("---")
    st.markdown("### Task Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Task ID", task_id)
    with col2:
        st.metric("Script Length", f"{len(result.get('script', ''))} chars")
    with col3:
        st.metric("Images Used", len(result.get("images", [])))
    with col4:
        st.metric("Audio Duration", f"{result.get('audio_duration', 0)}s")
    
    with st.expander("📝 View Full Script"):
        st.text(result.get("script", ""))
    
    with st.expander("🎨 View Prompts"):
        for i, p in enumerate(result.get("prompts", []), 1):
            st.caption(f"{i:02d}: {p}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🆕 Create New Video", type="primary", use_container_width=True):
            # Reset state
            for key in ["task_id", "step", "script", "prompts", "images_uploaded", "result"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.step = "input"
            st.rerun()
    with col2:
        if st.button("📁 Open Task Folder", use_container_width=True):
            st.info(f"Task folder: {task_dir}")


# ─── Run ───
def main():
    """Entry point for streamlit run."""
    pass


if __name__ == "__main__":
    main()
