import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Evaluasi Rekomendasi Menu", layout="centered")

# --- Konfigurasi Google Sheets Web App ---
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyjVaqwQTFu6vt0yM5zk3Md0cSXD04Fl-izeELBkagbL71cJvBDtHddthw3b7dA3Zy3ng/exec"

# --- Load Data ---
@st.cache_data
def load_data():
    df_menu = pd.read_excel("Data/mst_barang.xlsx")
    cf_sim = pd.read_csv("cbf_cosine_sim.csv", index_col=0)
    cbf_sim = pd.read_csv("cf_ensemble_sim_matrix.csv", index_col=0)
    return df_menu, cf_sim, cbf_sim

df_menu, cbf_sim, cf_sim = load_data()

# --- Fungsi Rekomendasi ---
def rekomendasi_ensemble(menu_input, cbf_sim, cf_sim, alpha=0.6, top_k=10):
    menu_input = menu_input.strip().upper()
    cbf_sim.columns = cbf_sim.columns.str.strip().str.upper()
    cbf_sim.index = cbf_sim.index.str.strip().str.upper()
    cf_sim.columns = cf_sim.columns.str.strip().str.upper()
    cf_sim.index = cf_sim.index.str.strip().str.upper()

    if menu_input not in cbf_sim.columns or menu_input not in cf_sim.columns:
        return []

    # Gabungan skor weighted average
    combined_score = alpha * cbf_sim[menu_input] + (1 - alpha) * cf_sim[menu_input]
    combined_score = combined_score.drop(index=menu_input)
    return combined_score.sort_values(ascending=False).head(top_k).index.tolist()
# --- Tampilan Utama ---
st.markdown(
    """
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="margin-bottom: 0;">🧠 Evaluasi Sistem Rekomendasi Menu</h1>
        <p style="font-size: 18px; color: gray;">Model Ensemble (CBF + CF)</p>
    </div>
    <hr style="margin-top: -10px;">
    """,
    unsafe_allow_html=True
)

# --- Sidebar Form ---
with st.sidebar:
    st.markdown("### 👤 Informasi Partisipan")
    partisipan = st.text_input("Nama Partisipan")
    num_iter = st.number_input("Jumlah Percobaan", value=5, step=1)
    if st.button("🚀 Mulai Tes"):
        st.session_state['current_iter'] = 1
        st.session_state['total_iter'] = num_iter
        st.session_state['results'] = []

    # Tampilkan histori di sidebar
    if 'results' in st.session_state and st.session_state['results']:
        st.markdown("---")
        st.markdown("### 📝 Riwayat Pilihan")
        for item in st.session_state['results']:
            st.markdown(f"""
            <div style='padding: 5px 8px; margin-bottom: 5px; background-color: #f2f2f2;
                        border-left: 4px solid #4CAF50; border-radius: 4px; font-size: 13px;'>
                <b>Iterasi {item['iterasi']}</b><br>{item['input_menu']}
            </div>
            """, unsafe_allow_html=True)

# --- Bagian Utama Interaksi ---
if 'current_iter' in st.session_state and st.session_state['current_iter'] <= st.session_state['total_iter']:
    iterasi = st.session_state['current_iter']
    st.info(f"Percobaan {iterasi} dari {st.session_state['total_iter']}", icon="🧪")

    # Tampilkan histori pilihan sebelumnya
    if st.session_state['results']:
        st.markdown("### 📋 Riwayat Pilihan Sebelumnya")
        for item in st.session_state['results']:
            st.markdown(f"""
            <div style='background-color: #f9f9f9; padding: 8px 12px; border-left: 5px solid #4CAF50; margin-bottom: 10px; border-radius: 5px;'>
                <b>Iterasi {item['iterasi']}:</b> {item['input_menu']}
            </div>
            """, unsafe_allow_html=True)
    st.subheader("Pilih Menu Favorit Anda")
    selected_menu = st.selectbox("", df_menu['nama'], key=f"menu_{iterasi}")
    

    col1, col2 = st.columns([2, 1])
    with col1:
        if f"rekomendasi_{iterasi}" not in st.session_state:
            if st.button("🎯 Tampilkan Rekomendasi", key=f"tampil_{iterasi}"):
                rekomendasi = rekomendasi_ensemble(selected_menu, cbf_sim, cf_sim, alpha=0.6, top_k=10)
                st.session_state[f"rekomendasi_{iterasi}"] = rekomendasi
    with col2:
        st.write("")

    if f"rekomendasi_{iterasi}" in st.session_state:
        rekomendasi = st.session_state[f"rekomendasi_{iterasi}"]

        if not rekomendasi:
            st.error("Menu tidak ditemukan dalam data.")
        else:
            st.divider()
            st.subheader("📝 Penilaian Rekomendasi")
            with st.form(f"rating_form_{iterasi}"):
                ratings = {}
                for i, item in enumerate(rekomendasi, 1):
                    col1, col2 = st.columns([3, 2])
                    with col1:
                        st.markdown(f"**{i}. {item}**")
                    with col2:
                        rating = st.radio(
                            "Relevan?",
                            ["Ya", "Tidak"],
                            key=f"rating_{iterasi}_{i}",
                            horizontal=True,
                            label_visibility="collapsed"
                        )
                        ratings[item] = 1 if rating == "Ya" else 0

                submitted = st.form_submit_button("✅ Kirim Penilaian")

            if submitted:
                st.session_state['results'].append({
                    "partisipan": partisipan,
                    "iterasi": iterasi,
                    "input_menu": selected_menu,
                    "rekomendasi": rekomendasi,
                    "penilaian": [ratings[item] for item in rekomendasi]
                })
                st.success("Penilaian berhasil disimpan. Lanjut ke percobaan berikutnya.")
                st.session_state['current_iter'] += 1
                st.rerun()

# --- Kirim ke Google Sheets ---
if 'current_iter' in st.session_state and st.session_state['current_iter'] > st.session_state['total_iter']:
    st.success("🎉 Evaluasi selesai. Mengirim data ke server...")

    with st.spinner("Mengirim hasil evaluasi..."):
        for record in st.session_state['results']:
            payload = {
                "partisipan": record['partisipan'],
                "iterasi": record['iterasi'],
                "input_menu": record['input_menu'],
                "rekomendasi": record['rekomendasi'],
                "penilaian": record['penilaian']
            }
            try:
                response = requests.post(WEB_APP_URL, json=payload)
                if response.status_code != 200:
                    st.warning("⚠️ Gagal menyimpan salah satu entri.")
                else:
                    st.success(f"✅ Iterasi {record['iterasi']} berhasil dikirim.")
            except:
                st.error("❌ Gagal menghubungi Google Sheets.")

    st.balloons()
    st.session_state.clear()
