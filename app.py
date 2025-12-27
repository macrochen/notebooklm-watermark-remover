import streamlit as st
from PIL import Image, ImageDraw
import os
import subprocess
import platform

# --- Helper Functions ---

def get_default_save_path():
    """Returns a default output path in the current working directory."""
    return os.path.join(os.getcwd(), "output")

def select_folder_mac():
    """Opens a native macOS folder selection dialog using AppleScript."""
    try:
        script = '''
        tell application "System Events"
            activate
            set p to POSIX path of (choose folder with prompt "Select Output Folder")
            return p
        end tell
        '''
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return None # User cancelled
    except Exception as e:
        print(f"Error opening folder picker: {e}")
        return None

def on_browse_click():
    """Callback for the browse button."""
    if platform.system() == "Darwin":
        st.toast("Trying to open folder picker... Check your Dock/Taskbar!", icon="🖥️")
        selected = select_folder_mac()
        if selected:
            st.session_state.output_path = selected
    else:
        st.warning("Folder picker only supported on macOS.")

def process_image(image, mask_width, mask_height, bg_strategy, manual_color=None):
    """
    Removes the watermark by covering the bottom-right corner.
    Returns: Processed PIL Image.
    """
    img = image.copy()
    if img.mode != 'RGB':
        img = img.convert('RGB')
        
    width, height = img.size
    
    # Calculate coordinates for the rectangle
    x0 = width - mask_width
    y0 = height - mask_height
    x1 = width
    y1 = height
    
    # Determine Color
    color = (255, 255, 255) # Default white
    
    try:
        if bg_strategy == "Manual" and manual_color:
            h = manual_color.lstrip('#')
            color = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        elif bg_strategy == "Auto-detect (Left)":
            sample_x = max(0, x0 - 5)
            sample_y = min(height - 1, int(y0 + mask_height/2))
            color = img.getpixel((sample_x, sample_y))
        elif bg_strategy == "Auto-detect (Top)":
            sample_x = min(width - 1, int(x0 + mask_width/2))
            sample_y = max(0, y0 - 5)
            color = img.getpixel((sample_x, sample_y))
    except Exception as e:
        print(f"Error picking color: {e}")
        
    # Draw Rectangle
    draw = ImageDraw.Draw(img)
    draw.rectangle([x0, y0, x1, y1], fill=color, outline=None)
    
    return img

def draw_preview_mask(image, mask_width, mask_height):
    """
    Draws a semi-transparent red box on the image to visualize the mask area.
    """
    # Convert to RGBA to support transparency
    img = image.convert("RGBA")
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    width, height = img.size
    x0 = width - mask_width
    y0 = height - mask_height
    x1 = width
    y1 = height
    
    # Draw semi-transparent red rectangle
    draw.rectangle([x0, y0, x1, y1], fill=(255, 0, 0, 100), outline=(255, 0, 0, 255))
    
    # Composite
    return Image.alpha_composite(img, overlay)


# --- UI Setup ---
st.set_page_config(page_title="NotebookLM Watermark Remover", layout="wide")

st.title("🧽 NotebookLM Watermark Remover")
st.markdown("Upload images and adjust the red box to cover the watermark.")

# --- Sidebar Controls ---
st.sidebar.header("⚙️ Settings")

st.sidebar.subheader("1. Adjust Mask Area")
st.sidebar.info("Use these sliders to fit the red box over the watermark.")
mask_width = st.sidebar.slider("Mask Width (px)", min_value=10, max_value=800, value=115, step=5)
mask_height = st.sidebar.slider("Mask Height (px)", min_value=10, max_value=400, value=35, step=5)

st.sidebar.divider()

st.sidebar.subheader("2. Color Strategy")
bg_strategy = st.sidebar.radio(
    "How to pick the background color?",
    ["Auto-detect (Left)", "Auto-detect (Top)", "Manual"],
    index=0
)

manual_color = None
if bg_strategy == "Manual":
    manual_color = st.sidebar.color_picker("Choose Color", "#F8F5EF")

# --- Main Area ---
uploaded_files = st.file_uploader("📂 Choose images...", type=['png', 'jpg', 'jpeg', 'webp'], accept_multiple_files=True)

if uploaded_files:
    st.divider()
    
    # --- Global Controls ---
    st.subheader("💾 Export Settings")
    
    # Initialize session state for output path if not exists
    if 'output_path' not in st.session_state:
        st.session_state.output_path = get_default_save_path()

    col_path, col_browse, col_save = st.columns([3, 1, 2])
    
    with col_path:
        path_input = st.text_input("Save Directory", value=st.session_state.output_path, label_visibility="collapsed")
        # Update session state if user manually types
        st.session_state.output_path = path_input 

    with col_browse:
        st.button("📂 Browse...", on_click=on_browse_click, key="browse_btn")

    with col_save:
        save_btn = st.button("🚀 Save All Processed Images", type="primary", use_container_width=True)

    st.divider()

    # --- Preview Section ---
    col_header, col_toggle = st.columns([4, 1])
    with col_header:
        st.subheader("🖼️ Preview")
    with col_toggle:
        expand_all = st.checkbox("Expand All", value=False)

    processed_images_map = {}

    for i, uploaded_file in enumerate(uploaded_files):
        original_image = Image.open(uploaded_file)
        
        # 1. Generate Preview with Red Box (for visualization)
        preview_with_mask = draw_preview_mask(original_image, mask_width, mask_height)
        
        # 2. Generate Actual Processed Image (for result)
        processed_image = process_image(original_image, mask_width, mask_height, bg_strategy, manual_color)
        processed_images_map[uploaded_file.name] = processed_image
        
        # Determine expand state
        is_expanded = expand_all or (i == 0) # Always expand first one if checkbox is off
        
        with st.expander(f"File: {uploaded_file.name}", expanded=is_expanded):
            col1, col2 = st.columns(2)
            with col1:
                st.image(preview_with_mask, caption="Original + Mask Area (Red)", use_column_width=True)
            with col2:
                st.image(processed_image, caption="Result Preview", use_column_width=True)

    # --- Save Logic ---
    if save_btn:
        target_dir = st.session_state.output_path
        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir)
                st.toast(f"Created directory: {target_dir}", icon="📁")
            except OSError as e:
                st.error(f"Error creating directory: {e}")
                st.stop()
        
        success_count = 0
        for filename, p_img in processed_images_map.items():
            try:
                save_full_path = os.path.join(target_dir, filename)
                p_img.save(save_full_path)
                success_count += 1
            except Exception as e:
                st.error(f"Failed to save {filename}: {e}")
        
        if success_count == len(processed_images_map):
            st.success(f"✅ Saved {success_count} images to: {target_dir}")
            st.balloons()
        else:
            st.warning(f"⚠️ Saved {success_count}/{len(processed_images_map)} images.")

else:
    st.info("👆 Please upload images to start.")
