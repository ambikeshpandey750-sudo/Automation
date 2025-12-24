from google.oauth2 import service_account
from googleapiclient.discovery import build
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
from io import BytesIO
import string
import textwrap

# ============================
# OWNER VALIDATION
# ============================
def _validate_owner():
    name = "".join(chr(c) for c in [65,109,98,105,107,101,115,104])
    if name != "Ambikesh":
        raise ValueError("Unauthorized modification detected")
    return name

OWNER_NAME = _validate_owner()

# ============================
# UTILITIES
# ============================
def col_letter_to_index(letter):
    idx = 0
    for ch in (letter or "").upper():
        if ch in string.ascii_uppercase:
            idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1 if idx else 0

def parse_color(c, default="#FFFFFF"):
    if not c:
        return default
    return "#{:02X}{:02X}{:02X}".format(
        int(c.get("red", 0) * 255),
        int(c.get("green", 0) * 255),
        int(c.get("blue", 0) * 255),
    )

def darken_color(hex_color, factor=0.80):
    """factor < 1 => darker"""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    r = int(r * factor)
    g = int(g * factor)
    b = int(b * factor)

    return "#{:02X}{:02X}{:02X}".format(r, g, b)

def parse_border(b):
    if not b:
        return None
    return {
        "color": parse_color(b.get("color"), "#000000"),
        "width": max(0.6, b.get("width", 1)),
    }

def resolve_fontsize(sheet_size, text, width, merged=False):
    if sheet_size:
        return sheet_size * 0.9
    size = (width * (16 if merged else 14)) / max(1, len(str(text)))
    return max(10, min(18, size))

def wrap_text_to_width(text, cell_width):
    if not text:
        return ""
    max_chars = max(1, int(cell_width * 6))
    return "\n".join(textwrap.wrap(str(text), max_chars))

def draw_borders(ax, x, y, w, h, fmt):
    if fmt["border_top"]:
        ax.plot([x, x + w], [y + h, y + h],
                color=fmt["border_top"]["color"], lw=fmt["border_top"]["width"])
    if fmt["border_bottom"]:
        ax.plot([x, x + w], [y, y],
                color=fmt["border_bottom"]["color"], lw=fmt["border_bottom"]["width"])
    if fmt["border_left"]:
        ax.plot([x, x], [y, y + h],
                color=fmt["border_left"]["color"], lw=fmt["border_left"]["width"])
    if fmt["border_right"]:
        ax.plot([x + w, x + w], [y, y + h],
                color=fmt["border_right"]["color"], lw=fmt["border_right"]["width"])

# ============================
# MAIN FUNCTION
# ============================
def Generate_Snapshot(config):

    SERVICE_ACCOUNT_FILE = "/Users/ambikeshpandey/Desktop/GDriveKey.json"
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    range_name = (
        f'{config["sheet_name"]}!'
        f'{config.get("column_start","")}{config.get("row_start","")}:'
        f'{config.get("column_end","")}{config.get("row_end","")}'
    )

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=creds)

    meta = service.spreadsheets().get(
        spreadsheetId=config["spreadsheet_id"],
        ranges=[range_name],
        includeGridData=True
    ).execute()

    sheet = meta["sheets"][0]
    data = sheet["data"][0]
    grid_data = data.get("rowData", [])
    merges = sheet.get("merges", [])

    row_meta = data.get("rowMetadata", [])
    col_meta = data.get("columnMetadata", [])

    hidden_rows = {i for i, r in enumerate(row_meta) if r.get("hiddenByUser")}
    hidden_cols = {i for i, c in enumerate(col_meta) if c.get("hiddenByUser")}

    visible_col_map = {}
    v_idx = 0
    for i in range(len(col_meta)):
        if i not in hidden_cols:
            visible_col_map[i] = v_idx
            v_idx += 1

    formatted_data, formatting = [], []

    for r_idx, row in enumerate(grid_data):
        if r_idx in hidden_rows:
            continue

        rv, rf = [], []
        for c_idx, cell in enumerate(row.get("values", [])):
            if c_idx in hidden_cols:
                continue

            rv.append(cell.get("formattedValue", "") or "")
            fmt = cell.get("userEnteredFormat", {})
            txt = fmt.get("textFormat", {})
            b = fmt.get("borders", {})

            rf.append({
                "bg": parse_color(fmt.get("backgroundColor")),
                "bold": txt.get("bold", False),
                "font_size": txt.get("fontSize"),
                "font_color": parse_color(txt.get("foregroundColor"), "#000000"),
                "wrap": fmt.get("wrapStrategy") == "WRAP",
                "border_top": parse_border(b.get("top")),
                "border_bottom": parse_border(b.get("bottom")),
                "border_left": parse_border(b.get("left")),
                "border_right": parse_border(b.get("right")),
            })

        formatted_data.append(rv)
        formatting.append(rf)

    df = pd.DataFrame(formatted_data)
    n_rows, n_cols = df.shape

    col_widths = [
        max(1.6, max(len(str(df.iat[r, c])) for r in range(n_rows)) * 0.15)
        for c in range(n_cols)
    ]

    dpi = 300

    fig, ax = plt.subplots(
        figsize=(sum(col_widths), max(1, n_rows * 0.42)),
        constrained_layout=True
    )
    ax.axis("off")
    ax.set_xlim(0, sum(col_widths))
    ax.set_ylim(0, n_rows)
    ax.margins(0)

    row_offset = config.get("row_start", 1) - 1
    col_offset = col_letter_to_index(config.get("column_start"))

    merges_map, covered = {}, set()

    for m in merges:
        sr = m["startRowIndex"] - row_offset
        er = m["endRowIndex"] - row_offset
        sc0 = m["startColumnIndex"] - col_offset
        ec0 = m["endColumnIndex"] - col_offset

        visible_cols = [visible_col_map[c] for c in range(sc0, ec0) if c in visible_col_map]
        if not visible_cols or sr < 0 or er > n_rows:
            continue

        sc, ec = min(visible_cols), max(visible_cols) + 1
        merges_map[(sr, sc)] = (er, ec)

        for r in range(sr, er):
            for c in range(sc, ec):
                if (r, c) != (sr, sc):
                    covered.add((r, c))

    for i in range(n_rows):
        x, j = 0, 0
        while j < n_cols:
            if (i, j) in covered:
                x += col_widths[j]
                j += 1
                continue

            fmt = formatting[i][j]
            if (i, j) in merges_map:
                er, ec = merges_map[(i, j)]
                w = sum(col_widths[j:ec])
                h = er - i
                y = n_rows - i - h
            else:
                w, h = col_widths[j], 1
                y = n_rows - i - 1

            ax.add_patch(
                patches.Rectangle((x, y), w, h, facecolor=fmt["bg"], edgecolor="none")
            )
            draw_borders(ax, x, y, w, h, fmt)

            text_val = str(df.iat[i, j])
            if fmt["wrap"]:
                text_val = wrap_text_to_width(text_val, w)

            ax.text(
                x + w / 2,
                y + h / 2,
                text_val,
                ha="center",
                va="center",
                fontsize=resolve_fontsize(fmt["font_size"], text_val, w, h > 1),
                color=darken_color(fmt["font_color"], 0.89),  # 🔥 DARKER TEXT
                weight="bold" if fmt["bold"] else "medium",
                wrap=True,
            )

            x += w
            j = ec if (i, j) in merges_map else j + 1
    ax.text(
        0.99, -0.03,
        f"Snapshot Generated by {OWNER_NAME}",
        ha="right", va="top", fontsize=9, alpha=0.7,
        transform=ax.transAxes
    )

    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=dpi, bbox_inches="tight", pad_inches=0)
    plt.close()

    buffer.seek(0)
    return Image.open(buffer)
