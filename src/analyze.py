from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[1]
FIRMS_FILE = ROOT / "data/raw/firms_indonesia.csv"
SALES_FILE = ROOT / "data/raw/mask_sales_demo.csv"
OUT = ROOT / "data/processed"
FIG = ROOT / "reports/figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

if not FIRMS_FILE.exists():
    raise FileNotFoundError(
        "Letakkan CSV NASA FIRMS di data/raw/firms_indonesia.csv. "
        "Lihat README.md untuk sumber dan format data."
    )

fires = pd.read_csv(FIRMS_FILE)
required = {"acq_date", "latitude", "longitude"}
missing = required - set(fires.columns)
if missing:
    raise ValueError(f"Kolom FIRMS tidak ditemukan: {sorted(missing)}")

fires["acq_date"] = pd.to_datetime(fires["acq_date"], errors="coerce")
fires = fires.dropna(subset=["acq_date"])
# Opsional: filter confidence untuk format kategorikal FIRMS.
if "confidence" in fires.columns and fires["confidence"].dtype == "object":
    fires["confidence"] = fires["confidence"].astype(str).str.lower()
    fires = fires[fires["confidence"].isin(["nominal", "high"])]

fires["month"] = fires["acq_date"].dt.to_period("M").dt.to_timestamp()
monthly_fires = (fires.groupby("month")
                 .size().rename("hotspot_count").reset_index())
monthly_fires.to_csv(OUT / "monthly_hotspots.csv", index=False)

sales = pd.read_csv(SALES_FILE)
sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
sales = sales.dropna(subset=["date"])
sales["month"] = sales["date"].dt.to_period("M").dt.to_timestamp()
monthly_sales = sales.groupby("month", as_index=False).agg(
    units_sold=("units_sold", "sum"), revenue_idr=("revenue_idr", "sum")
)
combined = monthly_fires.merge(monthly_sales, on="month", how="inner")
combined.to_csv(OUT / "monthly_analysis_dataset.csv", index=False)

sns.set_theme(style="whitegrid")
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(monthly_fires["month"], monthly_fires["hotspot_count"])
ax.set(title="Monthly Hotspot Detections – Indonesia",
       xlabel="Month", ylabel="Hotspot detections")
fig.tight_layout()
fig.savefig(FIG / "monthly_hotspot_trend.png", dpi=160)
plt.close(fig)

if len(combined) >= 3:
    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax1.plot(combined["month"], combined["hotspot_count"], label="Hotspots")
    ax1.set_ylabel("Hotspot detections")
    ax2 = ax1.twinx()
    ax2.plot(combined["month"], combined["units_sold"], label="Mask units sold",
             linestyle="--")
    ax2.set_ylabel("Mask units sold")
    ax1.set_title("Hotspots vs Mask Sales (check sales data status before interpretation)")
    fig.tight_layout()
    fig.savefig(FIG / "hotspots_vs_mask_sales.png", dpi=160)
    plt.close(fig)

    pearson = pearsonr(combined["hotspot_count"], combined["units_sold"])
    spearman = spearmanr(combined["hotspot_count"], combined["units_sold"])
    print(f"Pearson r={pearson.statistic:.3f}, p-value={pearson.pvalue:.4g}")
    print(f"Spearman rho={spearman.statistic:.3f}, p-value={spearman.pvalue:.4g}")
else:
    print("Data gabungan kurang dari 3 bulan; korelasi tidak dihitung.")

print(f"Jumlah bulan hotspot: {len(monthly_fires)}")
print(f"Jumlah bulan data gabungan: {len(combined)}")
print("Perhatian: data penjualan demo adalah simulasi, bukan transaksi riil.")
