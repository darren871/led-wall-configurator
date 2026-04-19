import streamlit as st
import matplotlib
matplotlib.use('Agg') # CRITICAL FIX: Forces Matplotlib into a safe, non-hanging background mode
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
from matplotlib.backends.backend_pdf import PdfPages
import io
import json
import os
import string
from PIL import Image
from datetime import datetime

# --- INITIAL SETUP & STATE ---
st.set_page_config(page_title="EPL - LED Wall Configurator", layout="wide")

# BRANDING
LOGO_FILENAME = "epl_logo.png"

# Initialize Session State
if 'sys_state' not in st.session_state:
    st.session_state.sys_state = {
        'project_name': "Unnamed_Project",
        'panel': "Generic P3.9 (500x500mm)",
        'processor': "Novastar VX400 (4 Ports)",
        'width': 5.0,
        'height': 3.0,
        'rigging': "Bottom (Ground Stacked)",
        'data_dir': "Vertical (Columns)",
        'use_backups': True,
        'auto_opt': True,
        'loom_strat': "Evenly Balance Load",
        'voltage': 230,
        'cable_type': "16A CEEFORM to PowerCON/True1 (16A Limit)",
        'distro_phase': "3-Phase (415V)",
        'distro_amps': 63
    }

raw_proj_name = st.session_state.sys_state.get('project_name', 'LED_Wall_Config')
safe_proj_name = "".join([c if c.isalnum() or c in " -_" else "_" for c in raw_proj_name]).strip()

# --- 1. THE DATABASES (JSON) ---
DB_FILE_PANELS = "panels.json"
DB_FILE_PROCESSORS = "processors.json"
DB_FILE_PROJECTS = "projects.json"

default_panels = {
    "Absen Polaris PL2.5 Pro (500x500mm)": {"width_mm": 500, "height_mm": 500, "res_w": 200, "res_h": 200, "max_power_w": 160, "weight_kg": 8.7},
    "Absen Polaris PL3.9 Pro (500x500mm)": {"width_mm": 500, "height_mm": 500, "res_w": 128, "res_h": 128, "max_power_w": 150, "weight_kg": 8.7},
    "Unilumin UpadIV 2.6 (500x500mm)": {"width_mm": 500, "height_mm": 500, "res_w": 192, "res_h": 192, "max_power_w": 160, "weight_kg": 6.3},
    "Unilumin UpadIII 3.9 (500x500mm)": {"width_mm": 500, "height_mm": 500, "res_w": 128, "res_h": 128, "max_power_w": 150, "weight_kg": 9.2},
    "Gloshine Legend LS3.9 (500x1000mm)": {"width_mm": 500, "height_mm": 1000, "res_w": 128, "res_h": 256, "max_power_w": 300, "weight_kg": 12.5},
    "Gloshine ZS2.6 (500x500mm)": {"width_mm": 500, "height_mm": 500, "res_w": 192, "res_h": 192, "max_power_w": 160, "weight_kg": 8.0},
    "ROE Black Pearl BP2V2 (500x500mm)": {"width_mm": 500, "height_mm": 500, "res_w": 176, "res_h": 176, "max_power_w": 140, "weight_kg": 9.3},
    "ROE Carbon CB5 (600x1200mm)": {"width_mm": 600, "height_mm": 1200, "res_w": 104, "res_h": 208, "max_power_w": 300, "weight_kg": 14.0},
    "Pioneer LED P3.91 Outdoor (500x500mm)": {"width_mm": 500, "height_mm": 500, "res_w": 128, "res_h": 128, "max_power_w": 200, "weight_kg": 8.5},
    "Generic P3.9 (500x500mm)": {"width_mm": 500, "height_mm": 500, "res_w": 128, "res_h": 128, "max_power_w": 150, "weight_kg": 8.5}
}

default_processors = {
    "Novastar VX400 (4 Ports)": {"ports": 4},
    "Novastar VX600 (6 Ports)": {"ports": 6},
    "Novastar VX1000 (10 Ports)": {"ports": 10},
    "Novastar MCTRL4K (16 Ports)": {"ports": 16},
    "Novastar NovaPro UHD Jr (16 Ports)": {"ports": 16},
    "Brompton Tessera S8 (8 Ports)": {"ports": 8},
    "Brompton Tessera SX40 (4x 10G Ports)": {"ports": 4} 
}

def load_json(file_path, default_data):
    if os.path.exists(file_path):
        with open(file_path, "r") as file: return json.load(file)
    else:
        with open(file_path, "w") as file: json.dump(default_data, file, indent=4)
        return default_data

def save_json(file_path, data):
    with open(file_path, "w") as file: json.dump(data, file, indent=4)

panel_database = load_json(DB_FILE_PANELS, default_panels)
processor_database = load_json(DB_FILE_PROCESSORS, default_processors)
project_database = load_json(DB_FILE_PROJECTS, {})

# --- SIDEBAR: PROJECT & INVENTORY MANAGEMENT ---
with st.sidebar:
    if os.path.exists(LOGO_FILENAME):
        st.image(LOGO_FILENAME, use_container_width=True)
        
    st.header("💾 Project Management")
    
    proj_save_name = st.text_input("Project Name to Save", value=st.session_state.sys_state.get('project_name', ''))
    if st.button("Save Current Project"):
        if proj_save_name:
            st.session_state.sys_state['project_name'] = proj_save_name
            project_database[proj_save_name] = st.session_state.sys_state
            save_json(DB_FILE_PROJECTS, project_database)
            st.success(f"Project '{proj_save_name}' saved!")
            st.rerun()
        else:
            st.error("Please enter a project name.")

    if project_database:
        proj_load_name = st.selectbox("Load Saved Project", options=list(project_database.keys()))
        if st.button("Load Project"):
            st.session_state.sys_state = project_database[proj_load_name]
            st.session_state.sys_state['project_name'] = proj_load_name
            st.success(f"Loaded '{proj_load_name}'!")
            st.rerun()
            
    st.divider()
    st.header("⚙️ Inventory Settings")
    with st.expander("➕ Add Custom Panel"):
        with st.form("new_panel_form"):
            new_name = st.text_input("Panel Name")
            c1, c2 = st.columns(2)
            new_w = c1.number_input("Width (mm)", min_value=100, value=500, step=100)
            new_h = c2.number_input("Height (mm)", min_value=100, value=500, step=100)
            c3, c4 = st.columns(2)
            new_res_w = c3.number_input("Pixels Wide", min_value=10, value=128, step=8)
            new_res_h = c4.number_input("Pixels High", min_value=10, value=128, step=8)
            c5, c6 = st.columns(2)
            new_power = c5.number_input("Max Power (W)", min_value=10, value=150, step=10)
            new_weight = c6.number_input("Weight (kg)", min_value=1.0, value=8.5, step=0.5)
            if st.form_submit_button("Save Panel"):
                if new_name:
                    panel_database[new_name] = {"width_mm": new_w, "height_mm": new_h, "res_w": new_res_w, "res_h": new_res_h, "max_power_w": new_power, "weight_kg": new_weight}
                    save_json(DB_FILE_PANELS, panel_database)
                    st.success(f"Added {new_name}!"); st.rerun()

    with st.expander("➕ Add Custom Processor"):
        with st.form("new_processor_form"):
            new_proc_name = st.text_input("Processor Name")
            new_proc_ports = st.number_input("Number of Output Ports", min_value=1, value=4, step=1)
            if st.form_submit_button("Save Processor"):
                if new_proc_name:
                    processor_database[new_proc_name] = {"ports": new_proc_ports}
                    save_json(DB_FILE_PROCESSORS, processor_database)
                    st.success(f"Added {new_proc_name}!"); st.rerun()

def get_index(options_list, match_value):
    try: return options_list.index(match_value)
    except ValueError: return 0

# --- 2. GENERAL INPUTS ---
st.title("EPL - LED Video Wall Configurator")
st.header("1. Hardware & Dimensions")

col_hw1, col_hw2 = st.columns(2)

with col_hw1: 
    panel_brands = ["All"] + sorted(list(set([k.split(' ')[0] for k in panel_database.keys()])))
    saved_panel = st.session_state.sys_state.get('panel', list(panel_database.keys())[0])
    default_brand = saved_panel.split(' ')[0] if saved_panel in panel_database else "All"
    
    sel_panel_brand = st.selectbox("Filter Panels by Manufacturer", options=panel_brands, index=get_index(panel_brands, default_brand))
    filtered_panels = [k for k in panel_database.keys() if sel_panel_brand == "All" or k.startswith(sel_panel_brand)]
    sel_panel = st.selectbox("Select Panel Type", options=filtered_panels, index=get_index(filtered_panels, saved_panel))
    st.session_state.sys_state['panel'] = sel_panel
    
with col_hw2: 
    proc_brands = ["All"] + sorted(list(set([k.split(' ')[0] for k in processor_database.keys()])))
    saved_proc = st.session_state.sys_state.get('processor', list(processor_database.keys())[0])
    default_proc_brand = saved_proc.split(' ')[0] if saved_proc in processor_database else "All"
    
    sel_proc_brand = st.selectbox("Filter Processors by Manufacturer", options=proc_brands, index=get_index(proc_brands, default_proc_brand))
    filtered_procs = [k for k in processor_database.keys() if sel_proc_brand == "All" or k.startswith(sel_proc_brand)]
    sel_proc = st.selectbox("Select Processor", options=filtered_procs, index=get_index(filtered_procs, saved_proc))
    st.session_state.sys_state['processor'] = sel_proc

col1, col2 = st.columns(2)
with col1:
    target_w = st.number_input("Target Width (meters)", min_value=0.5, value=float(st.session_state.sys_state['width']), step=0.5)
    st.session_state.sys_state['width'] = target_w
with col2:
    optimize_ratio = st.toggle("Snap to Standard Aspect Ratio", value=False)
    if optimize_ratio:
        target_ratio_str = st.selectbox("Target Aspect Ratio", ["16:9", "4:3", "1:1", "21:9"])
    else:
        target_h = st.number_input("Target Height (meters)", min_value=0.5, value=float(st.session_state.sys_state['height']), step=0.5)
        st.session_state.sys_state['height'] = target_h

# --- 3. BASE CALCULATIONS ---
panel_specs = panel_database[sel_panel]
processor_specs = processor_database[sel_proc]
processor_max_ports = processor_specs["ports"]

panel_width_m = panel_specs["width_mm"] / 1000
panel_height_m = panel_specs["height_mm"] / 1000
panel_weight_kg = panel_specs.get("weight_kg", 10.0) 

columns = math.ceil(target_w / panel_width_m)

if optimize_ratio:
    tr_w, tr_h = map(int, target_ratio_str.split(":"))
    ideal_height_m = (columns * panel_width_m) * (tr_h / tr_w)
    rows = max(1, round(ideal_height_m / panel_height_m))
else:
    rows = math.ceil(target_h / panel_height_m)

total_panels = columns * rows
actual_width_m = columns * panel_width_m
actual_height_m = rows * panel_height_m
total_weight_kg = total_panels * panel_weight_kg
actual_ratio_decimal = actual_width_m / actual_height_m
canvas_res_w = columns * panel_specs["res_w"]
canvas_res_h = rows * panel_specs["res_h"]

PORT_LIMIT = 655360 
pixels_per_panel = panel_specs["res_w"] * panel_specs["res_h"]
panels_per_port_max = PORT_LIMIT // pixels_per_panel 

# --- 4. BUILD REQUIREMENTS METRICS ---
st.header("2. Build Requirements")
metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
metric_col1.metric("Total Panels", f"{total_panels}")
metric_col2.metric("Grid Layout", f"{columns} W x {rows} H")
metric_col3.metric("Actual Build Size", f"{actual_width_m:.2f}m x {actual_height_m:.2f}m")
metric_col4.metric("Total Weight", f"{total_weight_kg:.1f} kg")
st.info(f"📐 **Calculated Aspect Ratio:** {actual_ratio_decimal:.2f}:1 | **Canvas Resolution:** {canvas_res_w} x {canvas_res_h} px")

# --- 5. CABLING CONFIGURATOR & OPTIMIZER ---
st.header("3. Data Cabling Configuration")
col_c1, col_c2 = st.columns([1, 1.5])

with col_c1:
    st.subheader("Controls")
    auto_opt = st.toggle("✨ Auto-Find Best Configuration", value=st.session_state.sys_state['auto_opt'], help="Simulates paths to find the most efficient and cleanly balanced setup.")
    st.session_state.sys_state['auto_opt'] = auto_opt
    
    rigging = st.radio("Rigging Origin", options=["Bottom (Ground Stacked)", "Top (Flown)"], horizontal=True, index=0 if "Bottom" in st.session_state.sys_state['rigging'] else 1)
    st.session_state.sys_state['rigging'] = rigging
    
    use_bu = st.toggle("Use Backup Data Lines", value=st.session_state.sys_state['use_backups'])
    st.session_state.sys_state['use_backups'] = use_bu
    
    if not auto_opt:
        data_dir = st.radio("Data Direction", options=["Vertical (Columns)", "Horizontal (Rows)"], horizontal=True, index=0 if "Vertical" in st.session_state.sys_state['data_dir'] else 1)
        st.session_state.sys_state['data_dir'] = data_dir
        
        loom_opts = ["Maximize Port Capacity (Even chunks only)", "Force 4-Line Groups", "Force 2-Line Groups", "Evenly Balance Load"]
        loom_strat = st.selectbox("Chunking Strategy", loom_opts, index=get_index(loom_opts, st.session_state.sys_state['loom_strat']))
        st.session_state.sys_state['loom_strat'] = loom_strat
    
is_flown = "Top" in rigging
ports_per_string = 2 if use_bu else 1

def simulate_routing(is_horiz, strategy):
    line_count = rows if is_horiz else columns
    panels_per_line = columns if is_horiz else rows
    max_lines_per_port = panels_per_port_max // panels_per_line
    if max_lines_per_port == 0: return float('inf'), float('inf'), float('inf'), float('inf'), [] 
        
    test_loads = []
    if strategy == "Evenly Balance Load":
        t_ports = math.ceil(line_count / max_lines_per_port)
        base = line_count // t_ports
        rem = line_count % t_ports
        for i in range(t_ports): test_loads.append((base + (1 if i < rem else 0)) * panels_per_line)
    else:
        if strategy == "Force 4-Line Groups": t_lines = min(4, max_lines_per_port)
        elif strategy == "Force 2-Line Groups": t_lines = min(2, max_lines_per_port)
        else: t_lines = max_lines_per_port

        if t_lines > 1 and t_lines % 2 != 0: t_lines -= 1
        rem_lines = line_count
        while rem_lines > 0:
            if rem_lines >= t_lines:
                test_loads.append(t_lines * panels_per_line)
                rem_lines -= t_lines
            else:
                if rem_lines > 1 and rem_lines % 2 != 0: test_loads.append((rem_lines - 1) * panels_per_line); rem_lines -= (rem_lines - 1)
                else: test_loads.append(rem_lines * panels_per_line); rem_lines = 0
                    
    stranded_returns = sum([1 for load in test_loads if (load // panels_per_line) % 2 != 0])
    strings = len(test_loads)
    phys_ports = strings * ports_per_string
    procs = math.ceil(phys_ports / processor_max_ports)
    
    load_diff = max(test_loads) - min(test_loads) if test_loads else float('inf')
    return procs, stranded_returns, phys_ports, load_diff, test_loads

if auto_opt:
    best_score = None; best_config = None; best_loads = []
    for d in [False, True]:
        for s in ["Maximize Port Capacity (Even chunks only)", "Force 4-Line Groups", "Force 2-Line Groups", "Evenly Balance Load"]:
            procs, stranded, ports, diff, loads = simulate_routing(d, s)
            score = (procs, stranded, ports, diff)
            if best_score is None or score < best_score:
                best_score = score; best_config = (d, s); best_loads = loads
    final_is_horizontal, final_strategy = best_config
    port_loads = best_loads
else:
    final_is_horizontal = "Horizontal" in st.session_state.sys_state['data_dir']
    final_strategy = st.session_state.sys_state['loom_strat']
    _, _, _, _, port_loads = simulate_routing(final_is_horizontal, final_strategy)

with col_c2:
    st.subheader("Cabling Output & Logistics")
    total_data_strings = len(port_loads)
    total_physical_ports = total_data_strings * ports_per_string 
    total_processors = math.ceil(total_physical_ports / processor_max_ports)
    
    if auto_opt:
        dir_str = "Horizontal" if final_is_horizontal else "Vertical"
        st.success(f"**Optimum Route Found:** {dir_str} routing using '{final_strategy}'.")
    
    met_c1, met_c2, met_c3 = st.columns(3)
    met_c1.metric("Data Strings Needed", f"{total_data_strings}")
    met_c2.metric(f"Ports Used {'(Inc B/U)' if use_bu else ''}", f"{total_physical_ports}")
    met_c3.metric("Processors Needed", f"{total_processors}")
    
    breakdown_parts = []
    panels_per_line = columns if final_is_horizontal else rows
    chunk_label = "Rows" if final_is_horizontal else "Cols"
    
    for i, load in enumerate(port_loads):
        main_port_idx = i * ports_per_string
        pr_main = (main_port_idx // processor_max_ports) + 1
        pt_main = (main_port_idx % processor_max_ports) + 1
        chunk_count = load // panels_per_line
        
        if use_bu:
            bu_port_idx = i * ports_per_string + 1
            pr_bu = (bu_port_idx // processor_max_ports) + 1
            pt_bu = (bu_port_idx % processor_max_ports) + 1
            breakdown_parts.append(f"- **String {i+1}** ({chunk_count} {chunk_label}): Main **Pr{pr_main}-P{pt_main}** ➔ Backup **Pr{pr_bu}-P{pt_bu}**")
        else:
            breakdown_parts.append(f"- **String {i+1}** ({chunk_count} {chunk_label}): Port **Pr{pr_main}-P{pt_main}**")
            
    st.info("**Processor Allocation:**\n\n" + "\n".join(breakdown_parts))

# --- 6. POWER DISTRIBUTION ---
st.header("4. Power Distribution")
cable_assemblies = {"10A IEC Cable (10A Limit)": 10, "13A UK Plug to PowerCON/True1 (13A Limit)": 13, "16A CEEFORM to PowerCON/True1 (16A Limit)": 16}

col_pwr1, col_pwr2, col_pwr3, col_pwr4 = st.columns(4)
with col_pwr1: 
    voltage = st.selectbox("Panel Voltage (V)", options=[110, 120, 230, 240], index=[110, 120, 230, 240].index(st.session_state.sys_state.get('voltage', 230)))
    st.session_state.sys_state['voltage'] = voltage
with col_pwr2: 
    cable_type = st.selectbox("Cable Assembly", options=list(cable_assemblies.keys()), index=get_index(list(cable_assemblies.keys()), st.session_state.sys_state.get('cable_type', list(cable_assemblies.keys())[2])))
    st.session_state.sys_state['cable_type'] = cable_type
with col_pwr3: 
    distro_phase = st.selectbox("Distro Type", options=["Single Phase (230V)", "3-Phase (415V)"], index=get_index(["Single Phase (230V)", "3-Phase (415V)"], st.session_state.sys_state.get('distro_phase', "3-Phase (415V)")))
    st.session_state.sys_state['distro_phase'] = distro_phase
with col_pwr4: 
    distro_amps = st.selectbox("Distro Amperage (Amps)", options=[16, 32, 63, 125, 400], index=get_index([16, 32, 63, 125, 400], st.session_state.sys_state.get('distro_amps', 63)))
    st.session_state.sys_state['distro_amps'] = distro_amps

cable_amps = cable_assemblies[cable_type]
safe_wattage_limit = voltage * cable_amps * 0.8
panel_max_power = panel_specs["max_power_w"]

panels_per_circuit = int(safe_wattage_limit // panel_max_power)
total_circuits_raw = math.ceil(total_panels / panels_per_circuit)
total_max_draw_kw = (total_panels * panel_max_power) / 1000

max_rows_per_circuit = panels_per_circuit // columns
power_loads = []

if max_rows_per_circuit > 0:
    target_rows = max_rows_per_circuit
    if target_rows > 1 and target_rows % 2 != 0: target_rows -= 1
    remaining_rows = rows
    while remaining_rows > 0:
        if remaining_rows >= target_rows: power_loads.append(target_rows * columns); remaining_rows -= target_rows
        else:
            if remaining_rows > 1 and remaining_rows % 2 != 0: power_loads.append((remaining_rows - 1) * columns); remaining_rows -= (remaining_rows - 1)
            else: power_loads.append(remaining_rows * columns); remaining_rows = 0
else:
    base_panels_per_circuit = total_panels // total_circuits_raw
    remainder_panels = total_panels % total_circuits_raw
    for i in range(total_circuits_raw): power_loads.append(base_panels_per_circuit + (1 if i < remainder_panels else 0))

distro_capacity_kw = (3 * 230 * distro_amps * 0.8) / 1000 if "3-Phase" in distro_phase else (230 * distro_amps * 0.8) / 1000

col_res1, col_res2, col_res3, col_res4 = st.columns(4)
col_res1.metric("Max Panels / Circuit", f"{panels_per_circuit}")
col_res2.metric("Power Runs Needed", f"{len(power_loads)}")
col_res3.metric("Total Wall Max Draw", f"{total_max_draw_kw:.2f} kW")
if distro_capacity_kw >= total_max_draw_kw: col_res4.success(f"✅ Distro OK ({distro_capacity_kw:.1f} kW limit)")
else: col_res4.error(f"❌ Distro Too Small ({distro_capacity_kw:.1f} kW limit)")

# --- 7. SMART PATHFINDING LOGIC ---
data_path_points = []
if not final_is_horizontal: 
    current_col = 0
    rem_panels_in_col = rows
    origin_r = 0 if not is_flown else rows - 1
    away_step = 1 if not is_flown else -1
    current_r = origin_r
    r_step = away_step
    
    for load in port_loads:
        # Snap back to origin correctly
        if rem_panels_in_col == rows:
            current_r = origin_r
            r_step = away_step
            
        for _ in range(load):
            data_path_points.append((current_col + 0.5, current_r + 0.5))
            rem_panels_in_col -= 1
            if rem_panels_in_col > 0: current_r += r_step
            else:
                current_col += 1
                rem_panels_in_col = rows
                r_step = -r_step 
else: 
    current_row_idx = 0
    row_order = list(range(rows - 1, -1, -1)) if is_flown else list(range(rows))
    rem_panels_in_row = columns
    current_c = 0
    c_step = 1
    
    for load in port_loads:
        # Snap back to Left edge correctly
        if rem_panels_in_row == columns:
            current_c = 0
            c_step = 1
            
        for _ in range(load):
            actual_r = row_order[current_row_idx]
            data_path_points.append((current_c + 0.5, actual_r + 0.5))
            rem_panels_in_row -= 1
            if rem_panels_in_row > 0: current_c += c_step
            else:
                current_row_idx += 1
                rem_panels_in_row = columns
                c_step = -c_step

power_path_points = []
current_row_idx = 0
row_order = list(range(rows - 1, -1, -1)) if is_flown else list(range(rows))
rem_panels_in_row = columns
current_c = 0
c_step = 1

for load in power_loads:
    if rem_panels_in_row == columns:
        current_c = 0
        c_step = 1
    for _ in range(load):
        if current_row_idx < rows: 
            actual_r = row_order[current_row_idx]
            power_path_points.append((current_c + 0.5, actual_r + 0.5))
            rem_panels_in_row -= 1
            if rem_panels_in_row > 0: current_c += c_step
            else:
                current_row_idx += 1
                rem_panels_in_row = columns
                c_step = -c_step

# --- 8. VISUALIZER & REPORTS ---
st.header("5. Schematics & Reports")
tab_data, tab_power, tab_testcard, tab_info = st.tabs(["📶 Data Routing", "⚡ Power Routing", "🎛️ Custom Test Card", "📝 Wall Info & Reports"])
port_colors = list(mcolors.TABLEAU_COLORS.values())

fig_w = max(6, min(columns * 0.8, 16))
fig_h = max(4, min(rows * 0.8, 10))

fig_data, ax_data = plt.subplots(figsize=(fig_w, fig_h))
fig_power, ax_power = plt.subplots(figsize=(fig_w, fig_h))

with tab_data:
    dir_text = "Horizontal" if final_is_horizontal else "Vertical"
    st.write(f"Diagram showing generated {dir_text} data paths.")
    for r in range(rows):
        for c in range(columns): ax_data.add_patch(patches.Rectangle((c, r), 1, 1, linewidth=2, edgecolor='#333333', facecolor='#0e1117'))

    current_idx = 0
    for string_index, load in enumerate(port_loads):
        port_points = data_path_points[current_idx : current_idx + load]
        if not port_points: break
        xs = [p[0] for p in port_points]
        ys = [p[1] for p in port_points]
        color = port_colors[string_index % len(port_colors)]
        
        main_p = string_index * ports_per_string
        pr_main = (main_p // processor_max_ports) + 1
        pt_main = (main_p % processor_max_ports) + 1
        label_main = f"Pr{pr_main}-P{pt_main} MAIN" if use_bu else f"Pr{pr_main}-P{pt_main}"
        
        ax_data.plot(xs, ys, color=color, linewidth=2.5, marker='o', markersize=5, label=f"String {string_index + 1}")
        ax_data.text(xs[0], ys[0] + 0.2, label_main, color=color, fontsize=8, weight='bold', ha='center', va='bottom', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))
        
        if use_bu:
            bu_p = string_index * ports_per_string + 1
            pr_bu = (bu_p // processor_max_ports) + 1
            pt_bu = (bu_p % processor_max_ports) + 1
            label_bu = f"Pr{pr_bu}-P{pt_bu} B/U"
            ax_data.text(xs[-1], ys[-1] - 0.2, label_bu, color=color, fontsize=8, weight='bold', ha='center', va='top', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))
        current_idx += load

    ax_data.set_xlim(0, columns); ax_data.set_ylim(0, rows); ax_data.set_aspect('equal'); ax_data.axis('off'); ax_data.legend(bbox_to_anchor=(1.0, 1), loc='upper left')
    st.pyplot(fig_data)

with tab_power:
    st.write(f"Diagram showing power daisy-chains.")
    for r in range(rows):
        for c in range(columns): ax_power.add_patch(patches.Rectangle((c, r), 1, 1, linewidth=2, edgecolor='#333333', facecolor='#0e1117'))

    current_idx = 0
    power_colors = ['#e6194b', '#f58231', '#ffe119', '#bfef45', '#3cb44b', '#42d4f4', '#4363d8', '#911eb4', '#f032e6']
    for circuit_index, enumerate_load in enumerate(power_loads):
        circuit_points = power_path_points[current_idx : current_idx + enumerate_load]
        if not circuit_points: break
        xs = [p[0] for p in circuit_points]
        ys = [p[1] for p in circuit_points]
        color = power_colors[circuit_index % len(power_colors)]
        
        ax_power.plot(xs, ys, color=color, linestyle='--', linewidth=3, marker='s', markersize=5, label=f"Circuit {circuit_index + 1}")
        ax_power.text(xs[0], ys[0] + 0.2, f"PWR {circuit_index + 1} IN", color=color, fontsize=8, weight='bold', ha='center', va='bottom', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))
        current_idx += enumerate_load

    ax_power.set_xlim(0, columns); ax_power.set_ylim(0, rows); ax_power.set_aspect('equal'); ax_power.axis('off'); ax_power.legend(bbox_to_anchor=(1.0, 1), loc='upper left')
    st.pyplot(fig_power)

with tab_testcard:
    st.write("Generating 1:1 Pixel Perfect Test Pattern...")
    
    # RESTORED FEATURE: Manual Logo Uploader
    uploaded_logo = st.file_uploader("Upload Client Logo for Test Card (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
    
    # CALCULATE PIXEL PERFECT DIMENSIONS
    fig_tc = plt.figure(figsize=(columns, rows), dpi=panel_specs['res_w']) 
    ax_tc = fig_tc.add_axes([0, 0, 1, 1]) 
    ax_tc.set_facecolor('#1e1e1e')
    
    smpte_colors = ['#FFFFFF', '#FFFF00', '#00FFFF', '#00FF00', '#FF00FF', '#FF0000', '#0000FF']
    for r in range(rows):
        for c in range(columns):
            fill_color = '#2a2a2a' if (r + c) % 2 == 0 else '#353535'
            ax_tc.add_patch(patches.Rectangle((c, r), 1, 1, color=fill_color, zorder=0))
            if r == 0:
                bar_c = smpte_colors[c % len(smpte_colors)]
                ax_tc.add_patch(patches.Rectangle((c, 0), 1, 0.15, color=bar_c, alpha=0.8, zorder=1))

    # Crosshairs and Circle
    ax_tc.plot([0, columns], [0, rows], color='white', alpha=0.2, linewidth=1, zorder=2)
    ax_tc.plot([0, columns], [rows, 0], color='white', alpha=0.2, linewidth=1, zorder=2)
    
    center_x, center_y = columns / 2, rows / 2
    radius = min(columns, rows) / 2 * 0.95
    ax_tc.add_patch(patches.Circle((center_x, center_y), radius, fill=False, edgecolor='white', alpha=0.2, linewidth=1, zorder=2))

    # Data Mapping
    panel_map = {}
    current_idx = 0
    for string_index, load in enumerate(port_loads):
        port_points = data_path_points[current_idx : current_idx + load]
        if not port_points: break
        main_p = string_index * ports_per_string
        pt_main = (main_p % processor_max_ports) + 1
        for panel_idx, point in enumerate(port_points):
            panel_map[point] = f"{pt_main}.{panel_idx + 1}"
        current_idx += load

    font_s_grid = max(4, 10 - (columns * 0.1))
    font_s_route = max(5, 13 - (columns * 0.15))

    for r in range(rows):
        for c in range(columns):
            col_idx = c
            res_letter = ""
            while col_idx >= 0:
                res_letter = string.ascii_uppercase[col_idx % 26] + res_letter
                col_idx = col_idx // 26 - 1
            grid_id = f"{res_letter}{rows - r}"
            
            ax_tc.text(c + 0.05, r + 0.95, grid_id, color='white', alpha=0.4, fontsize=font_s_grid, va='top', ha='left', zorder=3)
            point = (c + 0.5, r + 0.5)
            if point in panel_map: ax_tc.text(c + 0.5, r + 0.5, panel_map[point], color='#cccccc', fontsize=font_s_route, va='center', ha='center', weight='bold', zorder=3)
            ax_tc.add_patch(patches.Rectangle((c, r), 1, 1, fill=False, edgecolor='black', alpha=0.3, linewidth=0.5, zorder=4))

    # Resolution text
    ax_tc.text(center_x, center_y + (rows * 0.15), f"{canvas_res_w} x {canvas_res_h} px", color='white', alpha=0.8, fontsize=max(7, columns * 1.2), ha='center', va='center', weight='bold', bbox=dict(facecolor='#1e1e1e', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.3'), zorder=5)

    # LOGIC: Use Uploaded Logo first, then fall back to epl_logo.png
    logo_to_use = None
    if uploaded_logo is not None:
        logo_to_use = Image.open(uploaded_logo)
    elif os.path.exists(LOGO_FILENAME):
        logo_to_use = Image.open(LOGO_FILENAME)

    if logo_to_use:
        logo_width = columns * 0.25
        logo_height = logo_width * (logo_to_use.height / logo_to_use.width)
        ax_tc.imshow(logo_to_use, extent=[center_x - logo_width/2, center_x + logo_width/2, (rows * 0.25) - logo_height/2, (rows * 0.25) + logo_height/2], zorder=6, alpha=0.8)

    ax_tc.set_xlim(0, columns); ax_tc.set_ylim(0, rows); ax_tc.set_aspect('equal'); ax_tc.axis('off')
    st.pyplot(fig_tc)
    
    # PIXEL PERFECT SAVE
    buf_tc = io.BytesIO()
    fig_tc.savefig(buf_tc, format="png", dpi=panel_specs['res_w'], pad_inches=0)
    st.download_button(
        label="📥 Download Pixel-Perfect Test Card (PNG)",
        data=buf_tc.getvalue(),
        file_name=f"{safe_proj_name}_TestCard_1to1.png",
        mime="image/png"
    )
    
with tab_info:
    st.write("Summary sheet of all build requirements.")
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.markdown("### Physical Build")
        st.markdown(f"**Panel:** {sel_panel}")
        st.markdown(f"**Total Panels:** {total_panels}")
        st.markdown(f"**Layout:** {columns} Columns x {rows} Rows")
        st.markdown(f"**Dimensions:** {actual_width_m:.2f}m W x {actual_height_m:.2f}m H")
        st.markdown(f"**Total Weight:** {total_weight_kg:.1f} kg")
        st.markdown(f"**Rigging Origin:** {st.session_state.sys_state['rigging']}")
        
    with col_info2:
        st.markdown("### Signal & Power")
        st.markdown(f"**Resolution:** {canvas_res_w} x {canvas_res_h} px")
        st.markdown(f"**Processors Needed:** {total_processors}x {sel_proc}")
        st.markdown(f"**Data Strings:** {total_data_strings} (Using {total_physical_ports} physical ports)")
        st.markdown(f"**Power Runs:** {len(power_loads)} circuits")
        st.markdown(f"**Total Max Draw:** {total_max_draw_kw:.2f} kW")
        st.markdown(f"**Required Distro:** {distro_amps}A {distro_phase}")

# --- 9. MASTER EXPORT BUTTON (MANUAL TRIGGER TO PREVENT HANGS) ---
st.divider()
st.header("📥 Export Project")
st.write("Generate a standardized A4 PDF containing the summary sheet, data schematics, and power schematics.")

current_config_str = f"{sel_panel}_{target_w}_{target_h}_{sel_proc}_{final_is_horizontal}_{final_strategy}_{rigging}_{use_bu}_{voltage}_{cable_type}_{distro_phase}_{distro_amps}"

if st.session_state.get('last_config') != current_config_str:
    if 'pdf_export' in st.session_state:
        del st.session_state['pdf_export']
    st.session_state['last_config'] = current_config_str

def add_logo_to_pdf_fig(fig, rect=[0.8, 0.85, 0.12, 0.12]):
    if os.path.exists(LOGO_FILENAME):
        try:
            img = Image.open(LOGO_FILENAME)
            ax_logo = fig.add_axes(rect)
            ax_logo.imshow(img)
            ax_logo.axis('off')
        except Exception: pass

def generate_master_pdf():
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        fig_cover, ax_cover = plt.subplots(figsize=(8.27, 11.69))
        ax_cover.axis('off')
        add_logo_to_pdf_fig(fig_cover, rect=[0.4, 0.75, 0.2, 0.2])
        proj_text = safe_proj_name.replace("_", " ") if safe_proj_name != "Unnamed_Project" else "LED Video Wall Configurator"
        ax_cover.text(0.5, 0.65, proj_text, fontsize=28, ha='center', weight='bold')
        ax_cover.text(0.5, 0.58, "Configuration Report & Schematics", fontsize=18, ha='center', color='grey')
        ax_cover.text(0.5, 0.5, f"Date: {datetime.now().strftime('%d %b %Y')}", fontsize=14, ha='center')
        pdf.savefig(fig_cover); plt.close(fig_cover)

        fig_info, ax_info = plt.subplots(figsize=(8.27, 11.69))
        ax_info.axis('off')
        add_logo_to_pdf_fig(fig_info)
        ax_info.text(0.1, 0.95, "Wall Info File", fontsize=20, weight='bold', va='top')
        info_text = (
            f"PHYSICAL BUILD\n"
            f"Panel Model: {sel_panel}\n"
            f"Total Panels: {total_panels}\n"
            f"Grid Layout: {columns} W x {rows} H\n"
            f"Physical Size: {actual_width_m:.2f}m x {actual_height_m:.2f}m\n"
            f"Total Weight: {total_weight_kg:.1f} kg\n"
            f"Rigging Origin: {st.session_state.sys_state['rigging']}\n\n"
            
            f"SIGNAL & DATA\n"
            f"Processor Model: {sel_proc}\n"
            f"Total Processors Required: {total_processors}\n"
            f"Canvas Resolution: {canvas_res_w} x {canvas_res_h} px\n"
            f"Data Strings Needed: {total_data_strings}\n"
            f"Physical Ports Used: {total_physical_ports}\n"
            f"Backups Included: {'Yes' if use_bu else 'No'}\n\n"
            
            f"POWER DISTRIBUTION\n"
            f"Power Cable Limit: {cable_amps}A\n"
            f"Total Power Runs (Circuits): {len(power_loads)}\n"
            f"Total Wall Max Draw: {total_max_draw_kw:.2f} kW\n"
            f"Minimum Distro Required: {distro_amps}A {distro_phase}\n"
        )
        ax_info.text(0.1, 0.88, info_text, fontsize=12, va='top', fontfamily='monospace')
        pdf.savefig(fig_info); plt.close(fig_info)

        fig_data.suptitle("Data Routing Schematic", fontsize=16, weight='bold')
        add_logo_to_pdf_fig(fig_data)
        pdf.savefig(fig_data, bbox_inches='tight')
        
        fig_power.suptitle("Power Routing Schematic", fontsize=16, weight='bold')
        add_logo_to_pdf_fig(fig_power)
        pdf.savefig(fig_power, bbox_inches='tight')
        
    return buf.getvalue()

if 'pdf_export' not in st.session_state:
    if st.button("🛠️ Generate Master PDF Report"):
        with st.spinner("Rendering High-Resolution PDF... Please wait."):
            st.session_state['pdf_export'] = generate_master_pdf()
            st.rerun()
else:
    st.success("✅ PDF Ready for Download!")
    st.download_button(
        label="📥 Download Master PDF Report", 
        data=st.session_state['pdf_export'], 
        file_name=f"{safe_proj_name}_Master_Report.pdf", 
        mime="application/pdf"
    )

# CRITICAL FIX: Flush RAM to ensure Streamlit server does not hang
plt.close('all')
