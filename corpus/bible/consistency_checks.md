# Physical Consistency Checks: Project Meridian
**Engineering Sizing & Math Verification**

This document presents the detailed engineering calculations to verify the physical coherence of all parameters in the Project Meridian campus design. These equations form the mathematical ground truth for the synthetic documents.

---

## 1. Campus Load and PUE Sizing

### 1.1. Campus Power Demands
*   **Design IT Load ($P_{IT}$):** $20,000\text{ kW}$ ($20\text{ MW}$).
*   **Target Power Usage Effectiveness ($\text{PUE}$):** $\le 1.45$.
*   **Total Campus Design Power ($P_{Campus}$):**
    $$P_{Campus} = P_{IT} \cdot \text{PUE} = 20,000\text{ kW} \cdot 1.45 = 29,000\text{ kW} \text{ (29.0 MW)}$$
    This total power includes IT load, cooling units, electrical distribution losses, lighting, and auxiliary systems.

---

## 2. Static UPS System Sizing

### 2.1. Redundancy Configuration
To improve fault isolation, the $20\text{ MW}$ IT load is distributed across **4 independent Server Halls**, each with a design load of:
$$P_{Hall} = \frac{20,000\text{ kW}}{4} = 5,000\text{ kW}$$

*   **UPS Module Capacity:** $1200\text{ kW}$ at unity power factor ($1200\text{ kVA}$).
*   **N+1 Redundancy per Hall:**
    *   Active modules required: $\lceil 5,000\text{ kW} / 1200\text{ kW} \rceil = 5$ modules.
    *   Redundant module: $+1$ module.
    *   Total modules per group: $5 + 1 = 6$ modules.
    *   Group capacity: $6 \cdot 1200\text{ kW} = 7200\text{ kW}$ (with $1200\text{ kW}$ redundancy).
*   **Campus-Wide Totals:**
    *   Total UPS Modules: $4 \text{ groups} \cdot 6 \text{ modules/group} = 24 \text{ modules}$.
    *   Total Installed UPS Capacity: $24 \cdot 1200\text{ kW} = 28,800\text{ kW}$.

### 2.2. Battery Sizing Calculation (Static UPS)
*   **Module Load ($P_{module}$):** $1200\text{ kW}$ at $100\%$ load.
*   **Inverter Efficiency ($\eta_{inv}$):** $97\%$ ($0.97$).
*   **DC Power Required from Battery ($P_{DC}$):**
    $$P_{DC} = \frac{P_{module}}{\eta_{inv}} = \frac{1200\text{ kW}}{0.97} \approx 1237.11\text{ kW} \text{ (1,237,113 W)}$$
*   **Nominal Battery DC Bus Voltage ($V_{nominal}$):** $480\text{ VDC}$ (composed of $40 \text{ blocks}$ of $12\text{V}$ batteries in series, or $240\text{ cells}$ of $2\text{V}$ nominal).
*   **Required Run Time ($t$):** $10\text{ minutes}$ ($0.167\text{ hours}$).
*   **DC Energy Delivered during Discharge ($E_{DC}$):**
    $$E_{DC} = P_{DC} \cdot t = 1237.11\text{ kW} \cdot \frac{10}{60}\text{ h} \approx 206.19\text{ kWh}$$
*   **Battery Capacity Sizing:**
    Due to internal resistance and chemical reaction limits, a battery discharged at the 10-minute rate (high-rate discharge) delivers only a fraction of its nominal capacity (rated at the 10-hour rate, C10). The C10-to-10-minute discharge efficiency factor is set to exactly $0.36$.
    *   Required Nominal Battery Energy Capacity ($E_{nominal}$):
        $$E_{nominal} = \frac{E_{DC}}{0.36} = \frac{206.19\text{ kWh}}{0.36} \approx 572.75\text{ kWh}$$
    *   Required Nominal Battery Bank Ampere-Hours ($C_{10}$):
        $$C_{10} = \frac{E_{nominal}}{V_{nominal}} = \frac{572,750\text{ Wh}}{480\text{ V}} \approx 1193.2\text{ Ah}$$
    *   **Implementation:** We use **6 parallel strings** of **200 Ah (C10)** battery blocks.
        *   Nominal capacity: $6 \cdot 200\text{ Ah} = 1200\text{ Ah}$ at $480\text{ VDC}$.
        *   Nominal energy: $1200\text{ Ah} \cdot 480\text{ V} = 576\text{ kWh}$.
        *   This nominal bank capacity (1200 Ah) successfully covers the required $1193.2\text{ Ah}$ at the 10-minute discharge rate under the $0.36$ factor.

---

## 3. Standby Generator Sizing & Autonomy

### 3.1. Generator Capacity and Redundancy
*   **Total Campus Peak Load ($P_{Campus}$):** $29,000\text{ kW}$ ($36,250\text{ kVA}$ at $0.8\text{ PF}$).
*   **Generator Rating:** $2500\text{ kVA}$ Standby ($2000\text{ kWe}$ at $0.8\text{ PF}$).
*   **N+1 Redundancy:**
    *   Active generators required for peak load: $\lceil 29,000\text{ kW} / 2000\text{ kW} \rceil = 15$ units.
    *   Redundant generator: $+1$ unit.
    *   Total campus generators: $15 + 1 = 16$ units.
    *   Total active capacity (under N+1, with 1 unit down): $15 \cdot 2000\text{ kW} = 30,000\text{ kW}$ (exceeds $29,000\text{ kW}$ peak load by $1000\text{ kW}$, providing margin).

### 3.2. Fuel Consumption and Bulk Storage Autonomy
*   **Autonomy Target:** 48 hours of continuous operation at full standby load ($2000\text{ kWe}$).
*   **Fuel Consumption Rate per Generator ($F_{rate}$):** $520\text{ L/h}$ at 100% load.
    *(Corresponds to a thermal efficiency of $\approx 39.5\%$ assuming diesel energy density of $38\text{ MJ/L}$ or $10\text{ kWh/L}$)*.
*   **Total Fuel Volume per Generator for 48 Hours ($V_{gen}$):**
    $$V_{gen} = 520\text{ L/h} \cdot 48\text{ h} = 24,960\text{ Liters}$$
*   **Total Campus Bulk Fuel Storage Required ($V_{total}$):**
    $$V_{total} = 16 \text{ generators} \cdot 24,960\text{ L/generator} = 399,360\text{ Liters}$$
    *   **Storage Design:** We will provision **4 bulk storage tanks of 100,000 Liters each** (total $400,000\text{ Liters}$).
    *   **Day Tanks:** Each generator room is equipped with a local **990 Liter day tank** (satisfying local safety codes that restrict day tanks to $<1000\text{ L}$ to limit fire load).

---

## 4. CRAH (Cooling) Unit Sizing

### 4.1. Cooling Load and Redundancy
*   **IT Heat Rejection:** $20,000\text{ kW}$ (at steady-state, 100% of IT load is converted to heat).
*   **UPS Heat Loss:** Assuming UPS operates at 96% efficiency (4% heat loss):
    $$Q_{UPS} = \frac{20,000\text{ kW}}{0.96} \cdot 0.04 \approx 833.3\text{ kW}$$
*   **Lighting and Auxiliary Heat Loads:** $\approx 166.7\text{ kW}$.
*   **Total Campus Sensible Heat Load ($Q_{sensible}$):**
    $$Q_{sensible} = 20,000 + 833.3 + 166.7 = 21,000\text{ kW} \text{ (21 MW)}$$
*   **Sensible Cooling per Server Hall:**
    $$Q_{Hall} = \frac{21,000\text{ kW}}{4} = 5,250\text{ kW}$$
*   **CRAH Unit Capacity:** $250\text{ kW}$ sensible cooling capacity.
*   **N+1 Redundancy per Server Hall:**
    *   Active CRAH units required: $\lceil 5,250\text{ kW} / 250\text{ kW} \rceil = 21$ units.
    *   Redundant CRAH unit: $+1$ unit.
    *   Total units per hall: $22$ units.
    *   Total campus CRAH units: $4 \text{ halls} \cdot 22 \text{ units/hall} = 88$ units.

### 4.2. Airflow Side Consistency
*   **CRAH Sensible Capacity ($Q_{crah}$):** $250\text{ kW} = 250,000\text{ W}$.
*   **Server Return Air Temperature ($T_{return}$):** $35^\circ\text{C}$ (hot aisle containment).
*   **Server Supply Air Temperature ($T_{supply}$):** $23^\circ\text{C}$ (cold aisle target).
*   **Air Temperature Temperature Delta ($\Delta T_{air}$):** $35^\circ\text{C} - 23^\circ\text{C} = 12\text{ K}$.
*   **Properties of Dry Air at $30^\circ\text{C}$ average:**
    *   Density ($\rho$): $1.16\text{ kg/m}^3$.
    *   Specific Heat Capacity ($C_p$): $1.005\text{ kJ/(kg}\cdot\text{K)} = 1005\text{ J/(kg}\cdot\text{K)}$.
*   **Required Volumetric Airflow ($\dot{V}$):**
    $$\dot{V} = \frac{Q_{crah}}{\rho \cdot C_p \cdot \Delta T_{air}} = \frac{250,000\text{ W}}{1.16\text{ kg/m}^3 \cdot 1005\text{ J/(kg}\cdot\text{K)} \cdot 12\text{ K}} \approx 17.867\text{ m}^3\text{/s}$$
    $$\dot{V}_{hourly} = 17.867\text{ m}^3\text{/s} \cdot 3600\text{ s/h} \approx 64,320\text{ m}^3\text{/h}$$
    This matches the vendor spec sheet airflow of **$64,320\text{ m}^3/\text{h}$** (approx. $37,850\text{ CFM}$).

### 4.3. Water Side Consistency
*   **Entering Chilled Water Temperature ($T_{in}$):** $10^\circ\text{C}$.
*   **Leaving Chilled Water Temperature ($T_{out}$):** $18^\circ\text{C}$.
*   **Water Temperature Delta ($\Delta T_{water}$):** $18^\circ\text{C} - 10^\circ\text{C} = 8\text{ K}$.
*   **Specific Heat of Water ($C_{p,water}$):** $4.187\text{ kJ/(kg}\cdot\text{K)}$.
*   **Required Water Mass Flow Rate ($\dot{m}_{water}$):**
    $$\dot{m}_{water} = \frac{Q_{crah}}{C_{p,water} \cdot \Delta T_{water}} = \frac{250\text{ kW}}{4.187\text{ kJ/(kg}\cdot\text{K)} \cdot 8\text{ K}} \approx 7.464\text{ kg/s} \approx 7.464\text{ L/s}$$
    $$\dot{V}_{water, hourly} = 7.464\text{ L/s} \cdot 3.6 = 26.87\text{ m}^3\text{/h}$$
    *(Corresponding to $118.3\text{ GPM}$ per unit)*. This water flow is standard and easily handled by a $65\text{ mm}$ (2.5-inch) control valve.
