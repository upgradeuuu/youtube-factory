import streamlit as st
import requests
import edge_tts
import asyncio
import os
import random
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, ColorClip
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

# --- 🧠 AI FUNCTIONS ---

def get_script(topic, mode):
    """Get Script from Pollinations.ai (Free)"""
    if mode == "Short (Vertical)":
        prompt = f"Write a fast-paced 40-second script about '{topic}'. No intro, straight into facts. Hook the audience immediately."
    else:
        prompt = f"Write a 2-minute educational script about '{topic}'. Include an intro, 3 main points, and a conclusion."
    
    try:
        # Use Pollinations Text API
        return requests.get(f"https://text.pollinations.ai/{prompt}").text
    except:
        return f"Error: Could not generate script for {topic}."

def get_thumbnail(topic, mode, vibe, filename):
    """Generate Psychological Thumbnail (Pollinations Image)"""
    # 1. Dimensions
    width, height = (720, 1280) if mode == "Short (Vertical)" else (1280, 720)
    
    # 2. Psychological Color Logic
    colors = {
        "Urgent/Scary 🔴": "high contrast red and black horror aesthetic glowing eyes",
        "Happy/Exciting 🟡": "bright yellow orange summer vibes euphoric high saturation",
        "Mysterious/Deep 🟣": "deep purple neon blue cyberpunk fog matrix style",
        "Professional/Trust 🔵": "clean white and blue corporate minimal high tech"
    }
    color_prompt = colors.get(vibe, "cinematic lighting")
    
    # 3. Request Image
    prompt = f"youtube thumbnail for {topic}, {color_prompt}, 8k resolution, highly detailed, expressive face"
    url = f"https://image.pollinations.ai/prompt/{prompt}?width={width}&height={height}&model=flux&nologo=true"
    
    with open(filename, 'wb') as f:
        f.write(requests.get(url).content)

def add_text_on_image(image_path, text, vibe):
    """Add Big Bold Text to Thumbnail"""
    try:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        
        # Dynamic Font Size
        fontsize = int(img.width * 0.12)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fontsize)
        except:
            font = ImageFont.load_default()

        # Wrap Text
        lines = wrap(text.upper(), width=12)
        wrapped_text = "\n".join(lines)
        
        # Text Color
        fill_color = "yellow" if "Happy" in vibe else "white"
        if "Scary" in vibe: fill_color = "red"
        
        # Center Position
        # (Simple centering math for fallback fonts)
        w, h = img.size
        x, y = w / 2, h / 2
        
        # Draw Outline (Thick Stroke)
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
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save(filename)

def edit_video(video_path, audio_path, script, output_path, mode, vibe):
    """Assemble Video with Overlay & Subtitles"""
    video = VideoFileClip(video_path)
    audio = AudioFileClip(audio_path)
    
    # 1. Loop Video
    if video.duration < audio.duration:
        video = video.loop(duration=audio.duration)
    else:
        video = video.subclip(0, audio.duration)
    
    # 2. Resize & Crop (Fill Screen)
    target_w, target_h = (1080, 1920) if mode == "Short (Vertical)" else (1920, 1080)
    
    # Resize to fit width or height, then center crop
    if video.w / video.h > target_w / target_h:
        video = video.resize(height=target_h)
        video = video.crop(x1=video.w/2 - target_w/2, width=target_w)
    else:
        video = video.resize(width=target_w)
        video = video.crop(y1=video.h/2 - target_h/2, height=target_h)
        
    # 3. Cinematic Overlay (Dimming for subtitles)
    video = video.fx(colorx, 0.8) # Darken slightly
    if "Scary" in vibe:
        video = video.fx(lum_contrast, contrast=0.2) # High contrast
        
    video = video.set_audio(audio)
    
    # 4. Subtitles
    fontsize = 80 if mode == "Short (Vertical)" else 60
    txt = TextClip(script, fontsize=fontsize, color='white', font='DejaVu-Sans-Bold',
                   stroke_color='black', stroke_width=3, method='caption',
                   size=(target_w * 0.9, None), align='center')
    txt = txt.set_pos('center').set_duration(video.duration)
    
    final = CompositeVideoClip([video, txt])
    final.write_videofile(output_path, fps=24)

# --- 🖥️ DASHBOARD UI ---
st.title("🏭 Cloud Video Factory")
st.write("Generating Content Online - No Laptop Storage Used.")

with st.sidebar:
    st.header("🔑 Access")
    # Secret Key Loader
    if "PEXELS_KEY" in st.secrets:
        api_key = st.secrets["PEXELS_KEY"]
        st.success("API Key Connected!")
    else:
        api_key = st.text_input("Paste Pexels API Key", type="password")
    
    st.divider()
    mode = st.radio("Format", ["Short (Vertical)", "Long (Horizontal)"])
    vibe = st.selectbox("Psychology Vibe", 
        ["Urgent/Scary 🔴", "Happy/Exciting 🟡", "Mysterious/Deep 🟣", "Professional/Trust 🔵"])

topic = st.text_input("Enter Video Topic", "Psychology of Money")

if st.button("🚀 START FACTORY"):
    if not api_key:
        st.error("Please enter Pexels Key in sidebar!")
    else:
        with st.status("🏗️ Processing in Cloud...", expanded=True):
            st.write("📝 Writing Script (Pollinations AI)...")
            script = get_script(topic, mode)
            
            st.write("🎙️ Recording Voice (Edge-TTS)...")
            asyncio.run(get_voice(script, "audio.mp3"))
            
            st.write("🎥 Searching Pexels Video...")
            if not get_video_clip(topic, api_key, mode, "bg.mp4"):
                st.warning("Video not found. Using Black Background.")
                ColorClip(size=(1080,1920), color=(0,0,0), duration=5).write_videofile("bg.mp4", fps=24)
            
            st.write(f"🎨 Creating '{vibe}' Thumbnail...")
            get_thumbnail(topic, mode, vibe, "thumb.jpg")
            add_text_on_image("thumb.jpg", topic, vibe)
            
            st.write("🎬 Editing Final Cut...")
            edit_video("bg.mp4", "audio.mp3", script, "final.mp4", mode, vibe)
            
        st.success("Production Complete!")
        
        c1, c2 = st.columns(2)
        with c1:
            st.image("thumb.jpg", caption="Thumbnail")
            with open("thumb.jpg", "rb") as f:
                st.download_button("⬇️ Download Thumb", f, "thumb.jpg")
        with c2:
            st.video("final.mp4")
            with open("final.mp4", "rb") as f:
                st.download_button("⬇️ Download Video", f, "video.mp4")
