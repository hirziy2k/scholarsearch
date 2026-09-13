// ============================================
// Dry Eye Disease Domain Vocabulary
// ============================================
//
// Comprehensive controlled vocabulary for dry eye disease (DED) research.
// Maps clinical terms, diagnostic instruments, treatments, and related
// psychosocial constructs to enable precise query expansion.
//
// Sources: TFOS DEWS II, AAO Preferred Practice Patterns, MeSH descriptors

import type { VocabularyEntry, RegionalOverlay } from "../utils/vocabulary-crosswalk.js";

// ============================================
// Core Disease Terms
// ============================================

const DRY_EYE_DISEASE_TERMS: VocabularyEntry[] = [
  // --- Primary Disease Names ---
  {
    term: "dry eye disease",
    synonyms: ["dry eye", "dry eye syndrome", "keratoconjunctivitis sicca", "ded", "des"],
    broaderTerms: ["ocular surface disease"],
    narrowerTerms: ["aqueous deficient dry eye", "evaporative dry eye", "mixed dry eye"],
    note: "TFOS DEWS II preferred terminology. 'Dry eye disease' over 'dry eye syndrome'.",
    weight: 1.0,
  },
  {
    term: "aqueous deficient dry eye",
    synonyms: ["adde", "sicca syndrome", "aqueous tear deficiency", "atd"],
    broaderTerms: ["dry eye disease"],
    narrowerTerms: ["sjogren syndrome dry eye", "non-sjogren aqueous deficiency"],
    note: "Subtype characterized by reduced lacrimal gland secretion.",
    weight: 0.95,
  },
  {
    term: "evaporative dry eye",
    synonyms: ["ede", "meibomian gland dysfunction", "mgd", "lipid deficiency dry eye"],
    broaderTerms: ["dry eye disease"],
    narrowerTerms: ["meibomian gland dysfunction", "lid margin disease", "contact lens related dry eye"],
    note: "Subtype characterized by increased tear film evaporation.",
    weight: 0.95,
  },
  {
    term: "meibomian gland dysfunction",
    synonyms: ["mgd", "meibomitis", " posterior blepharitis", "meibomian gland obstruction"],
    broaderTerms: ["evaporative dry eye", "lid margin disease"],
    narrowerTerms: ["hyposecretory mgd", "hypersecretory mgd", "obstructive mgd"],
    note: "Most common cause of evaporative dry eye.",
    weight: 0.95,
  },
  {
    term: "sjogren syndrome",
    synonyms: ["sjögren syndrome", "sicca complex", "sicca syndrome"],
    broaderTerms: ["autoimmune disease", "aqueous deficient dry eye"],
    narrowerTerms: ["primary sjogren syndrome", "secondary sjogren syndrome"],
    note: "Systemic autoimmune condition causing severe dry eye and dry mouth.",
    weight: 0.9,
  },

  // --- Symptoms ---
  {
    term: "dry eye symptoms",
    synonyms: ["symptoms of dry eye", "dry eye complaints", "ocular surface symptoms"],
    broaderTerms: ["dry eye disease"],
    narrowerTerms: ["eye dryness", "burning sensation", "foreign body sensation", "photophobia"],
    note: "Patient-reported symptoms including grittiness, burning, and fluctuating vision.",
    weight: 1.0,
  },
  {
    term: "eye dryness",
    synonyms: ["ocular dryness", "dryness of eyes", "feeling of dry eyes"],
    broaderTerms: ["dry eye symptoms"],
    narrowerTerms: [],
    weight: 0.95,
  },
  {
    term: "burning sensation",
    synonyms: ["eye burning", "ocular burning", "burning eyes", "stinging eyes"],
    broaderTerms: ["dry eye symptoms"],
    narrowerTerms: [],
    weight: 0.9,
  },
  {
    term: "foreign body sensation",
    synonyms: ["gritty feeling", "sand in eyes", "sandpaper eyes", "fbs"],
    broaderTerms: ["dry eye symptoms"],
    narrowerTerms: [],
    note: "Common patient description of dry eye discomfort.",
    weight: 0.9,
  },
  {
    term: "photophobia",
    synonyms: ["light sensitivity", "sensitivity to light", "glare sensitivity"],
    broaderTerms: ["dry eye symptoms", "visual symptoms"],
    narrowerTerms: [],
    weight: 0.85,
  },
  {
    term: "epiphora",
    synonyms: ["watering eyes", "tearing", "excessive tearing", "reflex tearing"],
    broaderTerms: ["dry eye symptoms"],
    narrowerTerms: [],
    note: "Paradoxical excessive tearing in dry eye due to reflex stimulation.",
    weight: 0.9,
  },
  {
    term: "visual fluctuation",
    synonyms: ["fluctuating vision", "blurry vision", "vision changes", "visual variability"],
    broaderTerms: ["dry eye symptoms", "visual symptoms"],
    narrowerTerms: [],
    note: "Vision that worsens throughout the day, especially with reading/screens.",
    weight: 0.9,
  },
  {
    term: "eye fatigue",
    synonyms: ["asthenopia", "eye strain", "visual fatigue", "tired eyes"],
    broaderTerms: ["dry eye symptoms", "visual symptoms"],
    narrowerTerms: [],
    weight: 0.85,
  },
  {
    term: "eye redness",
    synonyms: ["ocular redness", "red eyes", "bloodshot eyes", "conjunctival injection"],
    broaderTerms: ["dry eye symptoms", "clinical signs"],
    narrowerTerms: [],
    weight: 0.85,
  },

  // --- Clinical Signs ---
  {
    term: "tear film instability",
    synonyms: ["tear film break-up", "tbut", "nIBUT", "tear breakup time", "tear break up time"],
    broaderTerms: ["dry eye disease", "tear film disorders"],
    narrowerTerms: ["non-invasive tear break-up time", "fluorescein tear break-up time"],
    note: "Key diagnostic criterion. NIBUT preferred over fluorescein TBUT.",
    weight: 1.0,
  },
  {
    term: "tear film break-up time",
    synonyms: ["tbut", "tear breakup time", "fluorescein breakup time"],
    broaderTerms: ["tear film instability"],
    narrowerTerms: [],
    note: "Time between last blink and first break in tear film. <10s = abnormal.",
    weight: 0.95,
  },
  {
    term: "non-invasive tear break-up time",
    synonyms: ["nIBUT", "non-invasive breakup time", "nIBUT"],
    broaderTerms: ["tear film instability"],
    narrowerTerms: [],
    note: "NIBUT without fluorescein staining. More physiological than fluorescein TBUT.",
    weight: 0.95,
  },
  {
    term: "corneal staining",
    synonyms: ["corneal fluorescein staining", "cfs", "corneal epitheliopathy"],
    broaderTerms: ["dry eye disease", "ocular surface damage"],
    narrowerTerms: ["central corneal staining", "peripheral corneal staining"],
    note: "Indicates corneal epithelial damage from dry eye.",
    weight: 0.9,
  },
  {
    term: "conjunctival staining",
    synonyms: ["conjunctival fluorescein staining", "lissamine green staining"],
    broaderTerms: ["ocular surface damage"],
    narrowerTerms: [],
    weight: 0.85,
  },
  {
    term: "osmolarity",
    synonyms: ["tear osmolarity", "tear film osmolarity", "hyperosmolarity"],
    broaderTerms: ["dry eye disease", "tear film disorders"],
    narrowerTerms: [],
    note: "Tear osmolarity >308 mOsm/L or inter-eye difference >8 mOsm/L is abnormal.",
    weight: 0.9,
  },
  {
    term: "tear meniscus height",
    synonyms: ["lower tear meniscus", "ltm", "tear meniscus"],
    broaderTerms: ["dry eye disease"],
    narrowerTerms: [],
    note: "Reflects tear volume. <0.2mm suggests aqueous deficiency.",
    weight: 0.85,
  },
  {
    term: "meibography",
    synonyms: ["meibomian gland imaging", "meibomian gland morphology"],
    broaderTerms: ["dry eye disease", "meibomian gland dysfunction"],
    narrowerTerms: [],
    note: "Imaging of meibomian gland structure. Loss >33% indicates dropout.",
    weight: 0.85,
  },

  // --- Diagnostic Instruments ---
  {
    term: "ocular surface disease index",
    synonyms: ["osdi", "osdi questionnaire"],
    broaderTerms: ["dry eye questionnaires", "patient-reported outcomes"],
    narrowerTerms: [],
    note: "12-item validated questionnaire. Score 0-100: normal <20, mild 20-32, moderate 33-52, severe >52.",
    weight: 1.0,
  },
  {
    term: "dry eye questionnaire",
    synonyms: ["deq", "dry eye questionnaire 5", "deq5", "deq-5"],
    broaderTerms: ["dry eye questionnaires"],
    narrowerTerms: ["deq5", "deq-100"],
    weight: 0.9,
  },
  {
    term: "national eye institute visual function questionnaire",
    synonyms: ["nei-vfq", "vfq-25", "vfq", "visual function questionnaire"],
    broaderTerms: ["patient-reported outcomes", "visual quality of life"],
    narrowerTerms: ["vfq-25", "vfq-39"],
    note: "Assesses vision-related quality of life across multiple domains.",
    weight: 0.9,
  },
  {
    term: "impact of dry eye on everyday life",
    synonyms: ["ideal", "ideel questionnaire"],
    broaderTerms: ["dry eye questionnaires"],
    narrowerTerms: [],
    note: "Dry eye-specific quality of life instrument.",
    weight: 0.85,
  },
  {
    term: "speed questionnaire",
    synonyms: ["surface disease index", "speed"],
    broaderTerms: ["dry eye questionnaires"],
    narrowerTerms: [],
    weight: 0.8,
  },

  // --- Treatments ---
  {
    term: "artificial tears",
    synonyms: ["lubricant eye drops", "tear supplements", "ocular lubricants", "eye drops for dry eye"],
    broaderTerms: ["dry eye treatment"],
    narrowerTerms: ["preservative-free artificial tears", "preserved artificial tears", "gel tears", "cream-based lubricants"],
    note: "First-line treatment for all types of dry eye.",
    weight: 1.0,
  },
  {
    term: "cyclosporine",
    synonyms: ["cyclosporine a", "csa", "restasis", "cequa", "ikervis"],
    broaderTerms: ["dry eye treatment", "immunomodulator"],
    narrowerTerms: ["cyclosporine 0.05%", "cyclosporine 0.1%", "cyclosporine nanoemulsion"],
    note: "Topical immunomodulator for moderate-severe dry eye. Takes 3-6 months for full effect.",
    weight: 0.95,
  },
  {
    term: "lifitegrast",
    synonyms: ["xiidra", "lifitegrast ophthalmic solution"],
    broaderTerms: ["dry eye treatment", "lfa antagonist"],
    narrowerTerms: [],
    note: "LFA-1 antagonist. FDA-approved for DED. Faster onset than cyclosporine.",
    weight: 0.9,
  },
  {
    term: "punctal plugs",
    synonyms: ["punctal occlusion", "tear duct plugs", "silicone plugs"],
    broaderTerms: ["dry eye treatment"],
    narrowerTerms: ["temporary punctal plugs", "permanent punctal plugs", "punctal cauterization"],
    note: "Occludes lacrimal punctum to retain tears. Used for aqueous deficiency.",
    weight: 0.85,
  },
  {
    term: "omega-3 fatty acids",
    synonyms: ["omega-3", "fish oil", "essential fatty acids", "efas"],
    broaderTerms: ["dry eye treatment", "nutritional supplementation"],
    narrowerTerms: [],
    note: "Oral supplementation. Some evidence for reducing DED symptoms and MGD.",
    weight: 0.8,
  },
  {
    term: "warm compresses",
    synonyms: ["warm compress", "hot compress", "warm towel on eyes"],
    broaderTerms: ["dry eye treatment", "meibomian gland dysfunction treatment"],
    narrowerTerms: [],
    note: "First-line for MGD. Helps melt meibum and improve gland expression.",
    weight: 0.8,
  },
  {
    term: "lid hygiene",
    synonyms: ["lid scrub", "eyelid cleaning", "lid margin hygiene"],
    broaderTerms: ["dry eye treatment", "meibomian gland dysfunction treatment"],
    narrowerTerms: [],
    weight: 0.75,
  },
  {
    term: "autologous serum tears",
    synonyms: ["ast", "serum tears", "own blood eye drops"],
    broaderTerms: ["dry eye treatment"],
    narrowerTerms: [],
    note: "Patient's own blood serum used as tears. Reserved for severe/refractory DED.",
    weight: 0.85,
  },
  {
    term: "scleral contact lenses",
    synonyms: ["scleral lenses", "scleral contact lenses", "prosthetic replacement of the ocular surface ecosystem"],
    broaderTerms: ["dry eye treatment", "contact lens fitting"],
    narrowerTerms: [],
    note: "Large-diameter lenses that vault over cornea, maintaining a fluid reservoir.",
    weight: 0.8,
  },

  // --- Driving-Related ---
  {
    term: "night driving difficulty",
    synonyms: ["difficulty driving at night", "night driving problems", "impaired night driving"],
    broaderTerms: ["driving difficulty", "visual function impairment"],
    narrowerTerms: [],
    note: "Common complaint in DED patients. Related to glare, halos, and reduced contrast.",
    weight: 1.0,
  },
  {
    term: "driving performance",
    synonyms: ["driving ability", "driving safety", "road safety"],
    broaderTerms: ["driving difficulty"],
    narrowerTerms: ["simulated driving performance", "on-road driving assessment"],
    weight: 0.95,
  },
  {
    term: "glare sensitivity",
    synonyms: ["glare disability", "disability glare", "glare halos"],
    broaderTerms: ["visual symptoms", "dry eye symptoms"],
    narrowerTerms: [],
    note: "Exacerbated by dry eye. Particularly problematic for night driving.",
    weight: 0.9,
  },
  {
    term: "contrast sensitivity",
    synonyms: ["cs", "contrast visual acuity", "contrast vision"],
    broaderTerms: ["visual function"],
    narrowerTerms: [],
    note: "Reduced in DED. Affects ability to see objects against backgrounds.",
    weight: 0.85,
  },
  {
    term: "visual acuity",
    synonyms: ["va", "visual sharpness", " Snellen acuity"],
    broaderTerms: ["visual function"],
    narrowerTerms: ["best-corrected visual acuity", "uncorrected visual acuity", "functional visual acuity"],
    note: "May fluctuate in DED due to tear film instability.",
    weight: 0.85,
  },
  {
    term: "functional visual acuity",
    synonyms: ["fva", "sustained visual acuity", "visual endurance"],
    broaderTerms: ["visual function"],
    narrowerTerms: [],
    note: "Visual acuity maintained over time. More clinically relevant than single-measurement VA.",
    weight: 0.8,
  },

  // --- Psychosocial ---
  {
    term: "self-esteem",
    synonyms: ["self confidence", "self-worth", "self perception"],
    broaderTerms: ["psychological constructs"],
    narrowerTerms: ["state self-esteem", "trait self-esteem", "global self-esteem"],
    note: "Potential psychosocial mediator in DED-related quality of life impairment.",
    weight: 0.9,
  },
  {
    term: "quality of life",
    synonyms: ["qol", "quality-of-life", "health-related quality of life", "hrqol"],
    broaderTerms: ["patient-reported outcomes"],
    narrowerTerms: ["vision-related quality of life", "ocular surface disease-related quality of life"],
    weight: 1.0,
  },
  {
    term: "vision-related quality of life",
    synonyms: ["vrqol", "vr-qol", "visual quality of life"],
    broaderTerms: ["quality of life"],
    narrowerTerms: [],
    note: "QoL specifically impacted by visual function. Assessed by VFQ-25.",
    weight: 0.95,
  },
  {
    term: "depression",
    synonyms: ["depressive symptoms", "depressed mood", "major depression"],
    broaderTerms: ["mental health"],
    narrowerTerms: ["major depressive disorder", "persistent depressive disorder"],
    note: "Comorbid with DED. May mediate symptom burden.",
    weight: 0.85,
  },
  {
    term: "anxiety",
    synonyms: ["anxiety symptoms", "anxious mood", "generalized anxiety"],
    broaderTerms: ["mental health"],
    narrowerTerms: ["generalized anxiety disorder", "situational anxiety"],
    note: "Often comorbid with chronic conditions including DED.",
    weight: 0.85,
  },
  {
    term: "sleep quality",
    synonyms: ["sleep disturbance", "sleep problems", "insomnia"],
    broaderTerms: ["health outcomes"],
    narrowerTerms: ["sleep onset latency", "sleep efficiency", "sleep duration"],
    note: "DED symptoms can disrupt sleep; poor sleep can worsen DED.",
    weight: 0.8,
  },

  // --- Ocular Surface Inflammation ---
  {
    term: "ocular surface inflammation",
    synonyms: ["inflammation of ocular surface", "ocular surface inflammatory disease"],
    broaderTerms: ["dry eye disease"],
    narrowerTerms: ["conjunctival inflammation", "corneal inflammation"],
    weight: 0.9,
  },
  {
    term: "matrix metalloproteinases",
    synonyms: ["mmp", "mmps", "mmp-9"],
    broaderTerms: ["ocular surface inflammation", "biomarkers"],
    narrowerTerms: [],
    note: "MMP-9 elevated in DED tears. Potential biomarker for disease activity.",
    weight: 0.8,
  },
  {
    term: "inflammatory cytokines",
    synonyms: ["cytokines", "pro-inflammatory cytokines", "inflammatory mediators"],
    broaderTerms: ["ocular surface inflammation", "biomarkers"],
    narrowerTerms: ["il-1", "il-6", "tnf-alpha", "il-8"],
    weight: 0.8,
  },

  // --- Tear Film Components ---
  {
    term: "tear film",
    synonyms: ["tears", "tear fluid", "lacrimal film"],
    broaderTerms: ["ocular surface"],
    narrowerTerms: ["tear film lipid layer", "tear film aqueous layer", "tear film mucin layer"],
    weight: 1.0,
  },
  {
    term: "tear film lipid layer",
    synonyms: ["lipid layer", "meibum", "tear film oil layer"],
    broaderTerms: ["tear film"],
    narrowerTerms: [],
    note: "Outermost layer. Deficiency leads to evaporative dry eye.",
    weight: 0.85,
  },
  {
    term: "conjunctival goblet cells",
    synonyms: ["goblet cells", "mucin-secreting cells"],
    broaderTerms: ["ocular surface", "tear film mucin layer"],
    narrowerTerms: [],
    note: "Produce mucin essential for tear film stability.",
    weight: 0.8,
  },
];

// ============================================
// Regional Overlays
// ============================================

const DRY_EYE_REGIONAL_OVERLAYS: RegionalOverlay[] = [
  // MY (Malaysia) overlay
  {
    region: "MY",
    name: "Malaysian Dry Eye Vernacular",
    mappings: {
      "dry eye disease": ["mata kering", "sindrom mata kering"],
      "artificial tears": ["air mata buatan", "ubat mata kering"],
      "visual acuity": ["ketajaman penglihatan"],
      "night driving difficulty": ["kesukaran memandu malam"],
      "self-esteem": ["harga diri", "keyakinan diri"],
      "quality of life": ["kualiti hidup"],
      "depression": ["kemurungan"],
      "anxiety": ["kebimbangan"],
      "burning sensation": ["rasa terbakar pada mata"],
      "foreign body sensation": ["rasa ada benda asing dalam mata"],
      "photophobia": [" sensitiviti kepada cahaya"],
      "epiphora": ["air mata berlebihan", "mata berair"],
      "corneal staining": ["pewarnaan kornea"],
      "osmolarity": ["osmolariti air mata"],
    },
    additions: [
      {
        term: "mata kering",
        synonyms: ["dry eye", "dry eye disease", "keratoconjunctivitis sicca"],
        broaderTerms: ["ocular surface disease"],
        narrowerTerms: [],
        note: "Direct Malay translation used in Malaysian ophthalmology clinics.",
        weight: 1.0,
      },
    ],
    exclusions: new Set<string>(),
  },
  // SG (Singapore) overlay
  {
    region: "SG",
    name: "Singapore Dry Eye Vernacular",
    mappings: {
      "dry eye disease": ["dry eye", "mata kering"],
      "artificial tears": ["lubricant eye drops"],
      "self-esteem": ["self confidence", "self-worth"],
    },
    additions: [],
    exclusions: new Set<string>(),
  },
];

// ============================================
// Export
// ============================================

export const dryEyeVocabularyData = {
  source: "dry_eye",
  entries: DRY_EYE_DISEASE_TERMS,
  overlays: DRY_EYE_REGIONAL_OVERLAYS,
};

// ============================================
// Domain Detection Patterns
// ============================================

/**
 * Keywords that indicate a dry eye domain query.
 * Used by the search orchestrator to auto-activate the dry eye crosswalk.
 */
export const DRY_EYE_KEYWORDS = [
  "dry eye",
  "dry eye disease",
  "dry eye syndrome",
  "keratoconjunctivitis sicca",
  "meibomian gland",
  "mgd",
  "tear film",
  "nIBUT",
  "tbut",
  "osmolarity",
  "artificial tears",
  "cyclosporine ophthalmic",
  "lifitegrast",
  "punctal plug",
  "ocular surface",
  "osdi",
  "ded",
  "des",
  "sicca",
  "sjogren",
  "night driving",
  "visual performance",
  "tear break-up",
  "corneal staining",
];

/**
 * Check if a query is in the dry eye domain.
 */
export function isDryEyeQuery(query: string): boolean {
  const lower = query.toLowerCase();
  return DRY_EYE_KEYWORDS.some(kw => lower.includes(kw));
}
