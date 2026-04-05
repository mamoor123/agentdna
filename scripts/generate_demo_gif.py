"""Generate a terminal demo GIF for AgentDNA."""

from PIL import Image, ImageDraw, ImageFont
import subprocess
import os
import tempfile

# Terminal settings
WIDTH, HEIGHT = 720, 480
BG_COLOR = (30, 30, 30)
TEXT_COLOR = (204, 204, 204)
GREEN = (0, 255, 0)
YELLOW = (255, 200, 87)
RED = (255, 95, 86)
CYAN = (0, 200, 200)
DIM = (120, 120, 120)
PROMPT_COLOR = (100, 200, 100)
WHITE = (255, 255, 255)

FONT_SIZE = 14
LINE_H = 20
PAD_X = 20
PAD_Y = 15

def get_font():
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, FONT_SIZE)
    return ImageFont.load_default()

FONT = get_font()

def draw_terminal(lines, cursor_visible=False):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Title bar
    draw.rectangle([0, 0, WIDTH, 30], fill=(50, 50, 50))
    draw.ellipse([12, 10, 22, 20], fill=(255, 95, 86))
    draw.ellipse([28, 10, 38, 20], fill=(255, 189, 46))
    draw.ellipse([44, 10, 54, 20], fill=(39, 201, 63))
    draw.text((WIDTH//2 - 60, 8), "Terminal — AgentDNA Demo", fill=DIM, font=FONT)
    
    y = PAD_Y + 20
    for text, color in lines:
        draw.text((PAD_X, y), text, fill=color, font=FONT)
        y += LINE_H
    
    if cursor_visible:
        draw.rectangle([PAD_X, y - LINE_H + 2, PAD_X + 8, y - 2], fill=TEXT_COLOR)
    
    return img

# Define the demo sequence
typing_speed = 2  # frames per character
pause_frames = 15  # pause between commands
long_pause = 30

def colored_text(text):
    """Simple colored line: (text, color)"""
    return (text, TEXT_COLOR)

def make_lines_partial(full_lines, char_count):
    """Show partial typing effect."""
    lines = []
    remaining = char_count
    for text, color in full_lines:
        if remaining <= 0:
            break
        if remaining >= len(text):
            lines.append((text, color))
            remaining -= len(text)
        else:
            lines.append((text[:remaining], color))
            remaining = 0
    return lines

# Full demo content
demo_lines = [
    ("pip install agentdna-sdk", PROMPT_COLOR),
    ("", TEXT_COLOR),
    ("Collecting agentdna-sdk...", DIM),
    ("  Downloading agentdna_sdk-0.2.0-py3-none-any.whl (43 kB)", DIM),
    ("Installing collected packages: agentdna-sdk", DIM),
    ("Successfully installed agentdna-sdk-0.2.0", GREEN),
    ("", TEXT_COLOR),
    ("python examples/demo.py", PROMPT_COLOR),
    ("", TEXT_COLOR),
    ("🧬 AgentDNA — Sentry for AI Agents", CYAN),
    ("", TEXT_COLOR),
    ("Simulating 50 agent calls...", TEXT_COLOR),
    ("", TEXT_COLOR),
    ("==================================================", DIM),
    ("📊 AGENTDNA STATS (persisted to SQLite)", CYAN),
    ("==================================================", DIM),
    ("", TEXT_COLOR),
    ("  📌 fact-checker", TEXT_COLOR),
    ("     ⚠️  █████████░ 90%  |  10 calls", YELLOW),
    ("     ⏱️  avg 770ms  p95 1181ms", TEXT_COLOR),
    ("     ❌ Errors: ConnectionError(1)", RED),
    ("", TEXT_COLOR),
    ("  📌 summarizer", TEXT_COLOR),
    ("     ✅ ██████████ 100%  |  10 calls", GREEN),
    ("     ⏱️  avg 422ms  p95 739ms", TEXT_COLOR),
    ("", TEXT_COLOR),
    ("  📌 transcriber", TEXT_COLOR),
    ("     ✅ ██████████ 100%  |  10 calls", GREEN),
    ("     ⏱️  avg 278ms  p95 383ms", TEXT_COLOR),
    ("", TEXT_COLOR),
    ("==================================================", DIM),
    ("💾 All stats saved to ~/.agentdna/observe.db", DIM),
    ("🔍 Run 'agentdna stats' anytime to view them", DIM),
    ("", TEXT_COLOR),
    ("agentdna stats", PROMPT_COLOR),
    ("", TEXT_COLOR),
    ("📊 AgentDNA — 3 observed function(s)", CYAN),
    ("", TEXT_COLOR),
    ("  📌 fact-checker", TEXT_COLOR),
    ("     ⚠️  Degraded  10 calls  █████████░ 90%  avg 770ms", YELLOW),
    ("     ❌ 1 failures: ConnectionError(1)", RED),
    ("", TEXT_COLOR),
    ("  📌 summarizer", TEXT_COLOR),
    ("     ✅ Healthy  10 calls  ██████████ 100%  avg 422ms", GREEN),
    ("", TEXT_COLOR),
    ("  📌 transcriber", TEXT_COLOR),
    ("     ✅ Healthy  10 calls  ██████████ 100%  avg 428ms", GREEN),
    ("", TEXT_COLOR),
    ("pip install agentdna-sdk", DIM),
]

# Generate frames
frames = []
frame_durations = []

# Command 1: pip install (type then show output)
cmd1_lines = demo_lines[:7]
cmd2_start = 7

# Phase 1: Type pip install
for i in range(len("pip install agentdna-sdk")):
    lines = [("pip install agentdna-sdk"[:i+1], PROMPT_COLOR)]
    frames.append(draw_terminal(lines, cursor_visible=True))
    frame_durations.append(60)

# Pause on command
frames.append(draw_terminal([cmd1_lines[0]], cursor_visible=True))
frame_durations.append(200)

# Show pip output
for i in range(1, len(cmd1_lines)):
    lines = cmd1_lines[:i+1]
    frames.append(draw_terminal(lines))
    frame_durations.append(80 if "Successfully" not in cmd1_lines[i][0] else 300)

# Hold on finished pip
frame_durations[-1] = 500

# Phase 2: Type python command
cmd2_line = ("python examples/demo.py", PROMPT_COLOR)
for i in range(len(cmd2_line[0])):
    lines = cmd1_lines + [("", TEXT_COLOR), (cmd2_line[0][:i+1], PROMPT_COLOR)]
    frames.append(draw_terminal(lines, cursor_visible=True))
    frame_durations.append(60)

# Pause
frames.append(draw_terminal(cmd1_lines + [("", TEXT_COLOR), cmd2_line], cursor_visible=True))
frame_durations.append(200)

# Phase 3: Show demo output
output_start = 8  # after python command lines
output_lines = demo_lines[output_start:37]  # up to the stats

for i in range(len(output_lines)):
    lines = cmd1_lines + [("", TEXT_COLOR), cmd2_line, ("", TEXT_COLOR)] + output_lines[:i+1]
    # Keep only last ~18 visible lines
    visible = lines[-18:]
    frames.append(draw_terminal(visible))
    d = 80
    if "AGENTDNA STATS" in output_lines[i][0]:
        d = 400
    elif any(e in output_lines[i][0] for e in ["████", "Errors:", "📌"]):
        d = 120
    elif "saved to" in output_lines[i][0]:
        d = 500
    frame_durations.append(d)

# Hold on final output
frame_durations[-1] = 800

# Phase 4: Type agentdna stats
stats_lines = demo_lines[37:52]
cmd3_line = ("agentdna stats", PROMPT_COLOR)

for i in range(len(cmd3_line[0])):
    last = output_lines[-8:] if len(output_lines) > 8 else output_lines
    lines = [cmd1_lines[-1], ("", TEXT_COLOR), cmd2_line, ("", TEXT_COLOR)] + output_lines[-6:] + [("", TEXT_COLOR), (cmd3_line[0][:i+1], PROMPT_COLOR)]
    frames.append(draw_terminal(lines, cursor_visible=True))
    frame_durations.append(60)

# Pause
lines = [cmd1_lines[-1], ("", TEXT_COLOR), cmd2_line, ("", TEXT_COLOR)] + output_lines[-6:] + [("", TEXT_COLOR), cmd3_line]
frames.append(draw_terminal(lines, cursor_visible=True))
frame_durations.append(200)

# Show stats output
for i in range(len(stats_lines)):
    lines = [cmd2_line, ("", TEXT_COLOR)] + output_lines[-4:] + [("", TEXT_COLOR), cmd3_line, ("", TEXT_COLOR)] + stats_lines[:i+1]
    visible = lines[-18:]
    frames.append(draw_terminal(visible))
    d = 80
    if any(e in stats_lines[i][0] for e in ["████", "📌", "failures"]):
        d = 150
    frame_durations.append(d)

# Hold on final
frame_durations[-1] = 1500

# Save as GIF
output_path = "/root/.openclaw/workspace/agentdna/docs/demo.gif"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

# Convert durations from ms to 10ms (GIF format) and save
durations_cs = [max(2, d // 10) for d in frame_durations]

frames[0].save(
    output_path,
    save_all=True,
    append_images=frames[1:],
    duration=durations_cs,
    loop=0,
    optimize=True,
)

print(f"✅ Generated {len(frames)} frames → {output_path}")
print(f"   Size: {os.path.getsize(output_path) / 1024:.0f} KB")
