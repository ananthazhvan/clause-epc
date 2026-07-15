Invented Errors & Answer Key
The generated PDF and CSV files contain the following test cases:

Category	Finding Description	Spec Reference	Test Document	Expected Verdict / Behavior
Redundancy	N+1 offered instead of required N+2	26 33 53 Part 2.1.2.A	SUB-263353-01-R0	DEVIATION (marked false_comply since compliance matrix claimed Comply)
Efficiency	95.5% efficiency offered instead of >= 96.0%	26 33 53 Part 2.3.4	SUB-263353-01-R0	DEVIATION (marked false_comply)
Addendum Blast Wave	96.2% offered in R1 becomes invalid after Addendum 3 raises spec requirement to >= 96.5%	26 33 53 Part 2.3.4	SUB-263353-01-R1	DEVIATION post-Addendum 3 (Verdict flipped COMPLY -> DEVIATION)
Statutory Code	Indoor day tank sized at 1200 L exceeds NBC fire-safety cap (< 1000 L)	26 32 13 Part 3.2.1.F	Spec HTML Linter	code_conflict spec lint warning
Contradiction	Spec mandates battery runtime of 10 mins in Part 2 and 12 mins in Part 3	26 33 53 Part 2.3.1.E vs Part 3.4.2.C	Spec HTML Linter	internal_contradiction spec lint warning
Withdrawn Std	References withdrawn NFPA 2001 (2008 Edition)	26 05 00 Part 1.2.1.A	Spec HTML Linter	withdrawn_standard spec lint warning
Qualitative	Demands adequate warranty without measurable metrics	26 33 53 Part 1.5.1.A	Spec HTML Linter	unverifiable_qualitative spec lint warning
Cross-Section	MV switchgear specifies UL-only standard (UL 347) conflicting with electrical umbrella IEC mandate	26 13 26 Part 1.2.1 vs 26 05 00 Part 1.4.3.B	Spec HTML Linter	cross_section_standard_conflict warning
