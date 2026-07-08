import matplotlib.pyplot as plt
import numpy as np
import os

def generate_curves():
    os.makedirs("corpus/rendered/assets", exist_ok=True)
    
    # 1. Deccan Generator Derating Curve
    temp = np.arange(20, 51, 1)
    # 2500 kVA up to 40C, then derating by -2% per degree C above 40C
    capacity = []
    for t in temp:
        if t <= 40:
            capacity.append(2500.0)
        else:
            # -2% per degree above 40C
            capacity.append(2500.0 * (1.0 - 0.02 * (t - 40)))
            
    plt.figure(figsize=(6, 4))
    plt.plot(temp, capacity, label="Standby Rating (kVA)", color="#d32f2f", linewidth=2.5)
    plt.axvline(x=40, color="gray", linestyle="--", label="Ref Ambient (40°C)")
    plt.axvline(x=45, color="blue", linestyle=":", label="Site Ambient (45°C)")
    plt.scatter([40, 45], [2500, 2250], color="black", zorder=5) # 2250 is the curve rating at 45C
    # Let's label the points
    plt.annotate("2500 kVA @ 40°C", (40, 2500), textcoords="offset points", xytext=(10,10), ha='left', fontsize=9)
    plt.annotate("2250 kVA @ 45°C (-10%)", (45, 2250), textcoords="offset points", xytext=(10,-15), ha='left', fontsize=9)
    
    plt.title("Deccan DD-2500 Ambient Temperature Derating Curve", fontsize=11, fontweight="bold", pad=10)
    plt.xlabel("Ambient Temperature (°C)", fontsize=9)
    plt.ylabel("Standby Rating (kVA)", fontsize=9)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(fontsize=8, loc="lower left")
    plt.tight_layout()
    plt.savefig("corpus/rendered/assets/gen_derating_curve.png", dpi=150)
    plt.close()
    
    # 2. UPS Efficiency Curves (R0 and R1)
    load = np.arange(10, 101, 5)
    
    # VFI efficiency curve for R0 (95.1% at 50%, 96.0% at 75%, 96.2% at 100% load)
    # Let's fit a simple quadratic curve to these three points: (50, 95.1), (75, 96.0), (100, 96.2)
    # A*x^2 + B*x + C = eff
    x_points = [50, 75, 100]
    y_points_r0 = [95.1, 96.0, 96.2]
    y_points_r1 = [96.2, 96.0, 96.2] # R1 has 96.2% at 50%, 96.0% at 75%, 96.2% at 100%
    
    p_r0 = np.polyfit(x_points, y_points_r0, 2)
    p_r1 = np.polyfit(x_points, y_points_r1, 2)
    
    eff_r0 = np.polyval(p_r0, load)
    eff_r1 = np.polyval(p_r1, load)
    
    plt.figure(figsize=(6, 4))
    plt.plot(load, eff_r0, label="VoltEdge R0 VFI Online Mode", color="#ff9800", linewidth=2.5)
    plt.plot(load, eff_r1, label="VoltEdge R1 VFI Online Mode", color="#4caf50", linewidth=2.5)
    plt.plot(load, [99.1] * len(load), label="ECO Mode (VFD)", color="#2196f3", linestyle="--", linewidth=2)
    
    plt.scatter(x_points, y_points_r0, color="#ff5722", zorder=5)
    plt.scatter(x_points, y_points_r1, color="#2e7d32", zorder=5)
    
    plt.title("VoltEdge PX-1200 UPS Operating Efficiency Curves", fontsize=11, fontweight="bold", pad=10)
    plt.xlabel("UPS Load (%)", fontsize=9)
    plt.ylabel("Efficiency (%)", fontsize=9)
    plt.ylim(90, 100)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(fontsize=8, loc="lower right")
    plt.tight_layout()
    plt.savefig("corpus/rendered/assets/ups_efficiency_curve.png", dpi=150)
    plt.close()
    
    print("Generated curve charts successfully under corpus/rendered/assets/")

if __name__ == "__main__":
    generate_curves()
