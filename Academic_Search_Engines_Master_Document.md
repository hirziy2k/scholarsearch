# ACADEMIC SEARCH ENGINES, DATABASES & TOOLS — FINAL MASTER DOCUMENT
## Compiled August 2026 | All Data Current as of 2025–2026

---

## 1. SEARCH ENGINES & CITATION INDEXES

### 1.1 Google Scholar
- **URL:** https://scholar.google.com
- **Owner/Developer:** Google (Alphabet Inc.)
- **Launch Year:** 2004
- **Corpus Size:** ~400M+ scholarly documents
- **Content Types:** Journal articles, theses, books, conference papers, abstracts, technical reports, preprints, court opinions, patents
- **Key Features:** Cited-by tracking, author profiles, library integration, "Related articles," "Cited by" alerts, My Library, citation export in multiple formats
- **Strengths:** Broadest coverage across disciplines; free; integrates with university libraries; "Cite" button for instant citation export; alerts for new citations
- **Weaknesses:** No formal selection criteria; includes predatory journals; limited advanced search operators; citation counts inflated by self-citations; no API for bulk data; quality control absent
- **Access Model:** Free (no account needed); optional Google account for alerts/saved searches
- **API Availability:** No official public API; unofficial APIs exist (e.g., scholarly, SerpAPI)
- **AI Integration Status:** Google AI features integrated into search ranking; no dedicated AI research assistant; Gemini integration possible via Google ecosystem

### 1.2 Semantic Scholar
- **URL:** https://www.semanticscholar.org
- **Owner/Developer:** Allen Institute for AI (AI2)
- **Launch Year:** 2015
- **Corpus Size:** 237M+ papers (as of Aug 2026)
- **Content Types:** Journal articles, conference papers, preprints, theses, book chapters
- **Key Features:** AI-generated TLDR summaries, semantic search, citation graph analysis, Research Feeds (personalized), Influential Citations metric, author pages, Semantic Reader (augmented reading), paper recommendations
- **Strengths:** AI-powered relevance ranking; free API with generous limits; open data; excellent for discovering connections between papers; TLDR summaries save time; no paywall bias in ranking
- **Weaknesses:** Coverage biased toward CS/biomedical; fewer humanities/social science records; citation graph less complete than WoS/Scopus; younger corpus
- **Access Model:** Free, open access
- **API Availability:** Yes — robust public API with paper search, author search, citation data; free for research use
- **AI Integration Status:** Native AI — TLDRs, semantic search, Smart Citations, influence scoring; built by AI research institute

### 1.3 OpenAlex
- **URL:** https://openalex.org
- **Owner/Developer:** OurResearch (nonprofit); originally Microsoft Academic Graph
- **Launch Year:** 2022 (successor to Microsoft Academic, which ended 2021)
- **Corpus Size:** 250M+ works, 125M+ authors, 110K+ venues, 14K+ institutions
- **Content Types:** Journal articles, books, chapters, datasets, dissertations, conference proceedings, preprints, software
- **Key Features:** Completely free and open; concept tagging; institution/author/venue profiles; full-text search; recommended by library community; snapshot downloads; concept hierarchies; open API; locations (OA status detection)
- **Strengths:** Fully open (CC0 license); comprehensive; replaces Microsoft Academic; rich entity graph; snapshots for bulk analysis; no registration required; funded by community
- **Weaknesses:** Newer (less historical depth than WoS/Scopus before 1970s); occasional metadata duplication; less granular topic classification than Scopus; no direct PDF access
- **Access Model:** 100% free and open; no login required
- **API Availability:** Yes — RESTful API with full entity access, filters, sorting; bulk snapshots available
- **AI Integration Status:** No native AI features; used as data source for AI tools; open data enables custom AI pipelines

### 1.4 Scopus
- **URL:** https://www.scopus.com
- **Owner/Developer:** Elsevier
- **Launch Year:** 2004
- **Corpus Size:** 90M+ records; 1.8B+ citations; 27K+ active journal titles
- **Content Types:** Peer-reviewed journal articles, conference papers, book chapters, trade publications, patents (via Lens integration)
- **Key Features:** Citation analysis, h-index tracking, affiliation search, author profiling (Scopus Author ID), journal metrics (CiteScore, SJR, SNIP), PlumX metrics, export to reference managers, analytical dashboards, field-weighted citation impact
- **Strengths:** Largest curated citation database; comprehensive coverage of STEM; robust bibliometric tools; Scopus preview (limited free access); used for university rankings (THE, QS)
- **Weaknesses:** Subscription-based (expensive); limited humanities/arts coverage; selective journal inclusion; metadata quality varies; no full-text access without subscription
- **Access Model:** Institutional subscription (Scopus Free for preview with limited features); Scopus Complete for full access
- **API Availability:** Yes — Elsevier APIs (Scopus Search API, Citation API, Author Retrieval API); requires Elsevier developer key
- **AI Integration Status:** SciVal integration uses AI for benchmarking; PlumX for altmetrics; no standalone AI assistant

### 1.5 Web of Science (WoS)
- **URL:** https://www.webofscience.com
- **Owner/Developer:** Clarivate
- **Launch Year:** 1997 (successor to Science Citation Index, 1964)
- **Corpus Size:** 210M+ records; 171M+ cited references; ~95K journal titles indexed across Science, Social Sciences, Arts & Humanities
- **Content Types:** Journal articles, book chapters, conference proceedings, books, data sets (newer), retracted papers
- **Key Features:** Citation indexing, h-index, Journal Impact Factor (JIF), times cited, "Cited Reference Search," researcher profiles, ResearcherID/Publons, analytical tools, Master Journal List
- **Strengths:** Gold standard for citation analysis; Impact Factor is dominant metric; longest citation history (back to 1900 in some indexes); cross-disciplinary; peer review verification
- **Weaknesses:** Expensive subscription; limited to indexed journals only; humanities coverage weaker; no preprint coverage; interface can be slow; selective indexing
- **Access Model:** Institutional subscription; Web of Science Core Collection is primary product
- **API Availability:** Yes — Web of Science API (via Clarivate); requires developer agreement
- **AI Integration Status:** Clarivate's AI/ML for editorial and research intelligence; no public AI assistant

### 1.6 Dimensions
- **URL:** https://app.dimensions.ai
- **Owner/Developer:** Digital Science (part of Macmillan)
- **Launch Year:** 2018
- **Corpus Size:** 164M+ publications, 280M+ citations, 8.1M+ grants, 170M+ patents, 938K+ clinical trials, 42M+ datasets, 2.5M+ policy documents
- **Content Types:** Publications, grants, patents, clinical trials, datasets, policy documents, citations
- **Key Features:** Linked data across research lifecycle; grant-to-publication linking; clinical trial integration; patent connections; full-text indexing (70%+ of publications); AI tools; open access badge; reviewer finder; research security tool; landscape analysis dashboards
- **Strengths:** Broadest linked dataset (grants + publications + patents + clinical trials); free basic tier (Dimensions Basic); excellent for horizon scanning; open access detection
- **Weaknesses:** Advanced features require paid subscription; citation data not as deep as WoS/Scopus for older works; proprietary scoring; less transparent methodology
- **Access Model:** Free basic search (Dimensions Basic); subscription for Analytics, API, advanced tools
- **API Availability:** Yes — Dimensions API (free basic tier; premium for bulk access)
- **AI Integration Status:** AI-powered features for reviewer matching, research security, landscape analysis; proprietary ML models

### 1.7 Lens.org
- **URL:** https://www.lens.org
- **Owner/Developer:** Cambia (nonprofit)
- **Launch Year:** 2013
- **Corpus Size:** 200M+ scholarly records + 170M+ patent records (combined patent-scholarly dataset)
- **Content Types:** Scholarly works, patents, biological sequences (PatSeq), full-text citations
- **Key Features:** Patent-scholarly integration, PatSeq (biological sequence search in patents), PatCite (patent-scholarly linkage), Lens Profiles (ORCID-enhanced), Lens Reports, In4M (influence mapping), bulk data/API
- **Strengths:** Unique patent-scholarly bridge; free for non-commercial use; ORCID integration; open data initiative; global authority; no paywall for basic access
- **Weaknesses:** Interface less polished than competitors; learning curve for advanced features; patent data mainly from major offices; scholarly coverage gaps in humanities
- **Access Model:** Free for registered users (non-commercial); commercial/API licensing available
- **API Availability:** Yes — Scholarly API, Patent API, PatSeq API; bulk downloads available
- **AI Integration Status:** No native AI features; serves as data source for AI patent analysis tools

### 1.8 BASE (Bielefeld Academic Search Engine)
- **URL:** https://base-search.net
- **Owner/Developer:** Bielefeld University Library
- **Launch Year:** 2004
- **Corpus Size:** 400M+ documents from 11K+ content providers
- **Content Types:** Journal articles, e-books, theses, conference papers, museum objects, audio files, video, maps, government documents, archives
- **Key Features:** Deep web harvesting via OAI-PMH; quality filtering; content provider selection; advanced Boolean search; multilingual; OpenURL linking
- **Strengths:** Massive deep web index; harvests from institutional repositories; free; broad format coverage; multilingual; trustworthy (university-run)
- **Weaknesses:** No full-text search for all content; slower updates; limited citation analysis; no AI features; interface dated; no mobile app
- **Access Model:** Free, open access
- **API Availability:** Limited — OAI-PMH harvesting; no modern REST API for general use
- **AI Integration Status:** None

### 1.9 CORE
- **URL:** https://core.ac.uk
- **Owner/Developer:** CORE (COnnecting REpositories), hosted by The Open University (UK)
- **Launch Year:** 2008
- **Corpus Size:** 452M+ papers (as of Aug 2026); 12M+ full-text records
- **Content Types:** Journal articles, preprints, conference papers, theses, working papers, technical reports from 15K+ repositories
- **Key Features:** Full-text search of open access content; OAI identifier minting; CORE Discovery (browser extension); CORE Recommender; dataset access; FAIR certification; OAI Resolver
- **Strengths:** World's largest collection of open access research papers; free; full-text indexing; supports open science; strong repository network; datasets available
- **Weaknesses:** Only indexes open access content; coverage gaps for paywalled work; less known than Google Scholar; search relevance can be inconsistent
- **Access Model:** Free, open access
- **API Availability:** Yes — CORE API (metadata search, full-text access); datasets available for download
- **AI Integration Status:** CORE Discovery browser extension; no dedicated AI research assistant

### 1.10 Science.gov
- **URL:** https://science.gov
- **Owner/Developer:** U.S. Federal Government interagency initiative
- **Launch Year:** 2002
- **Corpus Size:** 200M+ pages of authoritative U.S. government science information
- **Content Types:** Government-funded research reports, journal articles, technical reports, fact sheets, websites, data sets
- **Key Features:** Federated search across 60+ government databases and 200M+ pages; science.gov Aggregator for web crawl; Science.gov Alliance
- **Strengths:** Free; authoritative U.S. government sources; no login required; aggregates across agencies (DOE, NASA, NSF, DOD, etc.)
- **Weaknesses:** U.S. government only; no international coverage; dated interface; no citation tracking; no AI; limited to government-produced content
- **Access Model:** Free, open access
- **API Availability:** No public API
- **AI Integration Status:** None

### 1.11 Baidu Scholar (Xueshu)
- **URL:** https://xueshu.baidu.com
- **Owner/Developer:** Baidu Inc. (China)
- **Launch Year:** 2014
- **Corpus Size:** 600M+ documents (including Chinese-language sources)
- **Content Types:** Journal articles (Chinese and international), theses, conference papers, patents, legal documents, books
- **Key Features:** Chinese-language coverage; citation tracking; English/Chinese search; library integration; citation export; plagiarism checking links
- **Strengths:** Best coverage of Chinese-language academic literature; free; includes legal and patent documents; useful for Sinology research
- **Weaknesses:** Primarily Chinese-language; limited English-language coverage compared to Google Scholar; privacy concerns; no API; censorship may affect results; interface primarily in Chinese
- **Access Model:** Free
- **API Availability:** No public API
- **AI Integration Status:** Baidu AI (Ernie) integration in broader ecosystem; no dedicated academic AI features

### 1.12 RefSeek
- **URL:** https://www.refseek.com
- **Owner/Developer:** RefSeek.com
- **Launch Year:** ~2009
- **Corpus Size:** 1B+ pages; indexes ~1B+ documents
- **Content Types:** Journal articles, books, web pages, newspaper articles, encyclopedias
- **Key Features:** Web and document search; academic focus; directory of reference sites; lightweight interface
- **Strengths:** Free; fast; simple interface; no ads; good for quick academic web searches
- **Weaknesses:** No citation tracking; no advanced features; limited corpus details; no API; small team; less comprehensive than Google Scholar; no AI
- **Access Model:** Free
- **API Availability:** No
- **AI Integration Status:** None

---

## 2. ARCHIVES & DIGITAL LIBRARIES

### 2.1 JSTOR
- **URL:** https://www.jstor.org
- **Owner/Developer:** ITHAKA (nonprofit)
- **Launch Year:** 1995
- **Corpus Size:** 12M+ journal articles; 200K+ books; 3M+ images (via Artstor); 2M+ primary sources
- **Content Types:** Journal articles (back issues), e-books, images, primary sources, maps, manuscripts, newspapers, videos
- **Key Features:** Text mining (for subscribers); workspace for note-taking; citation export; image search (Artstor integration); Open Content (300K+ CC items); Text Analyzer (AI-based recommendation)
- **Strengths:** High-quality scholarly content; excellent archival depth; Artstor visual library merged in; Open Content initiative; reliable long-term preservation
- **Weaknesses:** Heavy paywall (most content requires subscription/PPV); expensive institutional access; limited recent content (embargo periods); no preprint coverage
- **Access Model:** Institutional subscription; individual access (~$20/month); Pay Per Article; Open Access content available
- **API Availability:** Limited — no public search API; Text and Data Mining (TDM) program for subscribers
- **AI Integration Status:** JSTOR Text Analyzer (AI-based search/recommendation); limited AI integration

### 2.2 Library of Congress
- **URL:** https://www.loc.gov
- **Owner/Developer:** U.S. Federal Government (Library of Congress)
- **Launch Year:** 1800 (digital collections: 1990s)
- **Corpus Size:** 180M+ items (physical + digital); millions of digitized items
- **Content Types:** Books, newspapers, manuscripts, maps, photos, prints, drawings, films, music, web archives, legislation, patents, data
- **Key Features:** Congress.gov integration; digital collections; Chronicling America (historical newspapers); Print & Photographs; Ask a Librarian; legislative tracking
- **Strengths:** World's largest library; free access; primary sources; legislative documents; unmatched American history collections
- **Weaknesses:** Primarily American focus; digitization ongoing; interface can be overwhelming; not optimized for scholarly discovery; limited full-text search for all items
- **Access Model:** Free (digital collections); physical access by appointment
- **API Availability:** Limited — various APIs for specific collections; no unified scholarly search API
- **AI Integration Status:** None currently

### 2.3 Google Books
- **URL:** https://books.google.com
- **Owner/Developer:** Google
- **Launch Year:** 2004
- **Corpus Size:** 40M+ books scanned; partnerships with 100K+ publishers
- **Content Types:** Books (full-text searchable), magazines, limited preview, public domain full-text
- **Key Features:** Full-text search within books; "About this book" metadata; library links; citation export; public domain full view; partner preview
- **Strengths:** Massive scale; free full-text for public domain; useful for finding quoted passages; integrates with Google Scholar
- **Weaknesses:** Copyright restrictions limit preview; scanning errors; metadata quality varies; no API for scholarly use; ads; privacy concerns
- **Access Model:** Free (limited preview for most; full view for public domain)
- **API Availability:** Google Books API (limited; primarily for metadata/display)
- **AI Integration Status:** Gemini integration in Google ecosystem; no dedicated academic AI features

### 2.4 WorldCat
- **URL:** https://www.worldcat.org
- **Owner/Developer:** OCLC (Online Computer Library Center)
- **Launch Year:** 1971 (online); worldcat.org: 2006
- **Corpus Size:** 405M+ books, 440M+ articles, 25M+ sound recordings, 10M+ musical scores, 6M+ maps, 30M+ theses/dissertations
- **Content Types:** Books, articles, sound recordings, musical scores, maps, theses/dissertations, videos, web resources
- **Key Features:** World's largest library catalog; interlibrary loan; "Find in a Library"; citation export; library profiles; lists/bookshelves; trending ILL titles
- **Strengths:** Comprehensive library holdings worldwide; interlibrary loan; authoritative metadata; free search; library locator
- **Weaknesses:** Limited full-text access; metadata-centric; subscription features for libraries; no scholarly citation tracking; no API for researchers
- **Access Model:** Free to search; institutional subscription for advanced features (WorldShare, etc.)
- **API Availability:** Yes — WorldCat Search API (requires institutional access or developer key)
- **AI Integration Status:** None currently

### 2.5 Internet Archive / Wayback Machine
- **URL:** https://archive.org
- **Owner/Developer:** Internet Archive (nonprofit)
- **Launch Year:** 1996 (Wayback Machine: 2001)
- **Corpus Size:** 999B+ web pages archived; 40M+ texts; 16M+ audio; 12M+ videos; 5M+ images; 800K+ software
- **Content Types:** Web pages (Wayback Machine), books (Open Library), audio, video, images, software, data, presentations, podcasts
- **Key Features:** Wayback Machine (website snapshots); Open Library (digital lending); archive.today integration; book lending; search; collections; donations
- **Strengths:** Free; irreplaceable web history archive; digital lending library; massive diverse content; preservation mission
- **Weaknesses:** Not curated; copyright issues with some content; web scraping may be incomplete; no citation tracking; search can be slow; bandwidth concerns
- **Access Model:** Free; Open Library lending for controlled digital lending items
- **API Availability:** Yes — Archive.org API, Wayback Machine CDX API, Save Page Now API
- **AI Integration Status:** None native; data source for AI training

### 2.6 HathiTrust
- **URL:** https://www.hathitrust.org
- **Owner/Developer:** HathiTrust (consortium of research libraries)
- **Launch Year:** 2008
- **Corpus Size:** 18M+ digitized items (17M+ volumes)
- **Content Types:** Books, journals, newspapers, dissertations, maps, audio recordings
- **Key Features:** Full-text search; bibliographic search; "Find in a Library" (WorldCat); temporary display (limited); collection builder; partner dashboard; bibliographic API
- **Strengths:** Massive digitized collection; library consortium (700+ partners); robust preservation; trusted academic infrastructure; full-text search across millions of volumes
- **Weaknesses:** Most full text restricted to partner institutions; copyright limitations; no citation analysis; interface functional but basic; limited to digitized print materials
- **Access Model:** Free bibliographic search; full-text access via partner institutions (HathiTrust member libraries)
- **API Availability:** Yes — HathiTrust Bibliographic API; limited full-text API for member institutions
- **AI Integration Status:** HTRC (HathiTrust Research Center) provides computational access for researchers; no consumer AI features

### 2.7 Digital Commons Network
- **URL:** https://digitalcommons.bepress.com
- **Owner/Developer:** Elsevier (bepress)
- **Launch Year:** 2014
- **Corpus Size:** 4M+ works from 600+ institutions
- **Content Types:** Journal articles, theses, dissertations, working papers, conference proceedings, books, data sets
- **Key Features:** Disciplinary Commons (by subject); institutional repositories; full-text access; citation analytics; Usage metrics; browsable by discipline
- **Strengths:** Free full text; disciplinary organization; high-quality institutional content; discoverable across institutions
- **Weaknesses:** Not all institutions participate; coverage varies by discipline; limited search functionality; no API; no citation network
- **Access Model:** Free, open access
- **API Availability:** No public API
- **AI Integration Status:** None

---

## 3. GOVERNMENT & SPECIALIZED DATABASES

### 3.1 PubMed
- **URL:** https://pubmed.ncbi.nlm.nih.gov
- **Owner/Developer:** U.S. National Library of Medicine (NLM), National Institutes of Health (NIH)
- **Launch Year:** 1996
- **Corpus Size:** 40M+ citations (MEDLINE + life science journals + online books)
- **Content Types:** Biomedical journal articles, reviews, case reports, clinical trials, meta-analyses, practice guidelines, editorials
- **Key Features:** MeSH (Medical Subject Headings) indexing; clinical queries; advanced search; My NCBI alerts; citation manager; linked full text (PMC, publisher); single citation matcher; E-utilities API
- **Strengths:** Gold standard for biomedical literature; free; authoritative MeSH controlled vocabulary; excellent search precision; linked to PMC for free full text; widely cited
- **Weaknesses:** Biomedical only; citations not full articles (abstracts only unless linked to PMC); MeSH indexing delays; no preprint coverage by default
- **Access Model:** Free, open access
- **API Availability:** Yes — E-utilities API (ESearch, EFetch, ELink, etc.); NCBI Datasets
- **AI Integration Status:** PubMed Copilot (experimental AI search); MeSH vocabulary supports NLP/AI; no consumer AI assistant

### 3.2 PubMed Central (PMC)
- **URL:** https://www.ncbi.nlm.nih.gov/pmc/
- **Owner/Developer:** U.S. National Library of Medicine (NLM)
- **Launch Year:** 2000
- **Corpus Size:** 10M+ full-text articles
- **Content Types:** Full-text biomedical journal articles (open access archive)
- **Key Features:** Full-text search; figure/table search; supplementary material; article sequence (PMC submission IDs); XML/FTP access; OA compliance (NIH Public Access Policy)
- **Strengths:** Free full text for all articles; permanent archive; NIH compliance; full-text search; linked to PubMed citations
- **Weaknesses:** Biomedical only; not all PubMed articles have PMC full text; embargo periods; metadata quality varies; no citation tracking
- **Access Model:** Free, open access
- **API Availability:** Yes — E-utilities for PMC; FTP bulk access
- **AI Integration Status:** Part of NCBI's computational tools; no consumer AI features

### 3.3 ERIC
- **URL:** https://eric.ed.gov
- **Owner/Developer:** U.S. Department of Education, Institute of Education Sciences
- **Launch Year:** 1966
- **Corpus Size:** 1.9M+ records
- **Content Types:** Journal articles, reports, books, conference papers, policy documents, assessments, curricula (education-focused)
- **Key Features:** ERIC Thesaurus (controlled vocabulary); peer-review filter; full-text filter; advanced search; IES What Works Clearinghouse; citation export
- **Strengths:** Free; authoritative education research; controlled vocabulary; government-backed; high-quality indexing
- **Weaknesses:** Education only; some records lack full text; update delays; dated interface; limited international coverage
- **Access Model:** Free, open access
- **API Availability:** Yes — ERIC API (public, RESTful)
- **AI Integration Status:** None

### 3.4 NASA NTRS (Technical Reports Server)
- **URL:** https://ntrs.nasa.gov
- **Owner/Developer:** NASA (STI Program)
- **Launch Year:** 1990s (NTRS redesign: 2021)
- **Corpus Size:** 500K+ records (publicly available); additional registered content
- **Content Types:** Conference papers, journal articles, meeting papers, patents, research reports, images, movies, technical videos
- **Key Features:** Full-text search; NASA-specific metadata; registered content access (for NASA personnel); public vs. registered tiers; modern search interface
- **Strengths:** Free (public content); authoritative aerospace/STEM data; NASA mission-related documents; images and multimedia
- **Weaknesses:** Much content restricted to registered users (NASA contractors/grantees); non-NASA users limited to public subset; niche focus
- **Access Model:** Free for publicly available content; registered access for NASA-affiliated users
- **API Availability:** Limited — no public API; OAI-PMH for metadata
- **AI Integration Status:** None

### 3.5 National Archives (NARA)
- **URL:** https://www.archives.gov
- **Owner/Developer:** U.S. National Archives and Records Administration
- **Launch Year:** 1934 (NARA established); digitized collections since 2000s
- **Corpus Size:** Billions of pages of records (physical); millions digitized
- **Content Types:** Federal records, military records, presidential records, immigration records, census data, photographs, maps, audiovisual materials
- **Key Features:** Research our records; veterans' service records; America's Founding Documents; digitized records; microfilm catalogs; National Archives Catalog; Presidential Libraries
- **Strengths:** Free; authoritative U.S. government records; essential for genealogy, history, and legal research; digitization expanding
- **Weaknesses:** Physical materials require in-person access; digitization incomplete; search interface basic; no scholarly citation tools; non-researcher-oriented
- **Access Model:** Free (digital); in-person at facilities; some records require FOIA request
- **API Availability:** National Archives Catalog API (limited)
- **AI Integration Status:** None

### 3.6 ARTstor (now part of JSTOR)
- **URL:** https://www.jstor.org (ARTstor collections merged into JSTOR)
- **Owner/Developer:** ITHAKA (acquired ARTstor in 2016; merged into JSTOR by 2024)
- **Launch Year:** 2004 (as standalone); merged by 2024
- **Corpus Size:** 3M+ images from 300+ collections
- **Content Types:** Images (fine art, architecture, decorative arts, photographs, maps, textiles); museum collections
- **Key Features:** High-resolution images; classroom tools; JSTOR integration; OAI-PMH metadata export; shared shelf (institutional image management)
- **Strengths:** Highest-quality art/image database; museum partnerships; free for teaching (fair use); classroom-ready
- **Weaknesses:** Merged into JSTOR (less discoverable standalone); institutional subscription; primarily images (not text); limited to art/design focus
- **Access Model:** Institutional subscription (via JSTOR)
- **API Availability:** Limited — OAI-PMH metadata export
- **AI Integration Status:** None

---

## 4. OPEN ACCESS INFRASTRUCTURE

### 4.1 DOAJ (Directory of Open Access Journals)
- **URL:** https://doaj.org
- **Owner/Developer:** Infrastructure Services for Open Access (IS4OA), community-governed nonprofit
- **Launch Year:** 2003
- **Corpus Size:** 21,000+ journals; 9M+ articles (as of 2026)
- **Content Types:** Peer-reviewed open access journal articles across all disciplines
- **Key Features:** Quality seal; journal/article search; metadata export (CSV, JSON); ISSN lookup; DOAJ Seal; community-driven curation; Atom feed of new journals
- **Strengths:** Trusted quality filter; fully free; open data; global coverage; essential for OA compliance; prevents predatory journal indexing
- **Weaknesses:** Only OA journals (no paywalled content); application process for journals; some quality variation despite seal; no full-text search
- **Access Model:** Free, open access; DOAJ Seal for quality journals
- **API Availability:** Yes — DOAJ API (journal/article search, metadata)
- **AI Integration Status:** None

### 4.2 DOAB (Directory of Open Access Books)
- **URL:** https://doabooks.org
- **Owner/Developer:** OAPEN Foundation / DOAB Foundation (The Hague, Netherlands)
- **Launch Year:** 2012
- **Corpus Size:** 108,000+ peer-reviewed open access books
- **Content Types:** Peer-reviewed open access academic books/chapters
- **Key Features:** Book/chapter search; publisher directory; subject browsing; TRUSTED Platform Network; publisher metadata standards; OAI-PMH integration
- **Strengths:** Free; peer-reviewed books only; trusted publisher network; supports open access monographs; global coverage
- **Weaknesses:** Book-focused only; smaller corpus than journal indexes; coverage varies by publisher; no citation tracking
- **Access Model:** Free, open access
- **API Availability:** Yes — DOAB API (OAI-PMH; metadata harvestable)
- **AI Integration Status:** None

---

## 5. DATA REPOSITORIES

### 5.1 Zenodo
- **URL:** https://zenodo.org
- **Owner/Developer:** CERN (European Organization for Nuclear Research)
- **Launch Year:** 2013
- **Corpus Size:** 3M+ records (growing rapidly)
- **Content Types:** Research datasets, software, publications, posters, presentations, videos, images, file sets (any research output)
- **Key Features:** DOI minting (via DataCite); versioning; community curation; GitHub integration; unlimited storage; Zenodo communities; open access; long-term preservation
- **Strengths:** Free; backed by CERN; any file type; unlimited storage; DOI for citability; GitHub integration; institutional communities; EU Horizon compliance
- **Weaknesses:** No quality curation (community-managed); metadata quality varies; no data analysis tools; search can be slow
- **Access Model:** Free, open access
- **API Availability:** Yes — Zenodo API (records, files, communities, buckets)
- **AI Integration Status:** None

### 5.2 Figshare
- **URL:** https://figshare.com
- **Owner/Developer:** Digital Science (part of Macmillan)
- **Launch Year:** 2011
- **Corpus Size:** 10M+ uploads
- **Content Types:** Datasets, figures, tables, media, papers, posters, file sets (any research output)
- **Key Features:** DOI minting; versioning; Altmetrics integration; figshare+ (curated repository); institutional portals; private sharing; API; unlimited file size
- **Strengths:** Free basic storage; DOI minting; institutional partnerships; Altmetrics built-in; user-friendly; wide file support
- **Weaknesses:** Free tier limited to 20GB private / 1GB per file; premium for more storage; ownership concerns in ToS; less preservation focus than Zenodo
- **Access Model:** Free basic (20GB private storage); Figshare+ for curated, peer-reviewed datasets; institutional subscriptions
- **API Availability:** Yes — comprehensive REST API (search, create, update, delete records)
- **AI Integration Status:** Altmetrics and usage analytics; no consumer AI features

### 5.3 Dryad
- **URL:** https://datadryad.org
- **Owner/Developer:** Dryad (nonprofit, community-governed)
- **Launch Year:** 2003
- **Corpus Size:** 80K+ datasets
- **Content Types:** Research datasets (any format, any discipline)
- **Key Features:** Curated data review; DOI minting; integration with journals (Wiley, PLOS, Royal Society); data files + metadata; versioning; plain-language descriptions
- **Strengths:** Human curation (quality check); publisher integrations; any file format; community governance; funder compliance; free for qualifying datasets
- **Weaknesses:** Data publishing charges (~$150–$500); limited to research datasets; smaller corpus; no API for public search
- **Access Model:** Free for authors from partner institutions/publishers; data publishing charges otherwise ($150–$500)
- **API Availability:** Limited — private API for publisher integration; no general public search API
- **AI Integration Status:** None

---

## 6. SOCIAL / NETWORK PLATFORMS

### 6.1 ResearchGate
- **URL:** https://www.researchgate.net
- **Owner/Developer:** ResearchGate GmbH (Berlin, Germany)
- **Launch Year:** 2008
- **Corpus Size:** 25M+ researchers; 2B+ citation recommendations; 35M+ publications
- **Content Types:** Journal articles, preprints, conference papers, theses, chapters, datasets, patents, jobs, questions
- **Key Features:** Researcher profiles; publication uploads; "Ask a question" Q&A; RG Score; recommendation algorithm; full-text sharing; job board; collaboration matching; lab pages; analytics
- **Strengths:** Largest academic social network; free; excellent for networking; preprint hosting; full-text sharing; collaboration discovery; impact metrics (RG Score)
- **Weaknesses:** Copyright concerns with uploaded PDFs; commercial incentives (ads, premium); RG Score criticized as metric; no rigorous peer review; email spam; predatory publisher ads
- **Access Model:** Free (with ads); ResearchGate Premium (ad-free; additional analytics)
- **API Availability:** No public API (closed ecosystem)
- **AI Integration Status:** Recommendation algorithm; no dedicated AI research tools

### 6.2 Academia.edu
- **URL:** https://www.academia.edu
- **Owner/Developer:** Academia.edu (San Francisco, USA)
- **Launch Year:** 2008
- **Corpus Size:** 30M+ academics; 40M+ papers
- **Content Types:** Journal articles, preprints, conference papers, theses, book chapters, working papers
- **Key Features:** Researcher profiles; paper uploads; following/readership analytics; Academia Premium (full-text access); paper recommendations; sections (curated collections); ORCID integration
- **Strengths:** Large academic community; free profiles; good for discoverability; following system; readership metrics
- **Weaknesses:** Aggressive monetization (paywall for premium features); privacy concerns; paper recommendation algorithm prioritizes engagement; limited collaboration tools; copyright issues with uploads
- **Access Model:** Free basic; Academia Premium (~$99/year for full-text access and analytics)
- **API Availability:** No public API
- **AI Integration Status:** Recommendation algorithm; no dedicated AI tools

---

## 7. REFERENCE MANAGEMENT

### 7.1 Zotero
- **URL:** https://www.zotero.org
- **Owner/Developer:** Digital Scholar (nonprofit, George Mason University)
- **Launch Year:** 2006
- **Corpus Size:** N/A (reference manager; no corpus)
- **Content Types:** References for any scholarly resource (articles, books, websites, datasets, media, patents, etc.)
- **Key Features:** Browser connector (auto-detect references); 9,000+ citation styles; Word/LibreOffice/Google Docs integration; PDF annotation; Zotero Groups (collaboration); ZoteroBib; open source; plugins ecosystem; unlimited storage (local)
- **Strengths:** Free; open source; no vendor lock-in; powerful plugins (ZotFile, Better BibTeX); unlimited local storage; group libraries; active community; citation style editor; mobile apps
- **Weaknesses:** Cloud storage limited to 300MB free (paid for more); UI can feel dated; no AI features; steep learning curve for power features; no built-in PDF reader (uses external)
- **Access Model:** Free (open source); optional paid cloud storage (6GB = $20/year; unlimited = $60/year)
- **API Availability:** Yes — Zotero API (read/write libraries, items, tags); translators for web scraping
- **AI Integration Status:** None; relies on community plugins for any AI extensions

### 7.2 Mendeley
- **URL:** https://www.mendeley.com
- **Owner/Developer:** Elsevier
- **Launch Year:** 2008
- **Corpus Size:** N/A (reference manager)
- **Content Types:** References for scholarly resources (articles, books, websites, etc.)
- **Key Features:** PDF manager/annotator; citation generator; Word/LibreOffice plugin; Mendeley Web Importer; reference groups; 2GB free storage; Mendeley Data; AI-powered search; desktop + web versions
- **Strengths:** Free; 2GB free storage; PDF annotation; Elsevier integration; Mendeley Data for datasets; social networking features; AI search in library; widely used
- **Weaknesses:** Owned by Elsevier (vendor lock-in concerns); privacy controversies (2013); limited to Elsevier ecosystem; PDF limits; cloud-dependent; ads/promotions in free tier; no open source
- **Access Model:** Free (2GB storage); Mendeley Institutional Edition (for institutions)
- **API Availability:** Yes — Mendeley API (catalog search, library, user profiles)
- **AI Integration Status:** AI-powered library search; Semantic Reader-style features; context-aware document discovery; recently launched AI suite (2025–2026)

---

## 8. PREPRINT SERVERS

### 8.1 arXiv
- **URL:** https://arxiv.org
- **Owner/Developer:** Cornell University (Cornell Tech / Cornell University Library)
- **Launch Year:** 1991
- **Corpus Size:** 2.4M+ scholarly articles
- **Content Types:** Preprints (not peer-reviewed) in physics, math, computer science, quantitative biology, quantitative finance, statistics, electrical engineering, economics
- **Key Features:** Instant posting; permanent archive; DOI via arXiv; LaTeX source files; cross-listing between subjects; RSS; monthly archives; overlay journals integration
- **Strengths:** Pioneer of preprints; free; instantly available; massive CS/physics community; stable; respected; versioning; no embargo
- **Weaknesses:** No peer review; quality control relies on community moderation; rejection rate ~20% (moderation); primarily STEM (physics/math/CS); no biomedical
- **Access Model:** Free, open access
- **API Availability:** Yes — arXiv API (OAI-PMH; bulk access via Amazon S3; arXiv-sanity API by Karpathy)
- **AI Integration Status:** arXiv-sanity (AI-powered paper recommender by Andrej Karpathy, independent); no official AI tools

### 8.2 bioRxiv
- **URL:** https://www.biorxiv.org
- **Owner/Developer:** Cold Spring Harbor Laboratory (openRxiv consortium)
- **Launch Year:** 2013
- **Corpus Size:** 300K+ preprints
- **Content Types:** Preprints in all areas of biology
- **Key Features:** Subject-specific categories (30+ biology subfields); DOI via Crossref; preprint-server integration with journals (direct submission); SSRN integration; "Posting to bioRxiv" links from journals
- **Strengths:** Free; rapid dissemination; biology-focused community; journal partnerships (PLOS, eLife, etc.); versioning; no embargo
- **Weaknesses:** No peer review; variable quality; may confuse non-specialist readers; not all journals accept bioRxiv preprints
- **Access Model:** Free, open access
- **API Availability:** Yes — bioRxiv API (search, content); supported by Rxivist analytics
- **AI Integration Status:** None; Rxivist provides some altmetrics/analytics

### 8.3 medRxiv
- **URL:** https://www.medrxiv.org
- **Owner/Developer:** Cold Spring Harbor Laboratory, BMJ, NEJM (openRxiv)
- **Launch Year:** 2019
- **Corpus Size:** 30K+ preprints
- **Content Types:** Preprints in health sciences, medicine, epidemiology (50+ medical specialties)
- **Key Features:** Similar to bioRxiv; medical subject categories; DOI via Crossref; journal integration; rapid posting; versioning
- **Strengths:** Fills gap for medical preprints; free; rapid dissemination; backed by BMJ/NEJM; COVID-19 accelerated adoption
- **Weaknesses:** No peer review; controversial in medicine (risk of misinterpretation); clinical implications; variable quality; emerging platform
- **Access Model:** Free, open access
- **API Availability:** Yes — medRxiv API (same architecture as bioRxiv)
- **AI Integration Status:** None

### 8.4 SSRN (Social Science Research Network)
- **URL:** https://www.ssrn.com
- **Owner/Developer:** Elsevier
- **Launch Year:** 1994
- **Corpus Size:** 1M+ research papers
- **Content Types:** Working papers, preprints, conference papers, book chapters in social sciences, humanities, and more
- **Key Features:** Research paper networks; download rankings; author profiles; citations; SSRN Journal of Innovation; paper networks by topic; abstract page
- **Strengths:** Established platform; Elsevier backing; interdisciplinary; download counts as altmetric; working papers + preprints
- **Weaknesses:** Owned by Elsevier (concerns); less active than arXiv/bioRxiv; interface dated; quality varies; no peer review; declining usage in some fields
- **Access Model:** Free basic; SSRN Premium (ads-free; enhanced features)
- **API Availability:** Limited — SSRN has some programmatic access for institutional subscribers
- **AI Integration Status:** None

### 8.5 ChemRxiv
- **URL:** https://chemrxiv.org
- **Owner/Developer:** American Chemical Society (ACS), Royal Society of Chemistry (RSC), and others ( consortium)
- **Launch Year:** 2017
- **Corpus Size:** 50K+ preprints
- **Content Types:** Preprints in chemistry and related fields
- **Key Features:** DOI via Crossref; journal integration (ACS, RSC); subject categories; versioning; rapid posting
- **Strengths:** Free; chemistry-focused; backed by major chemistry societies; trustworthy; peer review alternative
- **Weaknesses:** Smaller community than arXiv; no peer review; chemistry traditionally slower to adopt preprints
- **Access Model:** Free, open access
- **API Availability:** Yes — API (same Zenodo/OSF infrastructure)
- **AI Integration Status:** None

### 8.6 EarthArXiv
- **URL:** https://www.eartharxiv.org
- **Owner/Developer:** California Digital Library (CDL) / Community
- **Launch Year:** 2017
- **Corpus Size:** 15K+ preprints
- **Content Types:** Preprints in Earth and planetary sciences (geology, geophysics, climate, oceanography, atmospheric science)
- **Key Features:** CDL infrastructure; Janeway platform; DOI minting; subject categories; versioning; community moderation
- **Strengths:** Free; community-governed; Earth sciences focus; backed by CDL
- **Weaknesses:** Small corpus; limited adoption; no peer review; community moderation variability
- **Access Model:** Free, open access
- **API Availability:** Limited — OAI-PMH
- **AI Integration Status:** None

### 8.7 PsyArXiv
- **URL:** https://psyarxiv.com
- **Owner/Developer:** Center for Open Science (COS) / Society for the Improvement of Psychological Science (SIPS)
- **Launch Year:** 2016
- **Corpus Size:** 15K+ preprints
- **Content Types:** Preprints in psychological science and cognitive science
- **Key Features:** OSF integration; DOI minting; versioning; rapid posting; psychology-focused categories
- **Strengths:** Free; community-driven; psychology research focus; OSF infrastructure (reliable)
- **Weaknesses:** Small community; limited adoption compared to arXiv; no peer review
- **Access Model:** Free, open access
- **API Availability:** Limited — via OSF API
- **AI Integration Status:** None

### 8.8 EdArXiv
- **URL:** https://edarxiv.org
- **Owner/Developer:** Center for Open Science (COS)
- **Launch Year:** 2017
- **Corpus Size:** 2K+ preprints
- **Content Types:** Preprints in education research
- **Key Features:** OSF infrastructure; education-focused; DOI minting; versioning
- **Strengths:** Free; fills gap for education research preprints
- **Weaknesses:** Very small corpus; low adoption; no peer review; limited community
- **Access Model:** Free, open access
- **API Availability:** Limited — via OSF API
- **AI Integration Status:** None

### 8.9 Preprints.org
- **URL:** https://www.preprints.org
- **Owner/Developer:** MDPI (Multidisciplinary Digital Publishing Institute)
- **Launch Year:** 2016
- **Corpus Size:** 136K+ preprints; 108M+ downloads; 26M+ views
- **Content Types:** Preprints across all disciplines (12 subject areas)
- **Key Features:** DOI minting; quality screening by editors; SciProfiles integration; Preprints Friendly Journals (transfer service); article-level metrics; ORCID linking
- **Strengths:** Free; multidisciplinary; quality screening (editorial check); MDPI journal integration; wide subject coverage; good metrics
- **Weaknesses:** MDPI connection (MDPI has mixed reputation); screening is light; commercial platform; not community-governed
- **Access Model:** Free, open access
- **API Availability:** Limited — no public API
- **AI Integration Status:** None

### 8.10 ScienceOpen
- **URL:** https://www.scienceopen.com
- **Owner/Developer:** ScienceOpen (Berlin, Germany)
- **Launch Year:** 2013
- **Corpus Size:** 90M+ records
- **Content Types:** Journal articles, preprints, books, datasets, posters
- **Key Features:** Contextual search; post-publication peer review; collection curation; ORCID integration; journal hosting; researcher profiles; open peer review
- **Strengths:** Free; post-publication peer review; collection curation; interdisciplinary; journal hosting platform
- **Weaknesses:** Less known; interface complexity; limited API; declining growth; small team
- **Access Model:** Free basic; premium journal hosting
- **API Availability:** Limited — ScienceOpen API (search)
- **AI Integration Status:** None

---

## 9. OPEN ACCESS TOOLS

### 9.1 Unpaywall
- **URL:** https://unpaywall.org
- **Owner/Developer:** OurResearch (nonprofit)
- **Launch Year:** 2011 (Unpaywall API: 2015)
- **Corpus Size:** 100M+ works with OA status
- **Content Types:** Journal articles (OA status detection)
- **Key Features:** Browser extension (finds free legal copy); Unpaywall API (OA status); Unpaywall Map (institutional OA subscriptions); integrates with 25K+ libraries
- **Strengths:** Free; finds legal free versions automatically; integrates with library systems; trusted; API widely used; green/gold OA classification
- **Weaknesses:** Only works with DOI/ISSN; no full text; relies on repository indexing; browser extension sometimes slow; may miss some OA copies
- **Access Model:** Free
- **API Availability:** Yes — Unpaywall API (URL-based; free for non-commercial)
- **AI Integration Status:** None

### 9.2 CORE Discovery
- **URL:** https://core.ac.uk/discovery
- **Owner/Developer:** CORE (Open University)
- **Launch Year:** ~2018
- **Corpus Size:** Same as CORE (452M+ papers)
- **Content Types:** Open access papers (full text)
- **Key Features:** Browser extension; finds OA versions while browsing publisher sites; integrates with CORE database; shows OA copies on demand
- **Strengths:** Free; automatic OA detection; full-text focus; integrates with CORE's massive OA database
- **Weaknesses:** Requires browser extension; less widely known than Unpaywall; limited adoption; no API for external use
- **Access Model:** Free
- **API Availability:** No (browser extension only)
- **AI Integration Status:** None

### 9.3 Sherpa/Romeo
- **URL:** https://sherpa.ac.uk/romeo/
- **Owner/Developer:** University of Nottingham / Jisc (UK)
- **Launch Year:** 2002
- **Corpus Size:** 11,000+ publisher policies; 1,000+ funder policies (Sherpa/Funder)
- **Content Types:** Publisher open access policies; embargo periods; permitted archiving locations; funder mandates
- **Key Features:** Publisher policy lookup; embargo information; journal search by ISSN; funder policy aggregation (Sherpa/Funder); Sherpa/Dolfin (deposit mandates)
- **Strengths:** Essential for OA compliance; trusted; free; comprehensive publisher policies; used by librarians worldwide; policy comparison
- **Weaknesses:** Manual data entry (policies change); interface dated; limited API; publisher self-reporting may lag behind changes
- **Access Model:** Free, open access
- **API Availability:** Yes — Romeo API (public, XML/JSON output)
- **AI Integration Status:** None

---

## 10. JOURNAL METRICS

### 10.1 Journal Impact Factor (JIF)
- **Owner/Developer:** Clarivate (Journal Citation Reports)
- **Definition:** Ratio of citations in year X to articles published in years X-1 and X-2, divided by number of citable items in those two years
- **Strengths:** Most widely recognized metric; used for university rankings, tenure decisions; 50+ years of history
- **Weaknesses:** Easily manipulated; self-citation gaming; varies by discipline; 2-year window penalizes slow-citing fields; not available for new journals
- **Access:** Journal Citation Reports (Clarivate subscription)

### 10.2 CiteScore
- **Owner/Developer:** Elsevier (Scopus)
- **Definition:** Citations in year X to documents published in years X-1 through X-4, divided by documents published in years X-1 through X-4
- **Strengths:** 4-year window (fairer to slower-citing fields); free to check via Scopus; covers 27K+ journals; transparent calculation
- **Weaknesses:** Elsevier-owned (Scopus bias); still susceptible to gaming; newer than JIF; 4-year window less precise for fast-moving fields
- **Access:** Free lookup via Scopus/CiteScore Tracker

### 10.3 SJR (SCImago Journal Rank)
- **Owner/Developer:** SCImago (based on Scopus data)
- **Definition:** Weighted citation ranking; prestige-weighted (citations from high-prestige journals weighted more)
- **Strengths:** Free; prestige-weighted (quality over quantity); available for all Scopus journals; visual rankings; good for cross-discipline comparison
- **Weaknesses:** Complex calculation; less recognized than JIF; Scopus-dependent; can be gamed; SJR2 vs SJR3 methodology changes
- **Access:** Free via scimagojr.com

### 10.4 SNIP (Source Normalized Impact per Paper)
- **Owner/Developer:** CWTS (Leiden University), based on Scopus data
- **Definition:** Contextualized citation impact; normalizes for field citation potential (how likely citations are in that field)
- **Strengths:** Field-normalized (fair cross-field comparison); free; accounts for citation culture differences; good for interdisciplinary journals
- **Weaknesses:** Complex; less intuitive; not widely used outside bibliometrics; Scopus-dependent
- **Access:** Free via Scopus/SNIP tracker

### 10.5 h-index
- **Owner/Developer:** Jorge E. Hirsch (2005)
- **Definition:** A researcher/journal has h-index of *h* if *h* papers have each been cited at least *h* times
- **Strengths:** Simple; intuitive; measures both productivity and impact; used for researcher evaluation
- **Weaknesses:** Can't be easily compared across fields; favors long-career researchers; ignores highly-cited outliers; manipulated by self-citation; varies by source
- **Access:** Calculated from Scopus/WoS/Google Scholar/Dimensions

### 10.6 h5-index
- **Owner/Developer:** Google Scholar (2009)
- **Definition:** h-index calculated over the last 5 years only
- **Strengths:** Fresh measurement; Google Scholar-based (broad coverage); good for journal comparison
- **Weaknesses:** Google Scholar data quality issues; shorter window; not widely adopted by institutions
- **Access:** Free via Google Scholar Metrics

### 10.7 i10-index
- **Owner/Developer:** Google Scholar
- **Definition:** Number of a researcher's publications with at least 10 citations
- **Strengths:** Simple; useful for identifying consistently cited work
- **Weaknesses:** Very crude metric; threshold is arbitrary; not widely used outside Google Scholar; easily gamed
- **Access:** Free via Google Scholar

### 10.8 Journal Citation Indicator (JCI)
- **Owner/Developer:** Clarivate (2021)
- **Definition:** Field-weighted citation impact for a journal; normalized to 1.0 (1.0 = world average)
- **Strengths:** Field-normalized; intuitive (above 1.0 = above average); available for all JCR journals; cross-discipline comparison
- **Weaknesses:** New metric (limited track record); Clarivate-dependent; part of JCR paywall; less familiar to researchers
- **Access:** Journal Citation Reports (Clarivate subscription)

### 10.9 Field-Weighted Citation Impact (FWCI)
- **Owner/Developer:** Elsevier (SciVal/Dimensions)
- **Definition:** Citations received normalized by expected citations for the same document type, publication year, and subject area
- **Strengths:** Field-normalized; available for researchers/institutions/countries; intuitive (1.0 = average); widely used in benchmarking
- **Weaknesses:** Scopus/Dimensions-dependent; Elsevier-owned; used in commercial benchmarking tools
- **Access:** Via SciVal (Elsevier) or Dimensions (subscription)

---

## 11. MASTER COVERAGE COMPARISON TABLE

| Tool | Peer-Reviewed Articles | Books/Chapters | Preprints | Theses | Datasets | Patents | Clinical Trials | Conference Papers | Images/Media | Government Docs |
|------|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|
| Google Scholar | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ✅ |
| Semantic Scholar | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| OpenAlex | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Scopus | ✅ | ✅ | ❌ | ⚠️ | ⚠️ | ⚠️ | ❌ | ✅ | ❌ | ❌ |
| Web of Science | ✅ | ✅ | ❌ | ⚠️ | ⚠️ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Dimensions | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Lens.org | ✅ | ⚠️ | ❌ | ⚠️ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ |
| BASE | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ❌ | ❌ | ✅ | ✅ | ✅ |
| CORE | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ⚠️ |
| Science.gov | ⚠️ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ⚠️ | ⚠️ | ✅ |
| Baidu Scholar | ✅ | ✅ | ⚠️ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ |
| JSTOR | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ✅ | ❌ |
| PubMed | ✅ | ❌ | ⚠️ | ❌ | ⚠️ | ❌ | ✅ | ✅ | ❌ | ❌ |
| PMC | ✅ (OA) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ⚠️ | ❌ | ❌ |
| DOAJ | ✅ (OA) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

*Legend: ✅ = Included; ⚠️ = Partial/Limited; ❌ = Not included*

---

## 12. MASTER ACCESS / API / AI COMPARISON TABLE

| Tool | Free Access | Institutional Required | Public API | AI Features | Open Data |
|------|:-----:|:-----:|:-----:|:-----:|:-----:|
| Google Scholar | ✅ | ❌ | ❌ (unofficial) | ⚠️ (Gemini ecosystem) | ❌ |
| Semantic Scholar | ✅ | ❌ | ✅ (free) | ✅ (native AI) | ✅ |
| OpenAlex | ✅ | ❌ | ✅ (free) | ❌ | ✅ (CC0) |
| Scopus | ❌ | ✅ | ✅ (Elsevier) | ⚠️ (SciVal) | ❌ |
| Web of Science | ❌ | ✅ | ✅ (Clarivate) | ⚠️ (Clarivate AI) | ❌ |
| Dimensions | ⚠️ (basic free) | ✅ (premium) | ✅ (free tier) | ✅ (ML features) | ❌ |
| Lens.org | ✅ | ❌ | ✅ (free) | ❌ | ⚠️ (partial) |
| BASE | ✅ | ❌ | ❌ | ❌ | ❌ |
| CORE | ✅ | ❌ | ✅ (free) | ❌ | ✅ |
| Science.gov | ✅ | ❌ | ❌ | ❌ | ❌ |
| Baidu Scholar | ✅ | ❌ | ❌ | ❌ | ❌ |
| JSTOR | ⚠️ (limited free) | ✅ | ❌ | ⚠️ (Text Analyzer) | ❌ |
| ARTstor (JSTOR) | ❌ | ✅ | ❌ | ❌ | ❌ |
| PubMed | ✅ | ❌ | ✅ (E-utilities) | ⚠️ (Copilot) | ✅ |
| PMC | ✅ | ❌ | ✅ | ❌ | ✅ |
| ERIC | ✅ | ❌ | ✅ | ❌ | ✅ |
| NASA NTRS | ✅ (public) | ✅ (registered) | ❌ | ❌ | ❌ |
| NARA | ✅ | ❌ | ⚠️ (limited) | ❌ | ✅ (public domain) |
| DOAJ | ✅ | ❌ | ✅ | ❌ | ✅ |
| DOAB | ✅ | ❌ | ✅ (OAI-PMH) | ❌ | ✅ |
| Zenodo | ✅ | ❌ | ✅ (free) | ❌ | ✅ |
| Figshare | ✅ | ❌ | ✅ (free) | ❌ | ⚠️ (premium) |
| Dryad | ⚠️ (partner free) | ❌ | ⚠️ (limited) | ❌ | ✅ |
| ResearchGate | ✅ | ❌ | ❌ | ⚠️ (rec engine) | ❌ |
| Academia.edu | ⚠️ (limited) | ❌ | ❌ | ❌ | ❌ |
| Zotero | ✅ | ❌ | ✅ (free) | ❌ | ✅ (open source) |
| Mendeley | ✅ | ❌ | ✅ | ✅ (AI search) | ❌ |
| arXiv | ✅ | ❌ | ✅ | ⚠️ (arXiv-sanity) | ✅ |
| bioRxiv | ✅ | ❌ | ✅ | ❌ | ✅ |
| medRxiv | ✅ | ❌ | ✅ | ❌ | ✅ |
| SSRN | ⚠️ (limited free) | ❌ | ❌ | ❌ | ❌ |
| ChemRxiv | ✅ | ❌ | ⚠️ (limited) | ❌ | ✅ |
| EarthArXiv | ✅ | ❌ | ❌ | ❌ | ✅ |
| PsyArXiv | ✅ | ❌ | ⚠️ (OSF) | ❌ | ✅ |
| EdArXiv | ✅ | ❌ | ⚠️ (OSF) | ❌ | ✅ |
| Preprints.org | ✅ | ❌ | ❌ | ❌ | ✅ |
| ScienceOpen | ✅ | ❌ | ⚠️ (limited) | ❌ | ⚠️ |
| Unpaywall | ✅ | ❌ | ✅ (free) | ❌ | ✅ |
| CORE Discovery | ✅ | ❌ | ❌ | ❌ | ❌ |
| Sherpa/Romeo | ✅ | ❌ | ✅ (free) | ❌ | ✅ |

---

## 13. DECISION FLOWCHART BY TASK

### Finding a Specific Paper (By Title/Author/DOI)
- **Known DOI →** Use https://doi.org or https://unpaywall.org
- **Know citation →** Google Scholar → Semantic Scholar → OpenAlex
- **Biomedical →** PubMed → PMC
- **Education →** ERIC
- **Government →** Science.gov → NASA NTRS (aerospace)

### Broad Literature Search (New Topic)
- **Start →** Google Scholar (broadest) → Semantic Scholar (AI-powered ranking) → Scopus/WoS (if institutional)
- **Humanities →** JSTOR → Google Scholar → JSTOR
- **Chinese sources →** Baidu Scholar
- **Multidisciplinary + open data →** OpenAlex + Dimensions

### Finding Open Access Copies
- **Quick check →** Unpaywall (browser extension) or CORE Discovery
- **Paywalled paper →** Check author's ResearchGate/Academia.edu → check institutional repository via CORE/BASE → check preprint server (arXiv/bioRxiv/medRxiv) → use Sherpa/Romeo to check publisher OA policy → Interlibrary Loan → email author directly

### Citing a Journal (Metrics)
- **Impact Factor →** Journal Citation Reports (Clarivate)
- **CiteScore →** Scopus
- **Free metrics →** SJR (scimagojr.com) / SNIP (via Scopus)
- **Researcher h-index →** Scopus Author ID / Google Scholar / OpenAlex

### Storing & Organizing References
- **Open source + control →** Zotero
- **Elsevier ecosystem →** Mendeley
- **Quick bibliography only →** ZoteroBib

### Sharing Preprints
- **Physics/Math/CS →** arXiv
- **Biology →** bioRxiv
- **Medicine →** medRxiv
- **Social sciences →** SSRN
- **Chemistry →** ChemRxiv
- **Earth sciences →** EarthArXiv
- **Psychology →** PsyArXiv
- **Education →** EdArXiv
- **Multidisciplinary →** Preprints.org

### Archiving Research Data
- **Free + CERN-backed →** Zenodo
- **Institutional + Altmetrics →** Figshare
- **Curated + publisher-integrated →** Dryad

### Measuring Journal Quality
- **Gold standard →** JIF (Web of Science/JCR)
- **Free SJR ranking →** scimagojr.com
- **Field-normalized →** SNIP / JCI / FWCI

---

## 14. HOW TO ACCESS PAYWALLED PAPERS (ALL LEGAL METHODS)

### Method 1: Open Access Detection
- Install **Unpaywall** browser extension (free) — automatically finds legal free versions
- Install **CORE Discovery** browser extension — finds OA copies via CORE database
- Check **DOAJ** for journal OA status

### Method 2: Author's Versions
- Search **ResearchGate** — authors often upload accepted manuscripts
- Search **Academia.edu** — authors share preprints/accepted versions
- Check author's **institutional repository** via CORE or BASE
- Check author's **personal website** or lab page
- Email the author directly — most will share a PDF on request (legal in most jurisdictions)

### Method 3: Preprint Servers
- **arXiv** (physics/math/CS), **bioRxiv** (biology), **medRxiv** (medicine), **SSRN** (social science), **ChemRxiv** (chemistry), **EarthArXiv** (earth science), **PsyArXiv** (psychology), **EdArXiv** (education), **Preprints.org** (multidisciplinary)

### Method 4: Library Access
- University/institutional library subscription — check library website
- Interlibrary Loan (ILL) — request through your library
- **HathiTrust** full-text access (member institutions)
- **WorldCat** to find libraries holding the item

### Method 5: Publisher Policy Check
- Use **Sherpa/Romeo** to check if author deposited manuscript in repository
- Check publisher's OA policy — many allow "green OA" (accepted manuscript) after embargo
- Check **PubMed Central** — some articles become free after embargo

### Method 6: Legal Free Access
- **OpenAlex** — links to OA locations
- **Dimensions** — shows OA badge and links
- **Semantic Scholar** — links to free versions
- **Google Scholar** — often shows [PDF] links to free copies

### Method 7: Controlled Digital Lending
- **Internet Archive / Open Library** — borrow digitized books legally
- **HathiTrust Emergency Temporary Access** — access during emergencies for member institutions

### Method 8: Paid Options (When All Else Fails)
- **Pay-Per-Article** via publisher website
- **PaperFull** or **DeepDyve** — article rental services
- **RACER** (Canadian Interlibrary Loan)
- **Copyright Clearance Center** — legal document delivery

### Method 9: Institutional/Community Resources
- **Ask-A-Librarian** — many university libraries offer remote assistance
- **#ICanHazPDF** on Twitter/X — community sharing (legal gray area; check copyright)
- **Academic Twitter** — authors often share their work

---

## 15. ALL VALID URLs — FINAL CONSOLIDATED LIST

### Search Engines & Citation Indexes
- https://scholar.google.com
- https://www.semanticscholar.org
- https://openalex.org
- https://www.scopus.com
- https://www.webofscience.com
- https://app.dimensions.ai
- https://www.lens.org
- https://base-search.net
- https://core.ac.uk
- https://science.gov
- https://xueshu.baidu.com
- https://www.refseek.com

### Archives & Digital Libraries
- https://www.jstor.org
- https://www.loc.gov
- https://books.google.com
- https://www.worldcat.org
- https://archive.org
- https://www.hathitrust.org
- https://digitalcommons.bepress.com

### Government & Specialized Databases
- https://pubmed.ncbi.nlm.nih.gov
- https://www.ncbi.nlm.nih.gov/pmc/
- https://eric.ed.gov
- https://ntrs.nasa.gov
- https://www.archives.gov

### Open Access Infrastructure
- https://doaj.org
- https://doabooks.org

### Data Repositories
- https://zenodo.org
- https://figshare.com
- https://datadryad.org

### Social / Network Platforms
- https://www.researchgate.net
- https://www.academia.edu

### Reference Management
- https://www.zotero.org
- https://www.mendeley.com

### Preprint Servers
- https://arxiv.org
- https://www.biorxiv.org
- https://www.medrxiv.org
- https://www.ssrn.com
- https://chemrxiv.org
- https://www.eartharxiv.org
- https://psyarxiv.com
- https://edarxiv.org
- https://www.preprints.org
- https://www.scienceopen.com

### Open Access Tools
- https://unpaywall.org
- https://core.ac.uk/discovery
- https://sherpa.ac.uk/romeo/

### Supplementary Tools (Not in main list but highly useful)
- https://orcid.org (ORCID — researcher ID)
- https://www.crossref.org (DOI registration)
- https://scimagojr.com (SJR rankings)
- https://www.journalmetrics.com (Clarivate metrics)
- https://citation-needed.springer.com (Springer Nature citation data)
- https://www.dimensions.ai (AI-powered research analytics)

---

*Document compiled August 2026. Data current as of 2025–2026. Corpus sizes are approximate and subject to rapid change. Always verify current statistics on official websites.*
