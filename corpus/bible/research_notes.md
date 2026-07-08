# Research Notes: Data Centre Equipment & Standards
**Project Meridian Corpus Development**

This document records the research findings on realistic parameter ranges, standard CSI specification structures, and contract addendum formats to ensure industrial authenticity for the Project Meridian corpus.

---

## 1. Equipment Classes and Parameter Ranges

### 1.1. Static Uninterruptible Power Supply (UPS)
Based on systems like the **Vertiv Liebert EXL S1** and **Schneider Electric Galaxy VX**:
*   **Module Size:** 1.0 MW to 1.5 MW. For Project Meridian, we will use **1200 kW / 1200 kVA modules** (unity power factor, typical of modern transformerless double-conversion UPS systems).
*   **Operating Topology:** Double-conversion online mode (VFI-SS-111).
*   **Efficiency:** 
    *   Target: $\ge 96\%$ efficiency in double-conversion online mode across 50%, 75%, and 100% load points.
    *   ECO/VFD Mode: $\ge 99\%$.
*   **Battery System:** 
    *   Chemistry: Valve Regulated Lead-Acid (VRLA) or Lithium-ion. We will use VRLA in cabinets.
    *   DC Bus Voltage: Typically 480 VDC nominal (comprising 40 blocks of 12V batteries in series, or 240 cells of 2V).
    *   Runtime: 10 minutes at 100% full load ($1200\text{ kW}$).
*   **Input THDi:** $\le 5\%$ at full load.
*   **Standards:** IEC 62040-3 (performance and test requirements), UL 1778, IS 16242.

### 1.2. Standby Diesel Generator Sets
Based on systems like the **Caterpillar 3516C** and **Cummins QSK60**:
*   **Standby Rating:** 2500 kVA / 2000 ekW at $0.8\text{ PF}$, 50 Hz, 1500 RPM.
*   **Voltage:** 11 kV (medium voltage output connects directly to MV switchgear, standard for 20MW+ campuses).
*   **Fuel Autonomy:** 48 hours at full load.
*   **Ambient Reference Temperature:** 
    *   Manufacturer standard rating reference: $40^\circ\text{C}$ (or $25^\circ\text{C}$ per ISO 8528).
    *   Design basis ambient: $45^\circ\text{C}$.
    *   Derating curve: Typically $-1.0\%$ to $-2.0\%$ capacity per $1^\circ\text{C}$ rise above $40^\circ\text{C}$ ambient.
*   **Transient Load Acceptance:** 100% block load in a single step (per NFPA 110 Class 1, ISO 8528-5 G3).
*   **Standards:** ISO 8528, BS 5514, IS 10000, IS 13364.

### 1.3. Computer Room Air Handler (CRAH) Units
Based on systems like the **Vertiv Liebert PCW** and **Stulz CyberAir**:
*   **Sensible Cooling Capacity:** ~200 kW to 300 kW per unit. We will use **250 kW sensible cooling capacity**.
*   **Airflow Rate:** ~55,000 to 65,000 $\text{m}^3/\text{h}$ (approx. 32,000 to 38,000 CFM).
*   **Chilled Water Temperature Regime:**
    *   Entering Water Temperature: $10^\circ\text{C}$ (typical of medium-temperature chilled water systems).
    *   Leaving Water Temperature: $18^\circ\text{C}$ (Delta T of $8^\circ\text{C}$ or $8\text{ K}$).
*   **EC Fan Efficiency:** Modern EC fans consume ~4.5 kW to 6.0 kW at maximum airflow. Fan power density target is $< 0.10\text{ W}/(\text{m}^3/\text{h})$.
*   **Standards:** AHRI 1360 (performance rating of computer room air conditioners), ASHRAE 90.1, IS 1391.

### 1.4. Medium Voltage (MV) Switchgear
Based on systems like the **ABB UniGear ZS1** and **Schneider Electric Pix**:
*   **Rated Voltage:** 12 kV (for 11 kV nominal distribution).
*   **Rated Main Busbar Current:** 2000 A (sufficient for 20 MW load at 11 kV: $I = P / (\sqrt{3} \cdot V) \approx 20\text{MW} / (1.732 \cdot 11\text{kV}) \approx 1050\text{ A}$).
*   **Short-Time Withstand Current:** 26.3 kA (or 31.5 kA) for 3 seconds.
*   **Enclosure Rating:** IP4X (external panel protection), IP2X (internal compartments).
*   **Internal Arc Classification (IAC):** AFLR (Accessibility: Front, Lateral, Rear) rated for 31.5 kA for 1 second.
*   **Standards:** IEC 62271-200, IEC 62271-1, IS 3427, IS/IEC 62271.

### 1.5. Clean Agent Fire Suppression
Based on systems like the **Kidde ECS-500** and **Fike ADS** using FK-5-1-12 (Novec 1230):
*   **Agent Type:** FK-5-1-12 (Dodecafluoro-2-methylpentan-3-one).
*   **Discharge Time:** $\le 10$ seconds (NFPA 2001 standard).
*   **Hold Time (Retention):** $\ge 10$ minutes (600 seconds) to prevent re-ignition.
*   **Design Concentration:** 4.5% to 5.5% (v/v) for Class A/C hazards.
*   **NOAEL (No Observed Adverse Effect Level):** 10.0% (v/v).
*   **Safety Margin:** Design concentration is well below NOAEL, making it safe for occupied rooms.
*   **Standards:** NFPA 2001 (Clean Agent Fire Extinguishing Systems), UL 2166, IS 15493.

---

## 2. Document Conventions & Formats

### 2.1. CSI 3-Part Specification Section
Under the Construction Specifications Institute (CSI) MasterFormat, each technical specification section is organized into three distinct parts:
*   **PART 1 - GENERAL:** Defines the administrative and procedural requirements specific to the section.
    *   *1.1 Summary:* Describes the scope of work.
    *   *1.2 References:* Lists industry standards (e.g., IEC, IEEE, NFPA, IS).
    *   *1.3 Submittal Requirements:* Lists documents the contractor must submit for approval (product data, shop drawings, compliance statements, test reports).
    *   *1.4 Quality Assurance:* Manufacturer and installer qualifications.
*   **PART 2 - PRODUCTS:** Specifies the materials, equipment, and systems.
    *   *2.1 Acceptable Manufacturers:* List of approved brands.
    *   *2.2 Performance & Design Criteria:* Specific electrical/mechanical parameters, ratings, efficiencies, and redundancy requirements.
    *   *2.3 Component Description:* Detailed construction, enclosure type, accessories, and controls.
*   **PART 3 - EXECUTION:** Specifies the installation, testing, and commissioning requirements.
    *   *3.1 Examination and Preparation:* Site inspection.
    *   *3.2 Installation:* Physical mounting, electrical connections, clearances.
    *   *3.3 Field Quality Control:* Startup, site testing, and commissioning acceptance criteria.

### 2.2. Construction Addendum Format
An addendum is issued during the bidding/pre-construction phase to modify, delete, or insert requirements in the original contract documents. Standard amendments follow a structured "DELETE/INSERT" syntax:
*   **Header:** Identifies Addendum Number, Date, Project Name, Owner, and Consultant.
*   **Modification Syntax:**
    *   *Reference:* Section Number, Title, Page Number, and Article/Paragraph identifier.
    *   *Instruction:* E.g., "DELETE paragraph 2.3.A in its entirety and INSERT the following..."
    *   *Impact Summary:* Explicit list of affected drawings, specifications, or submittal packages.

---

## 3. Reference Material Citations
1.  *Vertiv Liebert EXL S1 UPS 1200kVA Technical Specification*, Vertiv Group Corp, 2024. [Vertiv EXL S1](https://www.vertiv.com).
2.  *Caterpillar C175-16 Standby Generator Technical Data Sheet (50 Hz)*, Caterpillar Inc., 2023. [Cat C175-16](https://www.cat.com).
3.  *ABB UniGear ZS1 Medium Voltage Switchgear Product Catalogue*, ABB Ltd, 2025. [ABB UniGear](https://www.abb.com).
4.  *Kidde ECS-500 Clean Agent Suppression System Manual*, Kidde-Fenwal Inc., 2023. [Kidde ECS-500](https://www.kidde.com).
5.  *CSI MasterFormat 2020 Edition*, Construction Specifications Institute.
6.  *NFPA 2001: Standard on Clean Agent Fire Extinguishing Systems (2018 Edition)*, National Fire Protection Association.
