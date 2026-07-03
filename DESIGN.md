# Reel Engine — Design Concept

> Facebook Reels automation tool, custom từ MoneyPrinterTurbo
> Designer: Luffy (trước khi code)

---

## 1. Problem / Why

MPT sinh video chung chung cho đủ nền tảng, dùng stock footage làm visual chính. 

Vấn đề:
- Facebook Reels cần hook mạnh 3s đầu, không phải "video có script + nhạc" là đủ
- Stock footage kém viral — Reels content bùng nổ nhất là **meme + shock + personal story + talking head có text**
- Không có tối ưu cho thuật toán Reels (retention, loop rate, share incentive)
- Không auto-post Facebook (MPT chỉ hỗ trợ TikTok/IG/YT)

Target: **creator / agency nhỏ** muốn auto-pump Reels content hàng ngày.

---

## 2. Core Philosophy

**"You give the seed, Reel Engine grows the tree."**

Input tối thiểu: **1 chủ đề** (hoặc 1 source content: link, article, video)

Output: **1+ Reels ready-to-post**, tối ưu viral mechanic Facebook.

---

## 3. Pipeline (draft)

```
Input ──► 1. Ingest
              │
              ▼
          2. Script Engine (hook + narrative + CTA)
              │
              ▼
          3. Visual Engine (ảnh AI + stock footage + text overlay)
              │
              ▼
          4. Audio Engine (TTS + BGM + sound FX)
              │
              ▼
          5. Subtitle Engine (burn-in, styled, motion)
              │
              ▼
          6. Assembly Engine (clips → transitions → overlay → timing)
              │
              ▼
          7. Optimizer (retention check, length adjust)
              │
              ▼
          8. Facebook Publisher (Graph API)
```

---

## 4. Module Deep-Dive

### 4.1 Ingest Layer
- **Text input**: chủ đề, keyword, hoặc URL article
- **Link input**: quét article/blog làm content seed
- **Re-upload input**: download Reels từ link → transcribe → re-script (nội dung gốc)
- **Batch input**: CSV nhiều topic, tạo loạt Reels

### 4.2 Script Engine — Khác MPT nhất
MPT: LLM sinh script generic.

Reel Engine:
- **Hook templates**: "3 things that will change your mind about X", "This is why you should never Y", "I tried Z for 30 days and here's what happened"
- **Story arc**: Hook (3s) → Problem → Twist → Solution → CTA
- **Tone config**: shock, humor, educational, motivational, storytelling
- **Length config**: 15s, 30s, 60s, 90s
- **Locale**: tiếng Việt, tiếng Anh

### 4.3 Visual Engine
Nguồn visual:
1. **AI image generation** — tạo từ prompt, style: meme, illustration, realistic
2. **Stock footage** — Pexels/Pixabay (như MPT)
3. **Text-only slides** — cho kiểu quote / fact video
4. **Template-based** — có sẵn background, chỉ replace text

**Khác MPT**: MPT chỉ stock footage. Reel Engine hỗ trợ multimodal visual — vì Reels content đa dạng hơn YouTube documentary.

### 4.4 Audio Engine
- **TTS**: Edge TTS (free, như MPT)
- **Voice clone**: ElevenLabs (optional)
- **Sound effects**: hook sound, notification sound, reaction sound
- **BGM**: auto-select theo mood (hoặc custom)
- **Voice + BGM auto ducking**

### 4.5 Subtitle Engine
- **Whisper** timing (giữ từ MPT)
- **Styled overlay**: font, color, stroke, background
- **Motion subtitles**: từng chữ/dòng xuất hiện theo nhịp (giống Reels viral)
- **Caption blocks**: cho quote video, text full màn hình

### 4.6 Assembly Engine
- **9:16** — Reels format mặc định
- **Clip composition**: ảnh tĩnh pan/zoom (Ken Burns), video clips ghép
- **Transitions**: giữ từ MPT, thêm caption transition
- **Text overlay**: hook text đầu + CTA cuối + watermark
- **Pacing**: auto-cut silent gap, speed up/slow down

### 4.7 Optimizer (unique)
- **Retention check**: ước tính viewer retention dựa trên script pacing
- **Loop check**: video có natural loop point không (auto-trim cho loop)
- **Hook strength**: 3s đầu có đủ curiosity gap không
- **Length validation**: Facebook Reels tối ưu 15-60s

### 4.8 Publisher
- **Facebook Graph API**: page posting, Reels upload
- **Scheduling**: lịch đăng hàng ngày
- **Batch post**: nhiều Reels / nhiều page
- **Analytics**: view, retention, shares (crawl sau post)

---

## 5. User Flow

### CLI
```bash
reel-engine --topic "tại sao người thành công dậy lúc 5h sáng" \
  --tone educational \
  --length 30s \
  --count 3 \
  --publish
```

### Config-driven (giống MPT)
```toml
[topic]
subject = "tại sao người thành công dậy lúc 5h sáng"
language = "vi"
tone = "educational"

[video]
aspect = "16:9"
length = 30  # seconds
count = 3
hooks = ["shock", "curiosity"]

[visual]
source = "ai+stock"  # mixed
style = "realistic"
ai_model = "stable-diffusion"
stock_source = "pexels"

[audio]
tts_voice = "vi-VN-HoaiMyNeural"
bgm_type = "random"
bgm_volume = 0.15

[subtitle]
enabled = true
style = "motion"  # static | motion
position = "bottom"
font = "Roboto-Bold"
foreground = "#FFFFFF"
stroke = "#000000"

[publish]
enabled = false
platform = "facebook"
page_id = ""
access_token = ""
schedule = "daily@08:00"
```

---

## 6. Pipeline Stage Hooks (stop-at)

Giống MPT, mỗi stage có thể dừng để user kiểm tra:

```
topic → script (stop) → terms (stop) → visuals (stop) → 
audio (stop) → subtitle (stop) → assembly (stop) → 
optimize (stop) → publish
```

Cho phép user can thiệp từng bước.

---

## 7. Tech Stack (LOCAL-FIRST, không cần internet cho core pipeline)

| Component | Choice | Cost | Network | Lý do |
|-----------|--------|------|---------|-------|
| Language | Python | Free | - | MPT codebase, ecosystem, AI libs |
| Web framework | FastAPI | Free | - | reuse MPT pattern |
| CLI | argparse | Free | - | reuse MPT |
| Web UI | Streamlit | Free | - | reuse MPT |
| **LLM** | **9router local API** | **FREE** | **Local network** | All-in-one model, tương thích OpenAI format |
| **TTS** | **Edge TTS** | **FREE** | Online | Microsoft Edge TTS, không cần key |
| **Subtitle** | **Whisper (local)** | **FREE** | **Offline** | faster-whisper, chạy local |
| **Image gen** | **Stable Diffusion local** (AUTOMATIC1111 API) | **FREE** | **Offline** | chạy local, không limit |
| Stock footage | Pexels/Pixabay (fallback) | Free tier | Online | backup khi không dùng AI image |
| Video | moviepy + ffmpeg | Free | - | open source |
| DB | file-based JSON | Free | - | đơn giản, không cần server |
| State | file-based | Free | - | reuse MPT pattern |
| Publish | Graph API (requests) | Free | Online | Facebook native API (chỉ khi publish) |

### Deployment Strategy: LOCAL-FIRST

**Core pipeline 100% offline:**
1. LLM: Ollama local (Llama 3.1 8B hoặc Mistral 7B)
2. Image gen: Stable Diffusion WebUI local (AUTOMATIC1111)
3. Subtitle: faster-whisper local
4. Video: moviepy + ffmpeg

→ Tạo video hoàn chỉnh **không cần internet**.

**Online chỉ khi:**
- TTS (Edge TTS cần internet, nhưng free)
- Stock footage download (nếu dùng)
- Publish lên Facebook (Graph API)

### Local Setup Requirements

**Minimum:**
- CPU: 4 cores
- RAM: 8GB
- GPU: không bắt buộc, nhưng nên có (RTX 3060+ hoặc tương đương)
- Disk: 20GB (models + workspace)

**Models cần download:**
- Ollama: Llama 3.1 8B (~4.7GB) hoặc Mistral 7B (~4.1GB)
- Whisper: large-v3 (~3GB) hoặc medium (~1.5GB)
- Stable Diffusion: SD 1.5 (~4GB) hoặc SDXL (~6.9GB)

Tổng: ~12-15GB models.

### Fallback Options

**Nếu không có GPU mạnh:**
- Image gen: dùng Pollinations.ai API (free online, không cần setup)
- LLM: dùng gpt4free (free online proxies)
- Whisper: dùng model nhỏ hơn (base ~150MB, small ~500MB)

**Nếu muốn quality cao hơn:**
- LLM: OpenAI/Claude API
- Image gen: DALL-E 3 / Midjourney
- TTS: ElevenLabs voice clone

---

## 8. Khác biệt với MPT

| Aspect | MPT | Reel Engine |
|--------|-----|-------------|
| Target platform | TikTok/IG/YT Shorts | **Facebook Reels** |
| Visual type | stock footage chủ yếu | AI image + stock + text slides |
| Hook optimization | không | Hook templates + strength check |
| Retention | không | Retention check + loop optimizer |
| Content types | educational/general | shock, humor, educational, motivational, storytelling |
| Image AI | không | Tích hợp SD/Pollinations |
| Facebook publish | không | Graph API |
| Watermark | không | Auto watermark (tuỳ chọn) |
| Batch scheduling | manual | Daily batch scheduler |
| Analytics | không | View/retention tracking |

---

## 9. Viral Hook Templates (draft)

```
Type          | Template
--------------|----------
Shock         | "99% của mọi người không biết điều này..."
Curiosity     | "Tôi đã thử [X] trong 30 ngày, kết quả..."
Contrarian    | "Mọi người bảo [X] là tốt, nhưng sự thật là..."
Number list   | "3 dấu hiệu cho thấy bạn đang [Y] sai cách"
Story         | "Hồi 2019, tôi từng mất tất cả vì..."
Myth bust     | "Bạn nghĩ [X] là thật? Nó hoàn toàn sai."
Question      | "Tại sao người thông minh lại thường [Z]?"
```

---

## 10. Monetization góc nhìn

- **Freemium**: CLI free, WebUI + batch pro
- **White-label agency version**: watermark custom, multi-page management
- **Service**: SaaS deploy (one-click Reel farm)

---

## 11. Risk / Challenges

- Facebook Graph API policy thay đổi → cần fallback manual upload
- Quality control: AI ảnh có thể xấu hoặc không consistent
- Ethical: tránh spam content, misinformation
- MPT license (MIT) → cần credit đúng

---

**Next step sau khi bạn duyệt design:**
1. Code structure / folder layout
2. Module specs
3. Coding → test → GitHub

---
