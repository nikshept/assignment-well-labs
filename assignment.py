# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

# Devanahalli town (Ahmad and Singhal 2024)
TOWN_POPULATION = 38_000
TOWN_TANKS = 9
TOWN_AGRI_SHARE = 0.21381087        # Census 2011, Bangalore Rural
TOWN_AGRI_WORKERS = TOWN_POPULATION * TOWN_AGRI_SHARE
WELL_WATER_PER_DAY = 159_000        # litres/day supplied to the town

# Wider region (Census 2011, Karnataka-wide)
REGION_AGRI_SHARE = 0.22481536

# Chance that a litre handled is ingested, per activity
IRRIGATION_INGESTION = 1e-5
DOMESTIC_INGESTION = 1e-4
DRINKING_INGESTION = 1.0

# Per pathogen (George et al. 2015): dose-response r, chance of illness once infected, DALY per case
PATHOGENS = {
    "E. coli":       {"r": 0.001, "p_ill": 0.25, "daly": 0.45},
    "Rotavirus":     {"r": 0.27,  "p_ill": 0.50, "daly": 0.44},
    "Campylobacter": {"r": 0.018, "p_ill": 0.30, "daly": 0.0652},
}

# Per scenario: share of the water used for each purpose, and pathogen concentration (organisms/litre)
SCENARIOS = {
    "BAU": {
        "irrigation": 0.84, "domestic": 0.08, "drinking": 0.08,
        "concentration": {"E. coli": 9.12e-05, "Rotavirus": 1.14e-08, "Campylobacter": 0.0007524},
    },
    "S2": {
        "irrigation": 1.0, "domestic": 0.0, "drinking": 0.0,
        "concentration": {"E. coli": 9.12, "Rotavirus": 0.00114, "Campylobacter": 75.24},
    },
}

GSDP_PER_CAPITA_RUPEES = 477_003    # Karnataka 2025-26, human capital approach


# ----------------------------------------------------------------------------
# Calculation steps
# ----------------------------------------------------------------------------

def ingestion_chance(default_chance, exposure_change):
    # Default chance of ingestion changed by exposure_change, kept between 0 and 1 (0% and 100%)
    return min(max(default_chance * (1 + exposure_change), 0), 1)


def ingested_litres(scenario, works_in_agriculture, exposure_change=0):
    # Litres of well water ingested per person per day (exposure_change of 0.1 = ingestion chances +10%)
    irrigation_water = WELL_WATER_PER_DAY * scenario["irrigation"]
    domestic_water = WELL_WATER_PER_DAY * scenario["domestic"]
    drinking_water = WELL_WATER_PER_DAY * scenario["drinking"]

    irrigation_ingestion = ingestion_chance(IRRIGATION_INGESTION, exposure_change)
    domestic_ingestion = ingestion_chance(DOMESTIC_INGESTION, exposure_change)
    drinking_ingestion = ingestion_chance(DRINKING_INGESTION, exposure_change)

    litres = domestic_ingestion * domestic_water / TOWN_POPULATION
    litres += drinking_ingestion * drinking_water / TOWN_POPULATION
    if works_in_agriculture:
        litres += irrigation_ingestion * irrigation_water / TOWN_AGRI_WORKERS
    return litres


def annual_disease_risk(litres, concentration, pathogen):
    # Yearly probability of diarrhoeal disease for one person and one pathogen
    daily_infection_risk = min(litres * concentration * pathogen["r"], 1)
    yearly_infection_risk = 1 - (1 - daily_infection_risk) ** 365
    return yearly_infection_risk * pathogen["p_ill"]


def run_scenario(scenario_name, tanks, quality_change=0, exposure_change=0, agri_share=REGION_AGRI_SHARE):
    # Print the disease risks for one scenario and return its DALY per year (quality_change of 0.1 = water 10% cleaner)
    scenario = SCENARIOS[scenario_name]

    people = round(TOWN_POPULATION / TOWN_TANKS * tanks)
    agri_people = people * agri_share
    other_people = people - agri_people

    agri_litres = ingested_litres(scenario, works_in_agriculture=True, exposure_change=exposure_change)
    other_litres = ingested_litres(scenario, works_in_agriculture=False, exposure_change=exposure_change)

    print(f"Scenario: {scenario_name} | Tanks supplied: {tanks:.0f} | People supplied to: {people:.0f}")
    print("Disease risk (per person per year)")
    daly = 0
    for pathogen_name, pathogen in PATHOGENS.items():
        concentration = scenario["concentration"][pathogen_name] * max(1 - quality_change, 0)
        agri_risk = annual_disease_risk(agri_litres, concentration, pathogen)
        other_risk = annual_disease_risk(other_litres, concentration, pathogen)
        daly += (agri_risk * agri_people + other_risk * other_people) * pathogen["daly"]
        print(f"  {pathogen_name:<14} agricultural workers {agri_risk:.4e} | non-agricultural {other_risk:.4e}")

    print(f"Disease burden: {daly:.2f} DALY/year\n")
    return daly


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main(total_tanks, share_by_scenario):
    # Split the tanks between scenarios by share, run each, then sum the burden and value
    assert abs(sum(share_by_scenario.values()) - 1) < 1e-9, "scenario shares must add up to 1"

    BAU_daly = run_scenario("BAU", total_tanks * share_by_scenario["BAU"])
    S2_daly = run_scenario("S2", total_tanks * share_by_scenario["S2"])
    total_daly = BAU_daly + S2_daly

    BAU_value = BAU_daly * GSDP_PER_CAPITA_RUPEES / 100_000   # lakh rupees
    S2_value = S2_daly * GSDP_PER_CAPITA_RUPEES / 100_000   # lakh rupees
    total_value = total_daly * GSDP_PER_CAPITA_RUPEES / 100_000   # lakh rupees

    print(f"Total disease burden from lake recharge: {BAU_daly:.2f} DALY/year worth {BAU_value:.0f} lakh rupees")
    print(f"Total disease burden from irrigation: {S2_daly:.2f} DALY/year worth {S2_value:.0f} lakh rupees")
    print(f"Total disease burden: {total_daly:.2f} DALY/year worth {total_value:.0f} lakh rupees")


if __name__ == "__main__":
    main(total_tanks=242, share_by_scenario={"BAU": 0.77, "S2": 0.23})   # edit total tanks and shares