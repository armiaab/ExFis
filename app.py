import streamlit as st
import pandas as pd
from datetime import datetime
import time

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSjfay3AikrwDJItRNLvCYlACYkuzT4HTQ9Azo59AaHRYkDV9CW6yDgrYpdhbWV6Wuqpja8tUh3OfaW/pub?output=csv"


def load_data():
    df = pd.read_csv(SHEET_CSV_URL)

    # Format tanggal: dd/mm/yyyy (tanggal/bulan/tahun), dengan atau tanpa jam
    df["Timestamp"] = pd.to_datetime(
        df["Timestamp"],
        dayfirst=True,
        errors="coerce",
    )

    df = df.dropna(subset=["Timestamp"])
    df = df.sort_values("Timestamp")

    numeric_cols = ["Voltage (V)", "Current (A)", "Power (W)", "Energy (kWh)", "Frequency (Hz)", "PF"]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=numeric_cols, how="any")

    return df


def main():
    st.set_page_config(
        page_title="Dashboard Energi ESP32",
        layout="wide",
    )

    st.title("⚡ Dashboard Energi ESP32 + PZEM004T")
    st.caption("Data diambil dari Google Sheets (via Apps Script + ESP32)")

    st.sidebar.header("Pengaturan")

    auto_refresh = st.sidebar.checkbox("Auto refresh setiap 5 detik", value=False)

    if st.sidebar.button("Refresh sekarang"):
        st.rerun()

    tarif = st.sidebar.number_input(
        "Tarif listrik (Rp / kWh)",
        min_value=0.0,
        value=1500.0,
        step=50.0,
    )
    hari_per_bulan = st.sidebar.number_input(
        "Asumsi hari per bulan",
        min_value=1,
        max_value=31,
        value=30,
    )

    try:
        df = load_data()
    except Exception as e:
        st.error(f"Gagal mengambil data dari Google Sheets: {e}")
        return

    if df.empty:
        st.warning("Belum ada data atau format kolom belum sesuai di Google Sheets.")
        return

    latest = df.iloc[-1]

    total_energy = df["Energy (kWh)"].max() - df["Energy (kWh)"].min()

    today_date = df["Timestamp"].iloc[-1].date()
    df_today = df[df["Timestamp"].dt.date == today_date]
    if len(df_today) > 1:
        energy_today = df_today["Energy (kWh)"].max() - df_today["Energy (kWh)"].min()
    else:
        energy_today = 0.0

    total_hours = (df["Timestamp"].iloc[-1] - df["Timestamp"].iloc[0]).total_seconds() / 3600.0
    if total_hours > 0:
        rate_kwh_per_hour = total_energy / total_hours
        monthly_kwh = rate_kwh_per_hour * 24.0 * hari_per_bulan
    else:
        rate_kwh_per_hour = 0.0
        monthly_kwh = 0.0

    cost_today = energy_today * tarif
    cost_monthly = monthly_kwh * tarif

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Daya sekarang (W)", f"{latest['Power (W)']:.2f}")
    with col2:
        st.metric("Energi hari ini (kWh)", f"{energy_today:.3f}")
    with col3:
        st.metric("Biaya hari ini (Rp)", f"{cost_today:,.0f}")
    with col4:
        st.metric(
            "Estimasi biaya / bulan (Rp)",
            f"{cost_monthly:,.0f}",
            help=f"Perkiraan berdasarkan rata-rata pemakaian {rate_kwh_per_hour:.3f} kWh/jam.",
        )

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["Grafik Daya", "Grafik Energi", "Data Mentah"])

    with tab1:
        st.subheader("Grafik Daya (W) vs Waktu")
        st.line_chart(
            df.set_index("Timestamp")[["Power (W)"]],
            use_container_width=True,
        )

    with tab2:
        st.subheader("Grafik Energi (kWh) vs Waktu")
        st.line_chart(
            df.set_index("Timestamp")[["Energy (kWh)"]],
            use_container_width=True,
        )

    with tab3:
        st.subheader("Data mentah (50 baris terakhir)")
        st.dataframe(
            df.sort_values("Timestamp", ascending=False).head(50),
            use_container_width=True,
        )

    if auto_refresh:
        time.sleep(5)
        st.rerun()


if __name__ == "__main__":
    main()
