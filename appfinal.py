import matplotlib
matplotlib.use('Agg')
import streamlit as st
from collections import OrderedDict
import random
import matplotlib.pyplot as plt
import pandas as pd

class VirtualMemory:
    def __init__(self, algo, num_frames, page_size):
        self.algo = algo
        self.num_frames = num_frames
        self.page_size = page_size
        
        self.frames = []          
        self.page_table = {}      
        self.lru_tracker = OrderedDict() 
        
        self.hits = 0
        self.faults = 0

    def request(self, logical_address, future_pages=None):
        page_number = logical_address // self.page_size
        offset = logical_address % self.page_size
        evicted_page = None
        
        if page_number in self.page_table:
            self.hits += 1
            frame_idx = self.page_table[page_number]
            if self.algo == "LRU":
                self.lru_tracker.move_to_end(page_number)
            status = "HIT"
        else:
            self.faults += 1
            status = "FAULT"
            
            if len(self.frames) < self.num_frames:
                frame_idx = len(self.frames)
                self.frames.append(page_number)
                self.page_table[page_number] = frame_idx
                if self.algo == "LRU":
                    self.lru_tracker[page_number] = frame_idx
            else:
                if self.algo == "FIFO":
                    evicted_page = self.frames.pop(0)
                    frame_idx = self.page_table.pop(evicted_page)
                    self.frames.append(page_number)
                    self.page_table[page_number] = frame_idx
                    
                elif self.algo == "LRU":
                    evicted_page, frame_idx = self.lru_tracker.popitem(last=False)
                    self.page_table.pop(evicted_page)
                    self.frames[frame_idx] = page_number 
                    self.page_table[page_number] = frame_idx
                    self.lru_tracker[page_number] = frame_idx
                    
                elif self.algo == "OPT":
                    farthest_use = -1
                    evict_frame_idx = -1
                    evicted_page = None
                    
                    for f_idx, p_in_frame in enumerate(self.frames):
                        try:
                            next_use = future_pages.index(p_in_frame)
                        except (ValueError, AttributeError):
                            next_use = float('inf') 
                            
                        if next_use > farthest_use:
                            farthest_use = next_use
                            evict_frame_idx = f_idx
                            evicted_page = p_in_frame
                            
                    frame_idx = evict_frame_idx
                    self.page_table.pop(evicted_page)
                    self.frames[frame_idx] = page_number
                    self.page_table[page_number] = frame_idx

        physical_address = (frame_idx * self.page_size) + offset
        
        return {
            "status": status,
            "frame": frame_idx,
            "evicted": evicted_page,
            "phys_addr": physical_address,
            "page": page_number,
            "offset": offset,
            "frames_state": self.frames.copy() 
        }

# --- UI LOGIC & TRACE GEN ---
st.set_page_config(page_title="Virtual Memory Simulator", layout="wide")

if 'trace_str' not in st.session_state:
    st.session_state.trace_str = "256, 512, 768, 256, 512, 1024, 256, 512"
if 'run_mode' not in st.session_state:
    st.session_state.run_mode = None
if 'belady_frames' not in st.session_state:
    st.session_state.belady_frames = 3

def generate_trace():
    length = st.session_state.trace_len
    trace_type = st.session_state.trace_type
    page_size = st.session_state.page_size
    
    trace = []
    if trace_type == "Belady's Anomaly Trace":
        unique_pages = random.sample(range(1, 50), 5)
        p_map = {1: unique_pages[0], 2: unique_pages[1], 3: unique_pages[2], 4: unique_pages[3], 5: unique_pages[4]}
        pattern = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
        trace = [(p_map[p] * page_size) + random.randint(0, page_size - 1) for p in pattern]
        
    elif trace_type == "Random":
        max_addr = page_size * 20 
        trace = [random.randint(0, max_addr) for _ in range(length)]
        
    elif trace_type == "Looping":
        core_pages = random.sample(range(1, 10), 2)
        cold_pages = random.sample(range(11, 30), 8)
        while len(trace) < length:
            for cp in core_pages:
                if len(trace) < length:
                    trace.append((cp * page_size) + random.randint(0, page_size - 1))
            if len(trace) < length:
                cold = random.choice(cold_pages)
                trace.append((cold * page_size) + random.randint(0, page_size - 1))

    st.session_state.trace_str = ", ".join(map(str, trace))

def run_single(): st.session_state.run_mode = "single"
def run_compare(): st.session_state.run_mode = "compare"
def run_belady(): 
    st.session_state.run_mode = "belady"
    st.session_state.belady_frames = 3
        
def clear_output(): st.session_state.run_mode = None

def inc_belady_frames():
    if st.session_state.belady_frames < 7: st.session_state.belady_frames += 1
def dec_belady_frames():
    if st.session_state.belady_frames > 1: st.session_state.belady_frames -= 1

# --- HORIZONTAL TABLE GENERATOR ---
def build_horizontal_table_html(results, num_frames):
    border_style = "1px solid #1e293b" 
    header_bg = "#0f172a" 
    row_bg = "#0b1120" 
    text_color = "#e2e8f0" 
    
    html = "<div style='overflow-x: auto; margin-bottom: 20px;'>"
    html += f"<table style='width: 100%; min-width: 800px; text-align: center; border-collapse: collapse; font-family: monospace; border: {border_style}; color: {text_color};'>"
    
    html += f"<tr><th style='border: {border_style}; padding: 10px; background-color: {header_bg};'>Trace (Pg)</th>"
    for _, res in results:
        html += f"<th style='border: {border_style}; padding: 10px; background-color: {header_bg};'>Pg {res['page']}</th>"
    html += "</tr>"

    for f in range(num_frames):
        html += f"<tr><td style='border: {border_style}; padding: 8px; font-weight: bold; background-color: {header_bg};'>F{f}</td>"
        for _, res in results:
            state = res['frames_state']
            val = state[f] if f < len(state) else "-"
            
            bg = f"background-color: {row_bg};"
            if res['frame'] == f:
                bg = "background-color: #166534;" if res['status'] == "HIT" else "background-color: #7f1d1d;"
            
            html += f"<td style='border: {border_style}; padding: 8px; {bg}'>{val}</td>"
        html += "</tr>"
        
    html += f"<tr><td style='border: {border_style}; padding: 8px; font-weight: bold; background-color: {header_bg};'>Status</td>"
    for _, res in results:
        color = "#4ade80" if res['status'] == "HIT" else "#f87171"
        html += f"<td style='border: {border_style}; padding: 8px; color: {color}; font-weight: bold; background-color: {row_bg};'>{res['status'][0]}</td>"
    html += "</tr>"
    
    html += "</table></div>"
    return html

# --- DATA EXPORT GENERATORS ---
def generate_csv_data(results, vmem):
    data = []
    for step, (addr, res) in enumerate(results):
        row = {
            "Step": step + 1,
            "Logical Addr": addr,
            "Page Math (Addr // Size)": f"{addr} // {vmem.page_size} = {res['page']}",
            "Offset Math (Addr % Size)": f"{addr} % {vmem.page_size} = {res['offset']}",
            "Status": res["status"],
            "Assigned Frame": res["frame"],
            "Evicted Page": res["evicted"] if res["evicted"] is not None else "None",
            "Physical Math ((Frame * Size) + Offset)": f"({res['frame']} * {vmem.page_size}) + {res['offset']} = {res['phys_addr']}"
        }
        for f in range(vmem.num_frames):
            row[f"Frame_{f}"] = res["frames_state"][f] if f < len(res["frames_state"]) else "-"
        data.append(row)
    return pd.DataFrame(data).to_csv(index=False).encode('utf-8')

def generate_stacked_combined_csv(f_res, l_res, o_res, fifo_vmem, lru_vmem, opt_vmem):
    fifo_csv = generate_csv_data(f_res, fifo_vmem).decode('utf-8')
    lru_csv = generate_csv_data(l_res, lru_vmem).decode('utf-8')
    opt_csv = generate_csv_data(o_res, opt_vmem).decode('utf-8')
    
    combined_text = (
        "--- FIFO ALGORITHM LOGS ---\n" + fifo_csv +
        "\n\n\n--- LRU ALGORITHM LOGS ---\n" + lru_csv +
        "\n\n\n--- OPT ALGORITHM LOGS ---\n" + opt_csv
    )
    return combined_text.encode('utf-8')

def show_mapping_table(vmem):
    st.write("#### Memory Mapping")
    if not vmem.page_table:
        st.info("Memory is empty.")
        return
    data = []
    for page, frame in vmem.page_table.items():
        v_start = page * vmem.page_size
        v_end = v_start + vmem.page_size - 1
        p_start = frame * vmem.page_size
        p_end = p_start + vmem.page_size - 1
        data.append({
            "Virtual Page": f"Page {page}",
            "Physical Frame": f"Frame {frame}",
            "Virtual Base Calc": f"{page} × {vmem.page_size} = {v_start}",
            "Physical Base Calc": f"{frame} × {vmem.page_size} = {p_start}",
            "Virtual Range": f"{v_start} → {v_end}",
            "Physical Range": f"{p_start} → {p_end}"
        })
    df = pd.DataFrame(data).sort_values("Physical Frame").reset_index(drop=True)
    st.dataframe(df, use_container_width=True)

# --- LAYOUT ---
st.title("Virtual Memory & Paging Simulator")

with st.sidebar:
    st.header("⚙️ Settings")
    algo = st.selectbox("Algorithm", ["FIFO", "LRU", "OPT"])
    num_frames = st.number_input("Physical Frames", min_value=1, value=3, key="num_frames")
    
    page_size_options = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    page_size = st.selectbox("Page Size (bytes)", page_size_options, index=8, key="page_size")
    
    st.divider()
    
    st.header("Generate Trace")
    st.selectbox("Trace Pattern", ["Looping", "Belady's Anomaly Trace", "Random"], key="trace_type")
    st.number_input("Length", min_value=1, value=15, key="trace_len")
    st.button("Generate Trace", on_click=generate_trace, use_container_width=True)

trace_input = st.text_input("Logical Address Trace (comma-separated):", key="trace_str")

col1, col2, col3, col4 = st.columns([2, 3, 3, 2])
with col1:
    st.button("Run Single Algo", on_click=run_single, use_container_width=True)
with col2:
    st.button("Compare All 3", type="primary", on_click=run_compare, use_container_width=True)
with col3:
    st.button("Test Belady's Anomaly", on_click=run_belady, use_container_width=True)
with col4:
    st.button("Clear Output", on_click=clear_output, use_container_width=True)

try:
    trace_list = [int(x.strip()) for x in trace_input.split(',') if x.strip()]
    trace_pages = [addr // page_size for addr in trace_list]
except ValueError:
    st.error("Please ensure the trace contains only valid comma-separated integers.")
    trace_list = []
    trace_pages = []

st.divider()

if st.session_state.run_mode == "single" and trace_list:
    vmem = VirtualMemory(algo, num_frames, page_size)
    results = []
    
    for i, address in enumerate(trace_list):
        future_pages = trace_pages[i+1:] if algo == "OPT" else None
        results.append((address, vmem.request(address, future_pages)))
        
    total = vmem.hits + vmem.faults
    hit_rate = (vmem.hits / total) * 100 if total > 0 else 0
    
    st.subheader(f"Results for {algo}")
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Hits", vmem.hits)
    sc2.metric("Page Faults", vmem.faults)
    sc3.metric("Hit Rate", f"{hit_rate:.1f}%")
    
    st.write("### Execution Timeline")
    st.markdown(build_horizontal_table_html(results, num_frames), unsafe_allow_html=True)
    
    st.download_button(
        label=f"⬇️ Download Logs (CSV)",
        data=generate_csv_data(results, vmem),
        file_name=f"{algo}_memory_logs.csv",
        mime="text/csv"
    )
        
    st.divider()
    show_mapping_table(vmem)

elif st.session_state.run_mode == "compare" and trace_list:
    fifo_vmem = VirtualMemory("FIFO", num_frames, page_size)
    lru_vmem = VirtualMemory("LRU", num_frames, page_size)
    opt_vmem = VirtualMemory("OPT", num_frames, page_size)
    
    f_res, l_res, o_res = [], [], []
    for i, address in enumerate(trace_list):
        f_res.append((address, fifo_vmem.request(address)))
        l_res.append((address, lru_vmem.request(address)))
        o_res.append((address, opt_vmem.request(address, trace_pages[i+1:])))

    st.subheader("Comparison: FIFO vs LRU vs OPT")
    
    fig, ax = plt.subplots(figsize=(8, 3))
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    ax.tick_params(colors='gray')
    ax.spines['bottom'].set_color('gray')
    ax.spines['left'].set_color('gray')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    bars = ax.bar(['FIFO', 'LRU', 'OPT'], [fifo_vmem.faults, lru_vmem.faults, opt_vmem.faults], color=['#e76f51', '#2a9d8f', '#e9c46a'])
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + 0.1, int(yval), ha='center', va='bottom', fontweight='bold', color='white')
    ax.set_title('Total Page Faults Comparison', color='white')
    ax.set_ylabel('Faults', color='gray')
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    st.pyplot(fig)
    
    st.download_button(
        label="⬇️ Download Combined Logs (CSV)",
        data=generate_stacked_combined_csv(f_res, l_res, o_res, fifo_vmem, lru_vmem, opt_vmem),
        file_name="combined_stacked_memory_logs.csv",
        mime="text/csv"
    )
    
    tab1, tab2, tab3 = st.tabs(["📊 FIFO", "📊 LRU", "📊 OPT"])
    
    def calc_rate(hits, faults):
        tot = hits + faults
        return f"{(hits/tot)*100:.1f}%" if tot > 0 else "0.0%"

    with tab1:
        c1, c2, c3 = st.columns(3)
        c1.metric("Hits", fifo_vmem.hits)
        c2.metric("Faults", fifo_vmem.faults)
        c3.metric("Hit Rate", calc_rate(fifo_vmem.hits, fifo_vmem.faults))
        st.markdown(build_horizontal_table_html(f_res, num_frames), unsafe_allow_html=True)
        show_mapping_table(fifo_vmem)
        st.download_button("⬇️ Download FIFO Logs", generate_csv_data(f_res, fifo_vmem), "fifo_logs.csv", "text/csv")
        
    with tab2:
        c1, c2, c3 = st.columns(3)
        c1.metric("Hits", lru_vmem.hits)
        c2.metric("Faults", lru_vmem.faults)
        c3.metric("Hit Rate", calc_rate(lru_vmem.hits, lru_vmem.faults))
        st.markdown(build_horizontal_table_html(l_res, num_frames), unsafe_allow_html=True)
        show_mapping_table(lru_vmem)
        st.download_button("⬇️ Download LRU Logs", generate_csv_data(l_res, lru_vmem), "lru_logs.csv", "text/csv")
        
    with tab3:
        c1, c2, c3 = st.columns(3)
        c1.metric("Hits", opt_vmem.hits)
        c2.metric("Faults", opt_vmem.faults)
        c3.metric("Hit Rate", calc_rate(opt_vmem.hits, opt_vmem.faults))
        st.markdown(build_horizontal_table_html(o_res, num_frames), unsafe_allow_html=True)
        show_mapping_table(opt_vmem)
        st.download_button("⬇️ Download OPT Logs", generate_csv_data(o_res, opt_vmem), "opt_logs.csv", "text/csv")

elif st.session_state.run_mode == "belady" and trace_list:
    st.subheader("Frame Scaling Test")
    
    def render_belady_tab(algo_name):
        faults_by_frames = []
        frame_range = range(1, 8)
        
        for f in frame_range:
            v = VirtualMemory(algo_name, f, page_size)
            for i, addr in enumerate(trace_list):
                future_pages = trace_pages[i+1:] if algo_name == "OPT" else None
                v.request(addr, future_pages)
            faults_by_frames.append(v.faults)
            
        c1, c2 = st.columns([1, 2])
        with c1:
            df = pd.DataFrame({"Frames": frame_range, "Page Faults": faults_by_frames})
            st.dataframe(df, hide_index=True)
            
            anomaly_found = False
            for i in range(1, len(faults_by_frames)):
                if faults_by_frames[i] > faults_by_frames[i-1]:
                    anomaly_found = True
                    break
                    
            if anomaly_found:
                st.error("⚠️ Belady's Anomaly Detected!")
            else:
                st.success("✅ No Anomaly Detected")
            
        with c2:
            fig, ax = plt.subplots(figsize=(8, 4))
            fig.patch.set_alpha(0.0)
            ax.patch.set_alpha(0.0)
            ax.tick_params(colors='gray')
            ax.spines['bottom'].set_color('gray')
            ax.spines['left'].set_color('gray')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            ax.plot(frame_range, faults_by_frames, marker='o', linestyle='-', color='#e76f51', linewidth=2, markersize=8)
            
            current_f = st.session_state.belady_frames
            current_faults = faults_by_frames[current_f - 1]
            ax.plot(current_f, current_faults, marker='o', color='#4ade80', markersize=12) 
            
            title_str = f"Frame Scaling Test ({algo_name})"
            ax.set_title(title_str, color='white', pad=15)
            ax.set_xlabel("Number of Physical Frames", color='gray')
            ax.set_ylabel("Total Page Faults", color='gray')
            ax.set_xticks(list(frame_range))
            ax.grid(True, linestyle='--', alpha=0.3)
            st.pyplot(fig)
            
        st.divider()
        st.write("### Execution Trace")
        
        btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 4])
        with btn_col1:
            st.button("➖ Decrease Frames", key=f"dec_{algo_name}", on_click=dec_belady_frames, use_container_width=True)
        with btn_col2:
            st.button("➕ Increase Frames", key=f"inc_{algo_name}", on_click=inc_belady_frames, use_container_width=True)
            
        st.write(f"**Observing: {st.session_state.belady_frames} Frames** | Total Faults: {current_faults}")
        
        deep_vmem = VirtualMemory(algo_name, st.session_state.belady_frames, page_size)
        deep_results = []
        for i, addr in enumerate(trace_list):
            future_pages = trace_pages[i+1:] if algo_name == "OPT" else None
            deep_results.append((addr, deep_vmem.request(addr, future_pages)))
            
        st.markdown(build_horizontal_table_html(deep_results, st.session_state.belady_frames), unsafe_allow_html=True)

    tab_f, tab_l, tab_o = st.tabs(["FIFO", "LRU", "OPT"])
    with tab_f: render_belady_tab("FIFO")
    with tab_l: render_belady_tab("LRU")
    with tab_o: render_belady_tab("OPT")

else:
    st.subheader("Results Dashboard")