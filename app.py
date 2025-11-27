import streamlit as st
import requests
import edge_tts
import asyncio
import os
import random
from gtts import gTTS
# FIXED IMPORTS: Using MoviePy 1.0.3
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, ColorClip, ImageClip
from moviepy.video.fx.all import crop, resize, colorx, lum_contrast
from PIL import Image, ImageDraw, ImageFont
from textwrap import wrap

# --- 🎨 CONFIGURATION ---
st.set_page_config(page_title="Cloud Video Factory", page_icon="☁️", layout="wide")
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stButton>button { background-color: #ff4b4b; color: white; width: 100%; border-radius: 8px; font-weight: bold; }
    .stTextInput>div>div>input { background-color: #262730; color: white; }
</style>
""", unsafe_allow_html=True)

# --- 🔑 API KEYS ---
PEXELS_API_KEY = "jQoGddZsH0YvgELlxhdfJfolBlxL1FBwh3AKM7pyR62S1XLWWhNX4AyP"

# --- 🧠 AI FUNCTIONS ---

def get_script(topic, mode):
    """Get Script from Pollinations.ai (Free)"""
    if mode == "Short (Vertical)":
        prompt = f"Write a fast-paced 40-second script about '{topic}'. No intro, straight into facts. Hook the audience immediately."
    else:
        prompt = f"Write a 2-minute educational script about '{topic}'. Include an intro, 3 main points, and a conclusion."
    
    try:
        response = requests.get(f"https://text.pollinations.ai/{prompt}")
        if response.status_code == 200 and len(response.text) > 10:
            return response.text
        else:
            return f"{topic} is a fascinating subject. There is so much to learn about it. Let's dive in."
    except:
        return f"{topic} is a fascinating subject. There is so much to learn about it. Let's dive in."

def get_thumbnail(topic, mode, vibe, filename):
    """Generate Psychological Thumbnail"""
    width, height = (720, 1280) if mode == "Short (Vertical)" else (1280, 720)
    colors = {
        "Urgent/Scary 🔴": "high contrast red and black horror aesthetic glowing eyes",
        "Happy/Exciting 🟡": "bright yellow orange summer vibes euphoric high saturation",
        "Mysterious/Deep 🟣": "deep purple neon blue cyberpunk fog matrix style",
        "Professional/Trust 🔵": "clean white and blue corporate minimal high tech"
    }
    color_prompt = colors.get(vibe, "cinematic lighting")
    prompt = f"youtube thumbnail for {topic}, {color_prompt}, 8k resolution, highly detailed, expressive face"
    url = f"https://image.pollinations.ai/prompt/{prompt}?width={width}&height={height}&model=flux&nologo=true"
    with open(filename, 'wb') as f:
        f.write(requests.get(url).content)

def add_text_on_image(image_path, text, vibe):
    """Add Text to Thumbnail using PIL"""
    try:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        fontsize = int(img.width * 0.12)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fontsize)
        except:
            font = ImageFont.load_default()

        lines = wrap(text.upper(), width=12)
        wrapped_text = "\n".join(lines)
        
        fill_color = "yellow" if "Happy" in vibe else "white"
        if "Scary" in vibe: fill_color = "red"
        
        w, h = img.size
        x, y = w / 2, h / 2
        stroke_width = 8
        draw.multiline_text((x, y), wrapped_text, font=font, fill=fill_color, 
                            stroke_width=stroke_width, stroke_fill="black", anchor="mm", align="center")
        img.save(image_path)
    except Exception as e:
        print(f"Text Error: {e}")

def get_video_clip(query, api_key, mode, filename):
    """Download Video from Pexels"""
    orientation = "portrait" if mode == "Short (Vertical)" else "landscape"
    headers = {'Authorization': api_key}
    url = f"https://api.pexels.com/videos/search?query={query}&orientation={orientation}&per_page=1"
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200 and r.json()['videos']:
            vid_url = r.json()['videos'][0]['video_files'][0]['link']
            with open(filename, 'wb') as f:
                f.write(requests.get(vid_url).content)
            return True
    except:
        pass
    return False

async def get_voice(text, filename):
    """Robust Audio Generation"""
    if not text or len(text) < 5:
        text = "I am sorry, but I could not generate a script for this topic."
    
    # Try Edge-TTS
    try:
        communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
        await communicate.save(filename)
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            return True
    except:
        pass

    # Fallback Google TTS
    try:
        tts = gTTS(text=text, lang='en')
        tts.save(filename)
        return True
    except:
        return False

# --- 🔥 NEW FUNCTION: GENERATE SUBTITLES WITHOUT IMAGEMAGICK ---
def create_subtitle_image(text, width, height, filename="temp_sub.png"):
    """Creates a transparent PNG with text using PIL to avoid MoviePy errors"""
    # Create transparent image
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Font setup
    fontsize = int(width * 0.08) # 8% of width
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fontsize)
    except:
        font = ImageFont.load_default()
        
    # Wrap Text
    lines = wrap(text, width=20)
    wrapped_text = "\n".join(lines)
    
    # Draw Text in Center
    w, h = img.size
    x, y = w / 2, h / 2
    
    # Draw Outline (Black)
    stroke_width = 4
    draw.multiline_text((x, y), wrapped_text, font=font, fill="white", 
                        stroke_width=stroke_width, stroke_fill="black", anchor="mm", align="center")
    
    img.save(filename)
    return filename

def edit_video(video_path, audio_path, script, output_path, mode, vibe):
    """Assemble Video using PIL for Text"""
    video = VideoFileClip(video_path)
    audio = AudioFileClip(audio_path)
    
    # 1. Loop Video
    if video.duration < audio.duration:
        video = video.loop(duration=audio.duration)
    else:
        video = video.subclip(0, audio.duration)
    
    # 2. Resize & Crop
    target_w, target_h = (1080, 1920) if mode == "Short (Vertical)" else (1920, 1080)
    
    if video.w / video.h > target_w / target_h:
        video = video.resize(height=target_h)
        video = video.crop(x1=video.w/2 - target_w/2, width=target_w)
    else:
        video = video.resize(width=target_w)
        video = video.crop(y1=video.h/2 - target_h/2, height=target_h)
        
    # 3. Cinematic Overlay
    video = video.fx(colorx, 0.8)
    if "Scary" in vibe:
        video = video.fx(lum_contrast, contrast=0.2)
        
    video = video.set_audio(audio)
    
    # 4. Subtitles (The Crash Fix)
    # Instead of TextClip, we make an ImageClip from a transparent PNG
    sub_img_path = create_subtitle_image(script, target_w, target_h)
    
    subtitle_clip = ImageClip(sub_img_path).set_duration(video.duration)
    # No need to set position as the PNG is already full size with centered text
    
    final = CompositeVideoClip([video, subtitle_clip])
    final.write_videofile(output_path, fps=24)

# --- 🖥️ DASHBOARD UI ---
st.title("🏭 Cloud Video Factory")
st.write("Generating Content Online - No Laptop Storage Used.")

with st.sidebar:
    st.header("🔑 Access")
    st.success("API Key Integrated!")
    st.divider()
    mode = st.radio("Format", ["Short (Vertical)", "Long (Horizontal)"])
    vibe = st.selectbox("Psychology Vibe", ["Urgent/Scary 🔴", "Happy/Exciting 🟡", "Mysterious/Deep 🟣", "Professional/Trust 🔵"])

topic = st.text_input("Enter Video Topic", "Psychology of Money")

if st.button("🚀 START FACTORY"):
    with st.status("🏗️ Processing in Cloud...", expanded=True):
        st.write("📝 Writing Script...")
        script = get_script(topic, mode)
        
        st.write("🎙️ Recording Voice...")
        if asyncio.run(get_voice(script, "audio.mp3")):
            st.write("🎥 Fetching Video...")
            if not get_video_clip(topic, PEXELS_API_KEY, mode, "bg.mp4"):
                 ColorClip(size=(1080,1920), color=(0,0,0), duration=5).write_videofile("bg.mp4", fps=24)
            
            st.write("🎨 Designing Thumbnail...")
            get_thumbnail(topic, mode, vibe, "thumb.jpg")
            add_text_on_image("thumb.jpg", topic, vibe)
            
            st.write("🎬 Editing (Crash-Proof Mode)...")
            edit_video("bg.mp4", "audio.mp3", script, "final.mp4", mode, vibe)
            st.success("Done!")
            
            c1, c2 = st.columns(2)
            with c1: st.image("thumb.jpg", caption="Thumb"); st.download_button("Download Thumb", open("thumb.jpg", "rb"), "thumb.jpg")
            with c2: st.video("final.mp4"); st.download_button("Download Video", open("final.mp4", "rb"), "video.mp4")
        else:
            st.error("Audio Failed.")
