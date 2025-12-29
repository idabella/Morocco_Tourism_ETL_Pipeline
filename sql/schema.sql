-- ============================================
-- Morocco Tourism Data Warehouse Schema
-- ============================================

-- Drop existing tables (in reverse order of dependencies)
DROP TABLE IF EXISTS fact_arrivees CASCADE ; 
DROP TABLE IF EXISTS fact_nuitees CASCADE;
DROP TABLE IF EXISTS fact_recettes CASCADE;
DROP TABLE IF EXISTS fact_capacite_hoteliere CASCADE;
DROP TABLE IF EXISTS fact_taux_occupation CASCADE;
DROP TABLE IF EXISTS fact_voies_acces CASCADE;
DROP TABLE IF EXISTS fact_indicateurs_globaux CASCADE;
DROP TABLE IF EXISTS fact_top_destinations CASCADE;
DROP TABLE IF EXISTS dim_destinations CASCADE;
DROP TABLE IF EXISTS dim_nationalites CASCADE;
DROP TABLE IF EXISTS dim_temps CASCADE;
DROP TABLE IF EXISTS dim_categories_hotel CASCADE;
DROP TABLE IF EXISTS dim_voies_acces CASCADE;
DROP TABLE IF EXISTS ref_agences_voyage CASCADE;
DROP TABLE IF EXISTS ref_guides_touristiques CASCADE;

-- ============================================
-- DIMENSION TABLES
-- ============================================

-- Dimension: Time
CREATE TABLE dim_temps (
    temps_id SERIAL PRIMARY KEY,
    annee INTEGER NOT NULL,
    mois VARCHAR(20),
    mois_num INTEGER,
    trimestre INTEGER,
    semestre INTEGER,
    UNIQUE(annee, mois)
);

-- Dimension: Destinations
CREATE TABLE dim_destinations (
    destinations_id SERIAL PRIMARY KEY,
    nom_destination VARCHAR(100) NOT NULL UNIQUE,
    region VARCHAR(100),
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dimension: Nationalities/Countries
CREATE TABLE dim_nationalites (
    nationalites_id SERIAL PRIMARY KEY,
    nom_pays VARCHAR(100) NOT NULL UNIQUE,
    continent VARCHAR(50),
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dimension: Hotel Categories
CREATE TABLE dim_categories_hotel (
    categories_hotel_id SERIAL PRIMARY KEY,
    nom_categorie VARCHAR(50) NOT NULL UNIQUE,
    nombre_etoiles INTEGER,
    description TEXT
);

-- Dimension: Access Routes
CREATE TABLE dim_voies_acces (
    voie_id SERIAL PRIMARY KEY,
    type_voie VARCHAR(50) NOT NULL,
    point_entree VARCHAR(100) NOT NULL,
    UNIQUE(type_voie, point_entree)
);

-- ============================================
-- FACT TABLES
-- ============================================

-- Fact: Tourist Arrivals
CREATE TABLE fact_arrivees (
    arrivee_id SERIAL PRIMARY KEY,
    temps_id INTEGER REFERENCES dim_temps(temps_id),
    nationalites_id INTEGER REFERENCES dim_nationalites(nationalites_id),
    type_touriste VARCHAR(50),
    nombre_arrivees BIGINT NOT NULL,
    variation_annuelle_pct NUMERIC(10, 2),
    date_chargement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_arrivees_positive CHECK (nombre_arrivees >= 0)
);

-- Fact: Overnight Stays (Nuitées)
CREATE TABLE fact_nuitees (
    nuitee_id SERIAL PRIMARY KEY,
    temps_id INTEGER REFERENCES dim_temps(temps_id),
    destinations_id INTEGER REFERENCES dim_destinations(destinations_id),
    nationalites_id INTEGER REFERENCES dim_nationalites(nationalites_id),
    type_touriste VARCHAR(50),
    nombre_nuitees BIGINT NOT NULL,
    variation_annuelle_pct NUMERIC(10, 2),
    taux_recuperation_vs_2019_pct NUMERIC(10, 2),
    date_chargement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_nuitees_positive CHECK (nombre_nuitees >= 0)
);

-- Fact: Monthly Revenues
CREATE TABLE fact_recettes (
    recette_id SERIAL PRIMARY KEY,
    temps_id INTEGER REFERENCES dim_temps(temps_id),
    montant_recettes NUMERIC(15, 2) NOT NULL,
    variation_annuelle_pct NUMERIC(10, 2),
    devise VARCHAR(10) DEFAULT 'MAD',
    date_chargement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_recettes_positive CHECK (montant_recettes >= 0)
);

-- Fact: Hotel Capacity
CREATE TABLE fact_capacite_hoteliere (
    capacite_id SERIAL PRIMARY KEY,
    temps_id INTEGER REFERENCES dim_temps(temps_id),
    categories_hotel_id INTEGER REFERENCES dim_categories_hotel(categories_hotel_id),
    nombre_unites INTEGER NOT NULL,
    nombre_chambres INTEGER NOT NULL,
    nombre_lits INTEGER NOT NULL,
    date_chargement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_capacite_positive CHECK (
        nombre_unites >= 0 AND 
        nombre_chambres >= 0 AND 
        nombre_lits >= 0
    )
);

-- Fact: Occupancy Rates
CREATE TABLE fact_taux_occupation (
    occupation_id SERIAL PRIMARY KEY,
    temps_id INTEGER REFERENCES dim_temps(temps_id),
    destinations_id INTEGER REFERENCES dim_destinations(destinations_id),
    taux_occupation_pct NUMERIC(5, 2) NOT NULL,
    ecart_annuel_points NUMERIC(5, 2),
    date_chargement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_taux_range CHECK (
        taux_occupation_pct >= 0 AND 
        taux_occupation_pct <= 100
    )
);

-- Fact: Access Routes Statistics
CREATE TABLE fact_voies_acces (
    acces_id SERIAL PRIMARY KEY,
    voie_id INTEGER REFERENCES dim_voies_acces(voie_id),
    total_passages BIGINT NOT NULL,
    mre_passages BIGINT,
    touristes_etrangers BIGINT,
    annee INTEGER,
    date_chargement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_acces_positive CHECK (total_passages >= 0)
);

-- Fact: Global Indicators
CREATE TABLE fact_indicateurs_globaux (
    indicateur_id SERIAL PRIMARY KEY,
    temps_id INTEGER REFERENCES dim_temps(temps_id),
    nom_indicateur VARCHAR(200) NOT NULL,
    valeur NUMERIC(20, 2) NOT NULL,
    unite_mesure VARCHAR(50),
    date_chargement TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fact: Top Destinations (Snapshot)
CREATE TABLE fact_top_destinations (
    top_dest_id SERIAL PRIMARY KEY,
    destinations_id INTEGER REFERENCES dim_destinations(destinations_id),
    non_residents BIGINT,
    residents BIGINT,
    total_visiteurs BIGINT NOT NULL,
    taux_occupation_pct NUMERIC(5, 2),
    annee INTEGER,
    rang INTEGER,
    date_chargement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_top_dest_positive CHECK (total_visiteurs >= 0)
);

-- ============================================
-- REFERENCE TABLES
-- ============================================

-- Reference: Travel Agencies
CREATE TABLE ref_agences_voyage (
    agence_id SERIAL PRIMARY KEY,
    raison_sociale VARCHAR(200) NOT NULL,
    adresse TEXT,
    ville VARCHAR(100),
    coordonnees VARCHAR(200),
    agrements TEXT,
    annee_agrement INTEGER,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Reference: Tourist Guides
CREATE TABLE ref_guides_touristiques (
    guide_id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    ville VARCHAR(100),
    categorie VARCHAR(50),
    langue_travail VARCHAR(100),
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Indexes on fact tables
CREATE INDEX idx_arrivees_temps ON fact_arrivees(temps_id);
CREATE INDEX idx_arrivees_nationalite ON fact_arrivees(nationalites_id);
CREATE INDEX idx_arrivees_type ON fact_arrivees(type_touriste);

CREATE INDEX idx_nuitees_temps ON fact_nuitees(temps_id);
CREATE INDEX idx_nuitees_destination ON fact_nuitees(destinations_id);
CREATE INDEX idx_nuitees_nationalite ON fact_nuitees(nationalites_id);
CREATE INDEX idx_nuitees_type ON fact_nuitees(type_touriste);

CREATE INDEX idx_recettes_temps ON fact_recettes(temps_id);

CREATE INDEX idx_capacite_temps ON fact_capacite_hoteliere(temps_id);
CREATE INDEX idx_capacite_categorie ON fact_capacite_hoteliere(categories_hotel_id);

CREATE INDEX idx_occupation_temps ON fact_taux_occupation(temps_id);
CREATE INDEX idx_occupation_destination ON fact_taux_occupation(destinations_id);

CREATE INDEX idx_acces_voie ON fact_voies_acces(voie_id);
CREATE INDEX idx_acces_annee ON fact_voies_acces(annee);

CREATE INDEX idx_indicateurs_temps ON fact_indicateurs_globaux(temps_id);
CREATE INDEX idx_indicateurs_nom ON fact_indicateurs_globaux(nom_indicateur);

-- Indexes on dimension tables
CREATE INDEX idx_temps_annee ON dim_temps(annee);
CREATE INDEX idx_temps_mois ON dim_temps(mois_num);

CREATE INDEX idx_destinations_nom ON dim_destinations(nom_destination);
CREATE INDEX idx_nationalites_nom ON dim_nationalites(nom_pays);

-- Indexes on reference tables
CREATE INDEX idx_agences_ville ON ref_agences_voyage(ville);
CREATE INDEX idx_guides_ville ON ref_guides_touristiques(ville);
CREATE INDEX idx_guides_categorie ON ref_guides_touristiques(categorie);

-- ============================================
-- VIEWS FOR COMMON QUERIES
-- ============================================

-- View: Annual Tourism Summary
CREATE OR REPLACE VIEW v_resume_annuel AS
SELECT 
    t.annee,
    SUM(a.nombre_arrivees) as total_arrivees,
    SUM(n.nombre_nuitees) as total_nuitees,
    SUM(r.montant_recettes) as total_recettes,
    AVG(o.taux_occupation_pct) as taux_occupation_moyen
FROM dim_temps t
LEFT JOIN fact_arrivees a ON t.temps_id = a.temps_id
LEFT JOIN fact_nuitees n ON t.temps_id = n.temps_id
LEFT JOIN fact_recettes r ON t.temps_id = r.temps_id
LEFT JOIN fact_taux_occupation o ON t.temps_id = o.temps_id
GROUP BY t.annee
ORDER BY t.annee DESC;

-- View: Top Source Markets
CREATE OR REPLACE VIEW v_top_marches_emetteurs AS
SELECT 
    n.nom_pays,
    t.annee,
    SUM(a.nombre_arrivees) as total_arrivees,
    RANK() OVER (PARTITION BY t.annee ORDER BY SUM(a.nombre_arrivees) DESC) as rang
FROM fact_arrivees a
JOIN dim_nationalites n ON a.nationalites_id = n.nationalites_id
JOIN dim_temps t ON a.temps_id = t.temps_id
GROUP BY n.nom_pays, t.annee
ORDER BY t.annee DESC, total_arrivees DESC;

-- View: Destination Performance
CREATE OR REPLACE VIEW v_performance_destinations AS
SELECT 
    d.nom_destination,
    t.annee,
    SUM(n.nombre_nuitees) as total_nuitees,
    AVG(o.taux_occupation_pct) as taux_occupation_moyen
FROM fact_nuitees n
JOIN dim_destinations d ON n.destinations_id = d.destinations_id
JOIN dim_temps t ON n.temps_id = t.temps_id
LEFT JOIN fact_taux_occupation o ON n.destinations_id = o.destinations_id AND n.temps_id = o.temps_id
GROUP BY d.nom_destination, t.annee
ORDER BY t.annee DESC, total_nuitees DESC;

-- ============================================
-- AUDIT AND METADATA
-- ============================================

-- Table: ETL Execution Log
CREATE TABLE etl_execution_log (
    log_id SERIAL PRIMARY KEY,
    execution_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    phase VARCHAR(50) NOT NULL,  -- 'EXTRACT', 'TRANSFORM', 'LOAD'
    status VARCHAR(20) NOT NULL,  -- 'SUCCESS', 'FAILED', 'WARNING'
    table_name VARCHAR(100),
    rows_affected INTEGER,
    error_message TEXT,
    execution_time_seconds NUMERIC(10, 2)
);

-- ============================================
-- GRANTS (adjust based on your users)
-- ============================================

-- Example: Create a read-only user for analysts
-- CREATE USER tourism_analyst WITH PASSWORD 'your_password';
-- GRANT CONNECT ON DATABASE morocco_tourism TO tourism_analyst;
-- GRANT USAGE ON SCHEMA public TO tourism_analyst;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO tourism_analyst;
-- GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO tourism_analyst;

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON TABLE fact_arrivees IS 'Tourist arrivals by nationality and type';
COMMENT ON TABLE fact_nuitees IS 'Overnight stays by destination and nationality';
COMMENT ON TABLE fact_recettes IS 'Monthly tourism revenues';
COMMENT ON TABLE fact_capacite_hoteliere IS 'Hotel capacity by category';
COMMENT ON TABLE fact_taux_occupation IS 'Occupancy rates by destination';
COMMENT ON TABLE dim_temps IS 'Time dimension for date-based analysis';
COMMENT ON TABLE dim_destinations IS 'Tourist destinations in Morocco';
COMMENT ON TABLE dim_nationalites IS 'Source markets and nationalities';

-- ============================================
-- INITIALIZATION DATA
-- ============================================

-- Insert common time periods (example for 2019-2023)
INSERT INTO dim_temps (annee, mois, mois_num, trimestre, semestre) 
SELECT 
    year,
    month_name,
    month_num,
    CASE 
        WHEN month_num <= 3 THEN 1
        WHEN month_num <= 6 THEN 2
        WHEN month_num <= 9 THEN 3
        ELSE 4
    END as trimestre,
    CASE 
        WHEN month_num <= 6 THEN 1
        ELSE 2
    END as semestre
FROM (
    SELECT 
        generate_series AS year,
        unnest(ARRAY['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 
                     'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']) AS month_name,
        unnest(ARRAY[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]) AS month_num
    FROM generate_series(2012, 2025) AS generate_series
) sub
ON CONFLICT (annee, mois) DO NOTHING;

-- Insert annual records (no month)
INSERT INTO dim_temps (annee, mois, mois_num, trimestre, semestre)
SELECT 
    generate_series,
    NULL,
    NULL,
    NULL,
    NULL
FROM generate_series(2012, 2025)
ON CONFLICT (annee, mois) DO NOTHING;

-- Insert common hotel categories
INSERT INTO dim_categories_hotel (nom_categorie, nombre_etoiles, description) VALUES
('1 étoile', 1, 'Hôtel 1 étoile'),
('2 étoiles', 2, 'Hôtel 2 étoiles'),
('3 étoiles', 3, 'Hôtel 3 étoiles'),
('4 étoiles', 4, 'Hôtel 4 étoiles'),
('5 étoiles', 5, 'Hôtel 5 étoiles'),
('Hôtel 1*', 1, 'Hôtel 1 étoile'),
('Hôtel 2*', 2, 'Hôtel 2 étoiles'),
('Hôtel 3*', 3, 'Hôtel 3 étoiles'),
('Hôtel 4*', 4, 'Hôtel 4 étoiles'),
('Hôtel 5*', 5, 'Hôtel 5 étoiles')
ON CONFLICT (nom_categorie) DO NOTHING;