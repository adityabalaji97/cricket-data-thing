# New Dataset Validation Report

Generated: 2025-12-18 14:39:46

## Match ID Analysis

- **Matches in new dataset**: 9,342
- **Matches in existing DB**: 7,981
- **Overlapping matches**: 6,638
- **New matches only** (not in DB): 2,704
- **Existing matches only** (no enhanced data): 1,343

## Player Name Analysis

- **Exact name matches**: 1,610
- **Players in new only**: 6,688
- **Players in existing only**: 4,212

### Sample New-Only Players (first 50)

- A Aravinddaraj
- A Warnakulasuriya
- AKV Tyrone
- Aadil Ali
- Aaftab Limdawala
- Aahan Gopinath Achar
- Aakarshit Gomel
- Aamer Ijaz
- Aanand Pandey
- Aaqib Khan
- Aaqib Liaquat
- Aarin Nadkarni
- Aaron Ayre
- Aaron Cawley
- Aaron Finch
- Aaron Gillespie
- Aaron Hardie
- Aaron Heywood
- Aaron Johnson
- Aaron Muslar
- Aaron Phangiso
- Aaron Summers
- Aaron Thomason
- Aarush Bhagwat
- Aarya Desai
- Aaryan Menon
- Aaryan Modi
- Aayush Thakur
- Abass Gbla
- Abbas Musa
- Abdallah Jabiri
- Abdollah Ahmadzai
- Abdoulaye Aminou
- Abdul Ameer
- Abdul Baqi
- Abdul Bhikari
- Abdul Gaffar
- Abdul Gaffar Saqlain
- Abdul Hadi
- Abdul Hakam
- Abdul Halim
- Abdul Hashmi
- Abdul Kayium
- Abdul Latif Ayoubi
- Abdul Makda
- Abdul Malik
- Abdul Rahman Bhadelia
- Abdul Razak
- Abdul Wasi
- Abdullah

## Ball-Level Integrity

| Match ID | New Count | Existing Count | Match |
|----------|-----------|----------------|-------|
| 1507418 | 28 | 53 | ⚠ |
| 1310901 | 246 | 246 | ✓ |
| 1310902 | 210 | 210 | ✓ |
| 1310938 | 249 | 249 | ✓ |
| 1310939 | 236 | 236 | ✓ |

## Recommendations

1. **6,638 matches can be enhanced** with wagon wheel and shot data
2. **2,704 new matches** available - consider adding to main database

### Next Steps

1. Create `delivery_details` table for enhanced ball data
2. Load overlapping match data first
3. Evaluate whether to add new-only matches to main tables
4. Build player ID mapping table for cleaner references
