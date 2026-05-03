import streamlit as st
import streamlit.components.v1 as components
import subprocess
import sys

st.set_page_config(page_title="MCP Visualizer", layout="wide")

st.title("MCP Flow Visualizer")
st.caption("Live sequence diagram — arrows appear as each interaction happens")

COLORS = {
    "User":      {"bg": "#E1F5EE", "border": "#0F6E56", "text": "#085041"},
    "client.py": {"bg": "#EEEDFE", "border": "#534AB7", "text": "#3C3489"},
    "server.py": {"bg": "#FAEEDA", "border": "#BA7517", "text": "#633806"},
    "ChromaDB":  {"bg": "#FAECE7", "border": "#993C1D", "text": "#712B13"},
    "Claude":    {"bg": "#F1EFE8", "border": "#5F5E5A", "text": "#2C2C2A"},
}

COMPONENTS = ["User", "client.py", "server.py", "ChromaDB", "Claude"]


def build_svg(steps, width=700):
    n = len(COMPONENTS)
    col_w = width // n
    row_height = 40
    header_h = 60
    total_h = header_h + max(len(steps), 1) * row_height + 40

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{total_h}">')

    # column headers
    for i, name in enumerate(COMPONENTS):
        cx = col_w * i + col_w // 2
        c = COLORS[name]
        x = cx - 52
        lines.append(f'''
        <rect x="{x}" y="8" width="104" height="36" rx="8"
              fill="{c["bg"]}" stroke="{c["border"]}" stroke-width="1.5"/>
        <text x="{cx}" y="31" text-anchor="middle" font-size="12"
              font-weight="600" fill="{c["text"]}"
              font-family="system-ui,sans-serif">{name}</text>
        ''')

    # lifelines
    for i in range(n):
        cx = col_w * i + col_w // 2
        lines.append(f'''
        <line x1="{cx}" y1="46" x2="{cx}" y2="{total_h - 10}"
              stroke="#CBD5E1" stroke-width="1" stroke-dasharray="4 4"/>
        ''')

    # arrows
    for idx, (frm, to, label) in enumerate(steps):
        y = header_h + idx * row_height + row_height // 2
        fi = COMPONENTS.index(frm)
        ti = COMPONENTS.index(to)
        x1 = col_w * fi + col_w // 2
        x2 = col_w * ti + col_w // 2
        color = COLORS[frm]["border"]
        going_right = x2 > x1
        ax = x2 - 8 if going_right else x2 + 8

        # source dot
        lines.append(f'<circle cx="{x1}" cy="{y}" r="4" fill="{color}"/>')

        # arrowhead marker
        lines.append(f'''
        <defs>
          <marker id="ah{idx}" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M2 1L8 5L2 9" fill="none" stroke="{color}"
              stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </marker>
        </defs>
        ''')

        # arrow line
        lines.append(f'''
        <line x1="{x1}" y1="{y}" x2="{ax}" y2="{y}"
              stroke="{color}" stroke-width="2"
              marker-end="url(#ah{idx})"/>
        ''')

        # label
        mid = (x1 + x2) // 2
        label_short = label if len(label) < 26 else label[:24] + "…"
        lw = len(label_short) * 6.8 + 16
        lx = mid - lw // 2
        bg = COLORS[frm]["bg"]
        lines.append(f'''
        <rect x="{lx}" y="{y - 14}" width="{lw}" height="14"
              rx="3" fill="{bg}" stroke="{color}" stroke-width="0.5"/>
        <text x="{mid}" y="{y - 3}" text-anchor="middle" font-size="9.5"
              font-weight="600" fill="{color}"
              font-family="system-ui,sans-serif">{label_short}</text>
        ''')

        # step number
        lines.append(f'''
        <text x="6" y="{y + 4}" font-size="9" fill="#94A3B8"
              font-family="system-ui,sans-serif">{idx + 1}</text>
        ''')

    lines.append('</svg>')
    return "\n".join(lines)


def wrap_svg(svg):
    return f'''
    <div style="background:white;border-radius:10px;
                border:0.5px solid #e2e8f0;padding:12px;
                overflow-x:auto;font-family:system-ui,sans-serif">
      {svg}
    </div>
    '''


def build_log_html(log_lines):
    return f'''
    <div style="font-family:system-ui,sans-serif;padding:4px">
      {"".join(log_lines)}
    </div>
    '''


# ── question form ────────────────────────────────────────
with st.form("q_form"):
    question = st.text_input(
        "Your question",
        placeholder="e.g. Do I need VPN to work remotely?",
        value="How many sick days do I get per year?"
    )
    submitted = st.form_submit_button("Run", type="primary", use_container_width=True)

# ── run ──────────────────────────────────────────────────
if submitted:
    if not question.strip():
        st.warning("Please type a question first.")
        st.stop()

    st.markdown("---")
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("**Sequence diagram**")
        diagram_slot = st.empty()

    with col_right:
        st.markdown("**Interaction log**")
        log_slot = st.empty()
        answer_slot = st.empty()

    steps = []
    log_lines = []

    # empty diagram to start
    with diagram_slot:
        components.html(wrap_svg(build_svg([])), height=120)

    process = subprocess.Popen(
        [sys.executable, "client.py", question],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    for line in process.stdout:
        line = line.strip()
        if not line:
            continue

        if line.startswith("STEP|"):
            parts = line.split("|", 3)
            if len(parts) == 4:
                frm, to, label = parts[1], parts[2], parts[3]
                steps.append((frm, to, label))

                # update diagram
                h = 60 + len(steps) * 40 + 60
                with diagram_slot:
                    components.html(wrap_svg(build_svg(steps)), height=h)

                # update log
                c = COLORS.get(frm, {})
                tc = COLORS.get(to, {})
                log_lines.append(f'''
                <div style="display:flex;align-items:center;gap:6px;
                     padding:5px 8px;border-radius:6px;margin-bottom:4px;
                     border-left:3px solid {c.get("border","#ccc")};
                     background:{c.get("bg","#f9f9f9")}">
                  <span style="font-size:10px;color:#94a3b8;min-width:14px">{len(steps)}</span>
                  <span style="font-size:11px;font-weight:600;
                        color:{c.get("border","#333")}">{frm}</span>
                  <span style="font-size:11px;color:#94a3b8">→</span>
                  <span style="font-size:11px;font-weight:600;
                        color:{tc.get("border","#333")}">{to}</span>
                  <span style="font-size:11px;color:#475569">{label}</span>
                </div>
                ''')
                with log_slot:
                    components.html(
                        build_log_html(log_lines),
                        height=min(44 * len(log_lines) + 16, 500)
                    )

        elif line.startswith("ANSWER|"):
            answer_slot.success("**Answer:** " + line[7:])

        elif line.startswith("ERROR|"):
            st.error("Error: " + line[6:])

    stderr_out = process.stderr.read()
    process.wait()
    if process.returncode != 0 and stderr_out:
        st.error("Check SERVER_PATH in client.py\n\n" + stderr_out[:300])