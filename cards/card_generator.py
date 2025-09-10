import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont, filedialog, colorchooser
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk
import re
import uuid

# --- Configuration ---
CARD_WIDTH = 420
CARD_HEIGHT = 600
ARTWORK_RECT = (40, 90, 380, 340)  # (left, top, right, bottom)
RULES_RECT = (30, 400, CARD_WIDTH - 30, 515) # (left, top, right, bottom)

# Set base paths using os.path.join for cross-platform compatibility
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) 
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "generated_cards")
DATA_FILE = os.path.join(SCRIPT_DIR, "card_data.json")
UI_DIR = os.path.join(PROJECT_ROOT, "Images", "UI")
ENERGY_ICON_DIR = os.path.join(UI_DIR, "Energy")
# --- Updated & New Paths ---
BACKGROUND_DIR = os.path.join(PROJECT_ROOT, "Images", "Backgrounds", "cards") # For faction/type BGs
CARD_ART_DIR = os.path.join(PROJECT_ROOT, "Images", "Backgrounds",) # For artwork & art BGs
BORDER_DIR = os.path.join(PROJECT_ROOT, "Images", "Backgrounds", "cards") # For custom borders


FACTION_COLORS = {
    "Soul Reaper": ("#E0E0E0", "#1C1C1C"),
    "Arrancar": ("#1C1C1C", "#FFFFFF"),
    "Quincy": ("#FFFFFF", "#007ACC"),
    "Human": ("#A0A0A0", "#000000"),
    "Default": ("#CCCCCC", "#000000")
}

ENERGY_MAPPING = {
    "W": "energy_white.png",
    "B": "energy_black.png",
    "U": "energy_blue.png",
    "G": "energy_gray.png",
}

BACKGROUND_MAPPING = {
    # Faction Backgrounds
    "Soul Reaper": "SR_BG.png",
    "Arrancar": "AR_BG.png",
    "Hollow": "AR_BG.png", # Hollows can share the Arrancar BG
    "Quincy": "QN_BG.png",
    "Human": "HM_BG.png",
    # Type Backgrounds
    "Technique": "T_BG.png",
    "Equipment": "E_BG.png",
    "Field": "F_BG.png",
}

# --- Helper Functions ---
def get_fonts(font_family):
    """Loads different sizes of a specified system font."""
    try:
        fonts = {
            "regular": ImageFont.truetype(f"{font_family}.ttf", 16),
            "bold": ImageFont.truetype(f"{font_family}b.ttf", 16), 
            "bold_title": ImageFont.truetype(f"{font_family}b.ttf", 22),
            "bold_subtitle": ImageFont.truetype(f"{font_family}b.ttf", 14),
            "stats": ImageFont.truetype(f"{font_family}b.ttf", 18),
            "italic": ImageFont.truetype(f"{font_family}i.ttf", 14),
            "bold_italic": ImageFont.truetype(f"{font_family}bi.ttf", 14),
            "energy": ImageFont.truetype(f"{font_family}b.ttf", 20) # Default energy font
        }
    except IOError:
        print(f"Warning: Could not load styled fonts for '{font_family}'. Falling back to default.")
        fonts = { k: ImageFont.load_default() for k in ["regular", "bold", "bold_title", "bold_subtitle", "stats", "italic", "bold_italic", "energy"]}
    return fonts

def text_wrap(text, font, max_width, inline_icon_size=16):
    """Wraps text to fit within a specified width, accounting for inline icons."""
    lines = []
    if not text: return lines
    
    get_len = lambda t, f: f.getlength(t) if hasattr(f, 'getlength') else f.getsize(t)[0]

    for paragraph in text.split('\n'):
        tokens = re.split(r'(\s|\(\w\))', paragraph)
        tokens = [t for t in tokens if t] 

        current_line = ""
        current_width = 0

        for token in tokens:
            token_width = 0
            is_icon = re.match(r'\(([WBUG])\)', token)
            is_space = token.isspace()

            if is_icon:
                token_width = inline_icon_size
            elif not is_space:
                clean_token = re.sub(r'</?b>', '', token)
                token_width = get_len(clean_token, font)
            else: # is a space
                token_width = get_len(' ', font)
            
            if current_width + token_width > max_width and current_line:
                lines.append(current_line.strip())
                current_line = token
                current_width = token_width
            else:
                current_line += token
                current_width += token_width
        
        lines.append(current_line.strip())
    return lines


def draw_formatted_text_line(card_image, pos, text, default_font, bold_font, fill, energy_icons):
    """Draws a line of text, handling <b> tags and inline energy icons."""
    x, y = pos
    draw = ImageDraw.Draw(card_image)
    
    parts = re.split(r'(<b>|</b>|\([WBUG]\))', text)
    is_bold = False

    inline_icon_size = default_font.getbbox("A")[3] 

    for part in parts:
        if not part: continue
        
        if part == '<b>': is_bold = True; continue
        elif part == '</b>': is_bold = False; continue

        match = re.match(r'\(([WBUG])\)', part)
        if match:
            energy_code = match.group(1)
            if icon_img := energy_icons.get(energy_code):
                icon_img = icon_img.resize((inline_icon_size, inline_icon_size), Image.Resampling.LANCZOS)
                card_image.paste(icon_img, (int(x), int(y)), icon_img)
                x += inline_icon_size
            continue

        current_font = bold_font if is_bold else default_font
        draw.text((x, y), part, font=current_font, fill=fill)
        try: x += current_font.getlength(part)
        except AttributeError: x += current_font.getsize(part)[0]


# --- Core Card Generation Logic ---

def create_card_image(card_data, fonts, energy_icons):
    """Generates a single card image from data, now with custom backgrounds and borders."""
    faction = card_data.get("faction", "Default")
    default_bg, default_text = FACTION_COLORS.get(faction, FACTION_COLORS.get("Default"))
    bg_color = card_data.get("background_color", default_bg)
    text_color = card_data.get("text_color", default_text)
    border_color = card_data.get("border_color", text_color)
    
    # --- New Custom Border Logic ---
    if border_path := card_data.get("card_border_path"):
        if os.path.exists(border_path):
            try:
                card = Image.open(border_path).convert("RGB")
                card = ImageOps.fit(card, (CARD_WIDTH, CARD_HEIGHT), Image.Resampling.LANCZOS)
            except Exception as e:
                print(f"Error loading custom border image: {e}")
                card = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), color=border_color)
        else:
            card = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), color=border_color)
    else:
        card = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), color=border_color)
    # --- End Custom Border Logic ---

    inner_bg = Image.new('RGB', (CARD_WIDTH - 20, CARD_HEIGHT - 20), color=bg_color)
    
    if card_bg_path := card_data.get("card_background_path"):
        if os.path.exists(card_bg_path):
            try:
                card_bg_img = Image.open(card_bg_path).convert("RGBA")
                card_bg_img = ImageOps.fit(card_bg_img, inner_bg.size, Image.Resampling.LANCZOS)
                inner_bg.paste(card_bg_img, (0,0), card_bg_img)
            except Exception as e:
                print(f"Error loading card background image: {e}")
    card.paste(inner_bg, (10,10))

    draw = ImageDraw.Draw(card, "RGBA")
    
    artwork_size = (ARTWORK_RECT[2] - ARTWORK_RECT[0], ARTWORK_RECT[3] - ARTWORK_RECT[1])
    final_artwork = Image.new("RGBA", artwork_size)
    
    if bg_path := card_data.get("background_path"):
        if os.path.exists(bg_path):
            try:
                bg_img = Image.open(bg_path).convert("RGBA")
                bg_scale = float(card_data.get("background_scale", 1.0))
                bg_size = (int(artwork_size[0] * bg_scale), int(artwork_size[1] * bg_scale))
                if bg_size[0] > 0 and bg_size[1] > 0: bg_img = ImageOps.fit(bg_img, bg_size, Image.Resampling.LANCZOS)
                bg_x, bg_y = int(card_data.get("background_x", 0)), int(card_data.get("background_y", 0))
                px, py = (artwork_size[0] - bg_img.width) // 2 + bg_x, (artwork_size[1] - bg_img.height) // 2 + bg_y
                final_artwork.paste(bg_img, (px, py))
            except Exception as e: print(f"Error loading BG image: {e}")

    if art_path := card_data.get("artwork_path"):
        if os.path.exists(art_path):
            try:
                art_img = Image.open(art_path).convert("RGBA")
                scale = float(card_data.get("artwork_scale", 1.0))
                ss = (int(art_img.width * scale), int(art_img.height * scale))
                if ss[0] > 0 and ss[1] > 0: art_img = art_img.resize(ss, Image.Resampling.LANCZOS)
                x_off, y_off = int(card_data.get("artwork_x", 0)), int(card_data.get("artwork_y", 0))
                px, py = (artwork_size[0] - art_img.width) // 2 + x_off, (artwork_size[1] - art_img.height) // 2 + y_off
                final_artwork.paste(art_img, (px, py), art_img)
            except Exception as e: print(f"Error loading art image: {e}")

    card.paste(final_artwork, (ARTWORK_RECT[0], ARTWORK_RECT[1]), final_artwork)
    draw.rectangle(ARTWORK_RECT, outline=text_color, width=1)
    
    draw.text((20, 20), card_data.get('name', ''), fill=text_color, font=fonts["bold_title"])
    draw.text((22, 50), card_data.get('subtitle', ''), fill=text_color, font=fonts["bold_subtitle"])

    if energy_cost_info := card_data.get("energy_icons"):
        icon_size = 25; energy_font_size = 18 
        energy_text_x_offset = card_data.get("energy_text_x_offset", 5)
        energy_text_y_offset = card_data.get("energy_text_y_offset", 2)
        try: energy_font = ImageFont.truetype("arialbd.ttf", energy_font_size)
        except IOError: energy_font = fonts["energy"] 
        
        x_offset = CARD_WIDTH - 20 - icon_size
        for color_code, count in reversed(list(energy_cost_info.items())):
            if color_code == "N": continue
            if icon_img := energy_icons.get(color_code):
                icon_img = icon_img.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
                card.paste(icon_img, (x_offset, 20), icon_img)
                cost_str = str(count); text_bbox = draw.textbbox((0,0), cost_str, font=energy_font)
                text_w, text_h = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
                text_pos = (x_offset + (icon_size - text_w) / 2 + energy_text_x_offset, 20 + (icon_size - text_h) / 2 - 2 + energy_text_y_offset)
                draw.text((text_pos[0]-1, text_pos[1]-1), cost_str, font=energy_font, fill="black"); draw.text((text_pos[0]+1, text_pos[1]-1), cost_str, font=energy_font, fill="black")
                draw.text((text_pos[0]-1, text_pos[1]+1), cost_str, font=energy_font, fill="black"); draw.text((text_pos[0]+1, text_pos[1]+1), cost_str, font=energy_font, fill="black")
                draw.text(text_pos, cost_str, font=energy_font, fill="white")
                x_offset -= (icon_size + 5)

        if generic_cost := energy_cost_info.get("N"):
            if icon_img := energy_icons.get("N"):
                icon_img = icon_img.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
                card.paste(icon_img, (x_offset, 20), icon_img)
                cost_str = str(generic_cost); text_bbox = draw.textbbox((0,0), cost_str, font=energy_font)
                text_w, text_h = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
                text_pos = (x_offset + (icon_size - text_w) / 2 + energy_text_x_offset, 20 + (icon_size - text_h) / 2 - 2 + energy_text_y_offset)
                draw.text((text_pos[0]-1, text_pos[1]-1), cost_str, font=energy_font, fill="black"); draw.text((text_pos[0]+1, text_pos[1]-1), cost_str, font=energy_font, fill="black")
                draw.text((text_pos[0]-1, text_pos[1]+1), cost_str, font=energy_font, fill="black"); draw.text((text_pos[0]+1, text_pos[1]+1), cost_str, font=energy_font, fill="black")
                draw.text(text_pos, cost_str, font=energy_font, fill="white")

    type_line = f"{card_data.get('type', '')} - {card_data.get('subtypes', '')}".strip(" -")
    draw.text((20, 370), type_line, fill=text_color, font=fonts["bold_subtitle"])
    draw.rectangle(RULES_RECT, outline=text_color, width=1)
    
    rules_text = card_data.get('rules_text', '')
    y_text = RULES_RECT[1] + 5
    for line in text_wrap(rules_text, fonts["regular"], RULES_RECT[2] - RULES_RECT[0] - 10):
        if y_text < RULES_RECT[3] - 20:
            draw_formatted_text_line(card, (RULES_RECT[0] + 5, y_text), line, fonts["regular"], fonts["bold"], text_color, energy_icons)
            y_text += 20
        
    separator_y = RULES_RECT[3] + 10
    draw.line((30, separator_y, CARD_WIDTH - 30, separator_y), fill=text_color, width=1)
    
    flavor_text = card_data.get('flavor_text', '')
    y_text = separator_y + 10
    for line in text_wrap(flavor_text, fonts["italic"], CARD_WIDTH - 60):
        if y_text < CARD_HEIGHT - 40:
            draw_formatted_text_line(card, (30, y_text), line, fonts["italic"], fonts["bold_italic"], text_color, energy_icons)
            y_text += 18

    if card_data.get('type') == 'Character':
        stats_text = f"{card_data.get('reiatsu', '0')} / {card_data.get('genryu', '0')}"
        text_bbox = draw.textbbox((0,0), stats_text, font=fonts["stats"])
        stats_width = text_bbox[2] - text_bbox[0]
        draw.text((CARD_WIDTH - 30 - stats_width, CARD_HEIGHT - 45), stats_text, fill=text_color, font=fonts["stats"])
        
    return card

# --- GUI Application ---

class CardEditorApp:
    def __init__(self, root):
        self.root = root; self.root.title("Bleach Soul Deck - Card Editor"); self.root.geometry("1300x850")
        self.cards_data = []; self.current_card_index = -1
        self.fonts = get_fonts("Arial"); self.card_preview_pil_image = None; self.card_preview_photo = None
        self.art_controls, self.bg_controls, self.color_buttons, self.energy_text_controls = {}, {}, {}, {}
        self.apply_faction_theme = tk.BooleanVar(value=True)
        self.energy_icons = self._load_energy_icons()
        self._setup_menu(); self._setup_layout()

    def _load_energy_icons(self):
        icons = {}
        all_mappings = {**ENERGY_MAPPING, "N": "energy_neutral.png"}
        for code, filename in all_mappings.items():
            try:
                path = os.path.join(ENERGY_ICON_DIR, filename)
                icons[code] = Image.open(path).convert("RGBA")
                print(f"Loaded icon: {path}")
            except Exception as e:
                print(f"Warning: Energy icon not found at {path}: {e}")
        return icons

    def _setup_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Load JSON", command=self._load_json)
        file_menu.add_command(label="Save JSON", command=self._save_json)
        file_menu.add_separator()
        file_menu.add_command(label="Update Energy Icons on All Cards", command=self._update_all_energies)
        file_menu.add_command(label="Update All Card Backgrounds", command=self._update_all_card_backgrounds)
        file_menu.add_separator()
        file_menu.add_command(label="Export Current Card...", command=self._export_card)
        file_menu.add_command(label="Export All Cards...", command=self._export_all_cards)
        file_menu.add_separator(); file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menubar)

    def _setup_layout(self):
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        left_pane = ttk.PanedWindow(main_pane, orient=tk.VERTICAL)
        main_pane.add(left_pane, weight=1)
        list_frame = ttk.Frame(left_pane, padding=5); left_pane.add(list_frame, weight=1)
        controls_frame_container = ttk.Frame(left_pane, padding=10); left_pane.add(controls_frame_container, weight=3)
        self.preview_frame = ttk.Frame(main_pane, padding=5); main_pane.add(self.preview_frame, weight=1)
        self._setup_list_pane(list_frame)
        self._setup_controls_pane(controls_frame_container)
        self._setup_preview_pane()

    def _setup_list_pane(self, parent):
        parent.grid_rowconfigure(0, weight=1); parent.grid_columnconfigure(0, weight=1)
        self.card_listbox = tk.Listbox(parent, selectmode=tk.SINGLE)
        self.card_listbox.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=5)
        self.card_listbox.bind("<<ListboxSelect>>", self._on_card_select)
        ttk.Button(parent, text="New Card", command=self._new_card).grid(row=1, column=0, sticky="ew", padx=2)
        ttk.Button(parent, text="Delete Card", command=self._delete_card).grid(row=1, column=1, sticky="ew", padx=2)

    def _setup_controls_pane(self, parent):
        parent.grid_rowconfigure(0, weight=1); parent.grid_columnconfigure(0, weight=1)
        controls_canvas = tk.Canvas(parent); scrollbar = ttk.Scrollbar(parent, orient="vertical", command=controls_canvas.yview)
        scrollable_frame = ttk.Frame(controls_canvas)
        scrollable_frame.bind("<Configure>", lambda e: controls_canvas.configure(scrollregion=controls_canvas.bbox("all")))
        controls_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        controls_canvas.configure(yscrollcommand=scrollbar.set)
        controls_canvas.grid(row=0, column=0, sticky='nsew'); scrollbar.grid(row=0, column=1, sticky='ns')

        self.fields = {}
        fields_to_create = [("ID", "id", "entry"), ("Name", "name", "entry"), ("Subtitle", "subtitle", "entry"), ("Cost", "cost", "entry"), ("Type", "type", "combo", ["Character", "Technique", "Equipment", "Field", "Spiritual Energy"]), ("Subtypes", "subtypes", "entry"), ("Faction", "faction", "combo", list(FACTION_COLORS.keys())), ("Tier", "tier", "entry"), ("Reiatsu", "reiatsu", "entry"), ("Genryu", "genryu", "entry"), ("Rules Text", "rules_text", "text"), ("Flavor Text", "flavor_text", "text")]
        
        row = 0
        for label, key, w_type, *opts in fields_to_create:
            ttk.Label(scrollable_frame, text=label + ":").grid(row=row, column=0, sticky="ne", pady=2, padx=5)
            container = scrollable_frame
            if key in ['rules_text', 'flavor_text']:
                container = ttk.Frame(scrollable_frame); container.grid(row=row, column=1, columnspan=2, sticky="ew")
                ttk.Button(container, text="B", width=2, command=lambda k=key: self._toggle_bold(k)).pack(side=tk.RIGHT, anchor='n', padx=2)
            
            if key == 'faction':
                container = ttk.Frame(scrollable_frame); container.grid(row=row, column=1, columnspan=2, sticky="ew")
                widget = ttk.Combobox(container, values=opts[0], state="readonly")
                widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
                ttk.Checkbutton(container, text="Apply Theme", variable=self.apply_faction_theme).pack(side=tk.LEFT, padx=5)
            elif w_type == "entry": widget = ttk.Entry(container)
            elif w_type == "combo": widget = ttk.Combobox(container, values=opts[0], state="readonly")
            elif w_type == "text": widget = tk.Text(container, height=5, wrap="word", relief="solid", borderwidth=1)
            
            if key not in ['faction', 'rules_text', 'flavor_text']: widget.grid(row=row, column=1, columnspan=2, sticky="ew", pady=2, padx=5)
            else: widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
            self.fields[key] = widget; row += 1
        
        self.fields['faction'].bind("<<ComboboxSelected>>", self._apply_faction_colors)
        color_frame = self._create_color_controls(scrollable_frame, "Color Scheme", row); row+=1
        
        img_frame = ttk.Frame(scrollable_frame); img_frame.grid(row=row, column=0, columnspan=3, pady=5, sticky="w", padx=5)
        ttk.Button(img_frame, text="Select Artwork...", command=lambda: self._select_image('artwork_path')).pack(side=tk.LEFT, padx=5)
        ttk.Button(img_frame, text="Select Art BG...", command=lambda: self._select_image('background_path')).pack(side=tk.LEFT, padx=5)
        ttk.Button(img_frame, text="Select Card BG...", command=lambda: self._select_image('card_background_path')).pack(side=tk.LEFT, padx=5)
        ttk.Button(img_frame, text="Select Card Border...", command=lambda: self._select_image('card_border_path')).pack(side=tk.LEFT, padx=5)
        row += 1
        
        self.art_controls = self._create_art_controls(scrollable_frame, "Artwork Controls", "artwork", row); row +=1
        self.bg_controls = self._create_art_controls(scrollable_frame, "Artwork BG Controls", "background", row); row +=1
        self.energy_text_controls = self._create_art_controls(scrollable_frame, "Energy Text Controls", "energy_text", row, range=(-25, 25)); row += 1
        ttk.Button(scrollable_frame, text="Update Preview / Save Details", command=self._update_card_from_fields).grid(row=row, column=0, columnspan=3, pady=10)
        
    def _setup_preview_pane(self):
        self.card_preview_label = ttk.Label(self.preview_frame, text="Card Preview", relief="solid", anchor="center")
        self.card_preview_label.pack(fill=tk.BOTH, expand=True)
        self.preview_frame.bind("<Configure>", self._on_preview_resize)

    def _toggle_bold(self, key):
        widget = self.fields.get(key)
        if not widget or not isinstance(widget, tk.Text): return
        try:
            start, end = widget.tag_ranges(tk.SEL)
            selected_text = widget.get(start, end)
            if selected_text.startswith("<b>") and selected_text.endswith("</b>"): new_text = selected_text[3:-4]
            else: new_text = f"<b>{re.sub(r'</?b>', '', selected_text)}</b>"
            widget.delete(start, end); widget.insert(start, new_text)
        except tk.TclError: pass 

    def _create_color_controls(self, parent, title, start_row):
        frame = ttk.LabelFrame(parent, text=title, padding=5); frame.grid(row=start_row, column=0, columnspan=3, pady=5, sticky="ew", padx=5)
        ttk.Button(frame, text="Outer Border", command=lambda: self._choose_color('border_color')).grid(row=0, column=0, padx=5)
        ttk.Button(frame, text="Background", command=lambda: self._choose_color('background_color')).grid(row=0, column=1, padx=5)
        ttk.Button(frame, text="Text", command=lambda: self._choose_color('text_color')).grid(row=0, column=2, padx=5)

    def _create_art_controls(self, parent, title, prefix, start_row, range=(-300, 300)):
        controls = {}; frame = ttk.LabelFrame(parent, text=title, padding=5); frame.grid(row=start_row, column=0, columnspan=3, pady=5, sticky="ew", padx=5)
        frame.grid_columnconfigure(1, weight=1)
        scale_var = tk.DoubleVar(value=1.0)
        x_var = tk.IntVar(value=0)
        y_var = tk.IntVar(value=0)
        controls[f'{prefix}_scale'] = scale_var
        controls[f'{prefix}_x'] = x_var
        controls[f'{prefix}_y'] = y_var
        
        if "text" not in prefix:
            ttk.Label(frame, text="Scale:").grid(row=0, column=0, sticky="w"); ttk.Scale(frame, from_=0.1, to=5.0, orient=tk.HORIZONTAL, variable=scale_var).grid(row=0, column=1, sticky="ew"); ttk.Entry(frame, textvariable=scale_var, width=5).grid(row=0, column=2, padx=2)
        
        ttk.Label(frame, text="X Offset:").grid(row=1, column=0, sticky="w"); ttk.Scale(frame, from_=range[0], to=range[1], orient=tk.HORIZONTAL, variable=x_var).grid(row=1, column=1, sticky="ew"); ttk.Entry(frame, textvariable=x_var, width=5).grid(row=1, column=2, padx=2)
        ttk.Label(frame, text="Y Offset:").grid(row=2, column=0, sticky="w"); ttk.Scale(frame, from_=range[0], to=range[1], orient=tk.HORIZONTAL, variable=y_var).grid(row=2, column=1, sticky="ew"); ttk.Entry(frame, textvariable=y_var, width=5).grid(row=2, column=2, padx=2)
        return controls

    def _load_json(self):
        filepath = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")], initialdir=SCRIPT_DIR, title="Open Card Data")
        if not filepath: return
        try:
            with open(filepath, 'r', encoding='utf-8') as f: self.cards_data = json.load(f)
            self._populate_card_list(); messagebox.showinfo("Success", f"Loaded {len(self.cards_data)} cards.")
        except Exception as e: messagebox.showerror("Error", f"Failed to load JSON.\nError: {e}")

    def _save_json(self):
        if not self.cards_data: return messagebox.showwarning("Warning", "No card data to save.")
        self._update_card_from_fields(silent=True)
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")], initialdir=SCRIPT_DIR, title="Save Card Data")
        if not filepath: return
        try:
            with open(filepath, 'w', encoding='utf-8') as f: json.dump(self.cards_data, f, indent=4)
            messagebox.showinfo("Success", f"Saved {len(self.cards_data)} cards.")
        except Exception as e: messagebox.showerror("Error", f"Failed to save file.\nError: {e}")

    def _export_card(self):
        if self.current_card_index < 0: return messagebox.showwarning("Warning", "No card selected.")
        self._update_card_from_fields(silent=True)
        card_data = self.cards_data[self.current_card_index]; card_id = card_data.get('id', 'card')
        if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
        filepath = filedialog.asksaveasfilename(initialdir=OUTPUT_DIR, initialfile=f"{card_id}.png", defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if not filepath: return
        try: create_card_image(card_data, self.fonts, self.energy_icons).save(filepath); messagebox.showinfo("Success", f"Card exported to:\n{filepath}")
        except Exception as e: messagebox.showerror("Export Error", f"Could not export card.\nError: {e}")

    def _export_all_cards(self):
        if not self.cards_data: return messagebox.showwarning("Warning", "No cards to export.")
        if not messagebox.askyesno("Confirm Export", f"Export all {len(self.cards_data)} cards?"): return
        if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
        errors = []
        for i, card_data in enumerate(self.cards_data):
            try: create_card_image(card_data, self.fonts, self.energy_icons).save(os.path.join(OUTPUT_DIR, f"{card_data.get('id', i)}.png"))
            except Exception as e: errors.append(f"'{card_data.get('name', 'N/A')}': {e}")
        if errors: messagebox.showwarning("Export Complete", f"Finished with {len(errors)} errors.")
        else: messagebox.showinfo("Export Complete", f"Successfully exported {len(self.cards_data)} cards.")

    def _populate_card_list(self):
        self.card_listbox.delete(0, tk.END)
        for i, card in enumerate(self.cards_data): self.card_listbox.insert(tk.END, f"{i:03d}: {card.get('name', 'Unnamed')}")

    def _on_card_select(self, event):
        selection = event.widget.curselection()
        if not selection: return
        self.current_card_index = selection[0]; self._populate_fields()

    def _populate_fields(self):
        if not (0 <= self.current_card_index < len(self.cards_data)): self._clear_fields(); return
        card = self.cards_data[self.current_card_index]
        for key, widget in self.fields.items():
            value = card.get(key, "")
            if isinstance(widget, ttk.Entry): widget.delete(0, tk.END); widget.insert(0, str(value))
            elif isinstance(widget, ttk.Combobox): widget.set(str(value))
            elif isinstance(widget, tk.Text): widget.delete("1.0", tk.END); widget.insert("1.0", str(value))
        
        all_controls = {**self.art_controls, **self.bg_controls, **self.energy_text_controls}
        for key, var in all_controls.items():
            default = 1.0
            if '_x' in key or '_y' in key:
                default = 0
            var.set(card.get(key, default))
        self._update_preview()

    def _clear_fields(self):
        for key, widget in self.fields.items():
            if isinstance(widget, (ttk.Entry)): widget.delete(0, tk.END)
            elif isinstance(widget, ttk.Combobox): widget.set("")
            elif isinstance(widget, tk.Text): widget.delete("1.0", tk.END)
        
        all_controls = {**self.art_controls, **self.bg_controls, **self.energy_text_controls}
        for key, var in all_controls.items(): 
            var.set(0.0 if 'x' in key or 'y' in key else 1.0)
        self.card_preview_label.config(image=None); self.card_preview_photo = None
        self.card_preview_pil_image = None

    def _collect_data_from_fields(self):
        data = {};
        if self.current_card_index != -1: data = self.cards_data[self.current_card_index].copy()
        for key, w in self.fields.items(): data[key] = w.get() if isinstance(w, (ttk.Entry, ttk.Combobox)) else w.get("1.0", tk.END).strip()
        
        all_controls = {**self.art_controls, **self.bg_controls, **self.energy_text_controls}
        for key, var in all_controls.items(): 
            data[key] = var.get()

        if isinstance(tier_val := data.get('tier', ''), str) and tier_val.isdigit(): data['tier'] = int(tier_val)
        return data

    def _update_card_from_fields(self, silent=False):
        if self.current_card_index < 0: return
        updated_data = self._collect_data_from_fields()
        self.cards_data[self.current_card_index] = updated_data
        self.card_listbox.delete(self.current_card_index); self.card_listbox.insert(self.current_card_index, f"{self.current_card_index:03d}: {updated_data.get('name', 'Unnamed')}")
        self.card_listbox.selection_set(self.current_card_index)
        self._update_preview()
        if not silent: print(f"Updated preview for: {updated_data.get('name')}")

    def _update_all_energies(self):
        if not self.cards_data: return messagebox.showwarning("Warning", "No card data loaded.")
        for card_data in self.cards_data:
            cost_str = card_data.get("cost", "")
            energy_icons = {}
            generic_cost_str = ''.join(filter(str.isdigit, cost_str))
            specific_cost_str = ''.join(filter(str.isalpha, cost_str))
            
            if generic_cost_str:
                energy_icons['N'] = int(generic_cost_str) 
            
            for char in specific_cost_str:
                char = char.upper() 
                if char in ENERGY_MAPPING:
                    energy_icons[char] = energy_icons.get(char, 0) + 1
            
            card_data["energy_icons"] = energy_icons
        
        self._update_preview()
        messagebox.showinfo("Success", "Energy icons data updated for all cards. Save the JSON to keep changes.")
    
    def _update_all_card_backgrounds(self):
        if not self.cards_data: return messagebox.showwarning("Warning", "No card data loaded.")
        
        updated_count = 0
        for card_data in self.cards_data:
            card_type = card_data.get("type")
            card_faction = card_data.get("faction")
            
            bg_filename = None
            # Prioritize type-specific backgrounds first
            if card_type in BACKGROUND_MAPPING:
                bg_filename = BACKGROUND_MAPPING[card_type]
            # Fallback to faction-specific backgrounds
            elif card_faction in BACKGROUND_MAPPING:
                bg_filename = BACKGROUND_MAPPING[card_faction]
            
            if bg_filename:
                bg_path = os.path.join(BACKGROUND_DIR, bg_filename)
                if os.path.exists(bg_path):
                    card_data["card_background_path"] = bg_path
                    updated_count +=1
                else:
                    print(f"Warning: Background file not found for '{card_data.get('name')}': {bg_path}")
        
        self._update_preview()
        messagebox.showinfo("Success", f"Default backgrounds updated for {updated_count} cards. Save the JSON to keep changes.")

    def _update_preview(self):
        if self.current_card_index < 0: return
        try:
            self.card_preview_pil_image = create_card_image(self.cards_data[self.current_card_index], self.fonts, self.energy_icons)
            self._resize_and_display_preview()
        except Exception as e: 
            print(f"Preview Error: {e}")
            self.card_preview_label.config(image=None, text=f"Preview Error:\n{e}")

    def _on_preview_resize(self, event):
        self._resize_and_display_preview()

    def _resize_and_display_preview(self):
        if not self.card_preview_pil_image: self.card_preview_label.config(image=None); return
        container_width, container_height = self.preview_frame.winfo_width(), self.preview_frame.winfo_height()
        if container_width < 20 or container_height < 20: return
        aspect_ratio = CARD_WIDTH / CARD_HEIGHT
        new_width = container_width; new_height = int(new_width / aspect_ratio)
        if new_height > container_height: new_height = container_height; new_width = int(new_height * aspect_ratio)
        resized_pil_image = self.card_preview_pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self.card_preview_photo = ImageTk.PhotoImage(resized_pil_image)
        self.card_preview_label.config(image=self.card_preview_photo, text="")

    def _new_card(self):
        bg_color, text_color = FACTION_COLORS["Default"]
        new_card = {"id": str(uuid.uuid4())[:8], "name": "New Card", "type": "Character", "faction": "Default", "tier": 1, "artwork_path": "", "background_path": "", "artwork_scale": 1.0, "artwork_x": 0, "artwork_y": 0, "background_scale": 1.0, "background_x": 0, "background_y": 0, "background_color": bg_color, "text_color": text_color, "border_color": text_color, "card_background_path": "", "card_border_path": ""}
        self.cards_data.append(new_card); self._populate_card_list()
        self.card_listbox.selection_clear(0, tk.END); self.card_listbox.selection_set(tk.END)
        self.card_listbox.event_generate("<<ListboxSelect>>")

    def _delete_card(self):
        if self.current_card_index < 0: return messagebox.showwarning("Warning", "No card selected.")
        card_name = self.cards_data[self.current_card_index].get('name')
        if messagebox.askyesno("Confirm Delete", f"Delete '{card_name}'?"):
            self.cards_data.pop(self.current_card_index); self.current_card_index = -1
            self._clear_fields(); self._populate_card_list(); self._update_preview()

    def _select_image(self, path_key):
        if self.current_card_index < 0: return messagebox.showwarning("Warning", "Please select a card first.")
        
        initial_dir = SCRIPT_DIR
        if path_key == 'card_background_path':
            initial_dir = BACKGROUND_DIR
        elif path_key == 'card_border_path':
            initial_dir = BORDER_DIR
        elif path_key in ['artwork_path', 'background_path']:
            initial_dir = CARD_ART_DIR

        filepath = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg")], 
            initialdir=initial_dir,
            title=f"Select {path_key.replace('_', ' ').title()}"
        )
        if filepath: 
            self.cards_data[self.current_card_index][path_key] = filepath
            self._update_card_from_fields(silent=True) # Save the change and update
            self._update_preview()

    def _choose_color(self, color_key):
        if self.current_card_index < 0: return messagebox.showwarning("Warning", "Please select a card first.")
        color_code = colorchooser.askcolor(title=f"Choose {color_key.replace('_', ' ')}")
        if color_code and color_code[1]: self.cards_data[self.current_card_index][color_key] = color_code[1]; self._update_preview()
        
    def _apply_faction_colors(self, event):
        if self.current_card_index < 0: return
        if self.apply_faction_theme.get():
            faction = self.fields['faction'].get()
            if faction in FACTION_COLORS:
                bg, text = FACTION_COLORS[faction]
                card = self.cards_data[self.current_card_index]
                card['background_color'] = bg; card['text_color'] = text; card['border_color'] = text
                self._update_preview()

if __name__ == "__main__":
    root = tk.Tk()
    app = CardEditorApp(root)
    root.mainloop()

