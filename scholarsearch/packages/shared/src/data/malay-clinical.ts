// ============================================
// Malay Clinical Vocabulary Crosswalk
// ============================================
//
// Intercepts Western medical terms and injects locally used
// clinical vernacular, brand names, and Malay/Manglish equivalents
// BEFORE compiling the AST for any source.
//
// This ensures Malaysian researchers find papers using terms they
// actually encounter in clinical practice.

import type { VocabularyEntry, RegionalOverlay } from "../utils/vocabulary-crosswalk.js";

export const malayClinicalData = {
  source: "malay_clinical",
  entries: [
    // === Common Medications ===
    {
      term: "acetaminophen",
      synonyms: ["paracetamol", "panadol", "pcm", "tylenol"],
      broaderTerms: ["analgesic", "antipyretic"],
      narrowerTerms: [],
      note: "Malaysian clinical practice uses paracetamol/panadol exclusively. Acetaminophen is rarely used in local prescriptions.",
      weight: 1.0,
    },
    {
      term: "ibuprofen",
      synonyms: ["brufen", "nurofen", "advil"],
      broaderTerms: ["nsaid", "anti-inflammatory"],
      narrowerTerms: [],
      note: "Common brand names in Malaysian pharmacies.",
      weight: 0.95,
    },
    {
      term: "metformin",
      synonyms: ["glucophage", "glucomet", "metformin hcl"],
      broaderTerms: ["oral hypoglycemic", "antidiabetic"],
      narrowerTerms: [],
      note: "First-line for type 2 diabetes in Malaysian clinical guidelines.",
      weight: 1.0,
    },
    {
      term: "atorvastatin",
      synonyms: ["lipitor", "atorvastatin calcium"],
      broaderTerms: ["statin", "lipid-lowering agent"],
      narrowerTerms: [],
      note: "Most prescribed statin in Malaysian public hospitals.",
      weight: 0.95,
    },
    {
      term: "amlodipine",
      synonyms: ["norvasc", "amlodipine besylate"],
      broaderTerms: ["calcium channel blocker", "antihypertensive"],
      narrowerTerms: [],
      note: "First-line antihypertensive in Malaysian MOH guidelines.",
      weight: 0.95,
    },

    // === Common Conditions (Malay terms) ===
    {
      term: "diabetes mellitus",
      synonyms: ["kencing manis", "diabetes", "dm", "penyakit gula"],
      broaderTerms: ["metabolic disorder", "endocrine disease"],
      narrowerTerms: ["type 2 diabetes", "gestational diabetes"],
      note: "'Kencing manis' is the colloquial Malay term used in patient education and rural health campaigns.",
      weight: 1.0,
    },
    {
      term: "hypertension",
      synonyms: ["darah tinggi", "hypertensi", "htn", "high blood pressure"],
      broaderTerms: ["cardiovascular disease"],
      narrowerTerms: ["essential hypertension", "secondary hypertension"],
      note: "'Darah tinggi' is universally understood by Malaysian patients and used in KKM health materials.",
      weight: 1.0,
    },
    {
      term: "hyperlipidemia",
      synonyms: ["darah berlemak", "kolesterol tinggi", "high cholesterol"],
      broaderTerms: ["lipid disorder", "metabolic syndrome"],
      narrowerTerms: ["hypercholesterolemia", "hypertriglyceridemia"],
      note: "'Darah berlemak' and 'kolesterol tinggi' are common patient-facing terms.",
      weight: 0.95,
    },
    {
      term: "asthma",
      synonyms: ["lelah", "asma", "penyakit lelah"],
      broaderTerms: ["respiratory disease", "allergic disease"],
      narrowerTerms: ["allergic asthma", "exercise-induced asthma"],
      note: "'Lelah' is the standard Malay term for asthma in clinical settings.",
      weight: 1.0,
    },
    {
      term: "chronic kidney disease",
      synonyms: ["buah pinggang", "ckd", "kidney failure", "kegagalan buah pinggang"],
      broaderTerms: ["renal disease"],
      narrowerTerms: ["end-stage renal disease", "diabetic nephropathy"],
      note: "'Buah pinggang' literally means kidney; 'kegagalan buah pinggang' for kidney failure.",
      weight: 1.0,
    },

    // === Clinical Procedures (Malay terms) ===
    {
      term: "blood pressure measurement",
      synonyms: ["ukur darah tinggi", "bp measurement", "blood pressure monitoring"],
      broaderTerms: ["vital signs", "clinical assessment"],
      narrowerTerms: [],
      weight: 0.9,
    },
    {
      term: "blood glucose monitoring",
      synonyms: ["ukur gula darah", "bg monitoring", "glucose check"],
      broaderTerms: ["diabetes management", "self-monitoring"],
      narrowerTerms: ["self-monitoring of blood glucose", "continuous glucose monitoring"],
      weight: 0.9,
    },
    {
      term: "electrocardiogram",
      synonyms: ["ecg", "ekg", "rekod jantung", "electric heart test"],
      broaderTerms: ["cardiac diagnostic test"],
      narrowerTerms: ["12-lead ecg", "holter monitoring"],
      note: "'Rekod jantung' is used in patient education materials.",
      weight: 0.95,
    },

    // === Ophthalmology (relevant to our dry eye use case) ===
    {
      term: "dry eye syndrome",
      synonyms: ["mata kering", "sindrom mata kering", "dry eye disease", "keratoconjunctivitis sicca"],
      broaderTerms: ["ocular surface disease"],
      narrowerTerms: ["aqueous deficient dry eye", "evaporative dry eye"],
      note: "'Mata kering' is the direct Malay translation used in Malaysian ophthalmology clinics.",
      weight: 1.0,
    },
    {
      term: "visual acuity",
      synonyms: ["ketajaman penglihatan", "va", "sharpness of vision"],
      broaderTerms: ["vision", "ocular function"],
      narrowerTerms: ["snellen acuity", "contrast sensitivity"],
      note: "'Ketajaman penglihatan' is the formal Malay term in ophthalmology.",
      weight: 1.0,
    },
    {
      term: "intraocular pressure",
      synonyms: ["tekanan dalam mata", "iop", "eye pressure"],
      broaderTerms: ["ocular measurement"],
      narrowerTerms: ["tonometry"],
      note: "'Tekanan dalam mata' is used in patient communication.",
      weight: 0.95,
    },
    {
      term: "cataract",
      synonyms: ["katarak", "kekeruhan kanta mata"],
      broaderTerms: ["lens disease", "visual impairment"],
      narrowerTerms: ["age-related cataract", "diabetic cataract"],
      note: "'Katarak' is the standard term in Malaysian ophthalmology.",
      weight: 1.0,
    },
    {
      term: "glaucoma",
      synonyms: ["glaukoma", "tekanan mata tinggi"],
      broaderTerms: ["optic neuropathy"],
      narrowerTerms: ["primary open-angle glaucoma", "angle-closure glaucoma"],
      note: "'Glaukoma' is the standard term; 'tekanan mata tinggi' (high eye pressure) is used in patient education.",
      weight: 1.0,
    },

    // === Public Health (Malaysian context) ===
    {
      term: "dengue fever",
      synonyms: ["denggi", "demam denggi", "dengue hemorrhagic fever"],
      broaderTerms: ["vector-borne disease", "tropical disease"],
      narrowerTerms: ["dengue hemorrhagic fever", "dengue shock syndrome"],
      note: "'Denggi' is universally used in Malaysian public health.",
      weight: 1.0,
    },
    {
      term: "malaria",
      synonyms: ["malaria", "demam malaria", "penyakit malaria"],
      broaderTerms: ["parasitic disease", "vector-borne disease"],
      narrowerTerms: ["plasmodium falciparum", "plasmodium vivax"],
      weight: 1.0,
    },
    {
      term: "tuberculosis",
      synonyms: ["tibi", "batuk kering", "tb", "penyakit tibi"],
      broaderTerms: ["infectious disease", "respiratory infection"],
      narrowerTerms: ["pulmonary tb", "extrapulmonary tb"],
      note: "'Tibi' is the common abbreviation; 'batuk kering' (dry cough) is a colloquial term.",
      weight: 1.0,
    },

    // === Mental Health ===
    {
      term: "depression",
      synonyms: [" kemurungan", "depresi", "major depressive disorder", "mdd"],
      broaderTerms: ["mental health", "mood disorder"],
      narrowerTerms: ["major depression", "persistent depressive disorder"],
      note: "'Kemurungan' is the formal Malay term used in Malaysian mental health services.",
      weight: 1.0,
    },
    {
      term: "anxiety",
      synonyms: ["kebimbangan", "anxieti", "anxiety disorder"],
      broaderTerms: ["mental health"],
      narrowerTerms: ["generalized anxiety disorder", "panic disorder"],
      note: "'Kebimbangan' is the formal Malay term.",
      weight: 0.95,
    },

    // === Paediatrics ===
    {
      term: "febrile seizure",
      synonyms: ["sawan demam", "seizur febril", "febrile convulsion"],
      broaderTerms: ["seizure", "paediatric emergency"],
      narrowerTerms: ["simple febrile seizure", "complex febrile seizure"],
      note: "'Sawan demam' is the Malay term commonly used by parents and in paediatric clinics.",
      weight: 1.0,
    },

    // === Diarrhoea/GI ===
    {
      term: "diarrhoea",
      synonyms: ["cirit-birit", "buang air besar", "bab", "loose stools"],
      broaderTerms: ["gastrointestinal symptom"],
      narrowerTerms: ["acute diarrhoea", "chronic diarrhoea", "bloody diarrhoea"],
      note: "'Cirit-birit' is formal; 'buang air besar' or 'BAB' is colloquial Manglish used in daily conversation.",
      weight: 1.0,
    },
    {
      term: "vomiting",
      synonyms: ["muntah", "muntah-muntah"],
      broaderTerms: ["gastrointestinal symptom"],
      narrowerTerms: ["hematemesis", "bilious vomiting"],
      note: "'Muntah' is the standard Malay term.",
      weight: 0.95,
    },

    // === Obstetrics/Gynae ===
    {
      term: "pregnancy",
      synonyms: ["hamil", "mengandung", "kehamilan"],
      broaderTerms: ["obstetrics"],
      narrowerTerms: ["first trimester", "third trimester"],
      note: "'Hamil' is formal Malay; 'mengandung' is also widely understood.",
      weight: 1.0,
    },
    {
      term: "gestational diabetes",
      synonyms: ["kencing manis semasa hamil", "gdm", "gestational diabetes mellitus"],
      broaderTerms: ["diabetes mellitus", "pregnancy complication"],
      narrowerTerms: [],
      note: "Malay translation commonly used in antenatal clinics.",
      weight: 0.95,
    },
  ],

  overlays: [
    // MY (Malaysia) overlay — primary target region
    {
      region: "MY",
      name: "Malaysian Clinical Vernacular",
      mappings: {
        // Western term → Malaysian equivalents
        "acetaminophen": ["paracetamol", "panadol"],
        "tylenol": ["paracetamol", "panadol"],
        "diabetes mellitus": ["kencing manis", "penyakit gula"],
        "hypertension": ["darah tinggi"],
        "hyperlipidemia": ["darah berlemak", "kolesterol tinggi"],
        "chronic kidney disease": ["buah pinggang", "kegagalan buah pinggang"],
        "dry eye syndrome": ["mata kering", "sindrom mata kering"],
        "visual acuity": ["ketajaman penglihatan"],
        "intraocular pressure": ["tekanan dalam mata", "tekanan mata"],
        "dengue fever": ["denggi", "demam denggi"],
        "tuberculosis": ["tibi", "batuk kering"],
        "depression": ["kemurungan"],
        "anxiety": ["kebimbangan"],
        "febrile seizure": ["sawan demam"],
        "diarrhoea": ["cirit-birit", "buang air besar", "BAB"],
        "vomiting": ["muntah"],
        "pregnancy": ["hamil", "mengandung"],
        "glaucoma": ["glaukoma", "tekanan mata tinggi"],
        "cataract": ["katarak"],
        "asthma": ["lelah", "asma"],
      },
      additions: [] as VocabularyEntry[],
      exclusions: new Set<string>(),
    },
  ] as RegionalOverlay[],
};
