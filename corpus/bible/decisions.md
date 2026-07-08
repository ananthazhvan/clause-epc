# Design Decisions Summary: Project Meridian
**Technical Choices and Configurations**

This document summarizes the specific engineering assumptions and design choices made to resolve open-ended requirements in the Project Meridian corpus design.

---

## 1. Electrical System & Voltages
*   **Utility Incoming Feed:** $11\text{ kV}$ (Medium Voltage, 3-phase, 50 Hz) from the local utility in Navi Mumbai.
*   **Distribution Voltage:** Stepped down to $415\text{ V}$ nominal (3-phase, 4-wire + Ground) for secondary distribution. Modern Indian and European data center standards specify a nominal $415/240\text{ V}$ low-voltage grid.
*   **UPS Voltage:** Rectifier input is $415\text{ VAC}$ (3-wire + Ground), Inverter output is $415\text{ VAC}$ (4-wire + Ground, providing a solid neutral for IT loads).
*   **Generator Voltage:** Standby generators will generate at $11\text{ kV}$ (Medium Voltage) to feed the main Medium Voltage Switchgear directly. This is standard practice in 20MW+ campuses to reduce power cable sizing, minimize voltage drop, and lower losses.

## 2. Campus Layout & Block Modularity
*   **IT Load Distribution:** The $20\text{ MW}$ IT load is split into **4 identical Server Halls**, each designed for a $5\text{ MW}$ IT load.
*   **Modular Infrastructure Blocks:**
    *   **UPS Systems:** Each of the 4 halls is served by an independent group of 6 UPS modules of $1200\text{ kW}$ each (5 active + 1 standby, N+1).
    *   **Cooling Systems:** Chilled water CRAH units are also grouped per hall, with 22 units of $250\text{ kW}$ sensible capacity each (21 active + 1 standby, N+1).
    *   This split-block modular layout makes the physical calculations realistic and represents standard hyperscale engineering practices.

## 3. Fuel Storage and Day Tanks
*   **Regulations (NFPA 30 / Local NBC):** Day tanks in enclosed generator rooms are capped at a maximum of $1,000\text{ Liters}$ ($264\text{ gallons}$) to limit fire risk. Therefore, we specify a local day tank capacity of **$990\text{ Liters}$** for each of the 16 generators.
*   **Bulk Fuel Storage:** Sized at $4 \times 100,000\text{ Liter}$ double-walled underground tanks to hold the required $399,360\text{ Liters}$ for 48 hours of campus-wide full load autonomy.

## 4. Chilled Water Cooling Regime
*   **Temperature Differential ($\Delta T$):** Sized for Entering Chilled Water at $10^\circ\text{C}$ and Leaving Chilled Water at $18^\circ\text{C}$ ($\Delta T = 8\text{ K}$). This high entering chilled water temperature is typical of modern high-efficiency chilled water plants operating with hot-aisle containment.
*   **CRAH Air Temperatures:** Return air (from hot aisle) is $35^\circ\text{C}$; supply air (to cold aisle) is $23^\circ\text{C}$ ($\Delta T_{air} = 12\text{ K}$).

## 5. Clean Agent Fire Suppression System
*   **Chemical Agent:** FK-5-1-12 (3M Novec 1230 / Kidde ECS-500 system).
*   **Obsolete Standard Reference:** Spec section 21 22 00 contains a planted reference to **NFPA 2001 (2008 Edition)**. The current valid standard is the 2018 or 2022 edition. NFPA 2001-2008 has been withdrawn/superseded.
*   **Design vs. Safety Concentrations:** Design concentration is set at **$4.7\%$** (v/v) for Class A/C hazards. The NOAEL limit for FK-5-1-12 is **$10.0\%$** (v/v), which results in a safe design margin.

## 6. Financial & Procurement Metadata
*   **PO Pricing and Lead Times:**
    *   *VoltEdge UPS Modules:* ₹2.5 Crore (25,000,000 INR) per unit. Lead time: 24 weeks.
    *   *Deccan Generator Sets:* ₹3.8 Crore (38,000,000 INR) per unit. Lead time: 40 weeks (critical path).
    *   *CryoCore CRAH Units:* ₹35 Lakh (3,500,000 INR) per unit. Lead time: 16 weeks (non-critical path).
    *   *Trident Switchgear Panels:* ₹1.2 Crore (12,000,000 INR) per panel. Lead time: 28 weeks.
    *   *AegisFire Systems:* ₹45 Lakh (4,500,000 INR) per server room. Lead time: 12 weeks.
