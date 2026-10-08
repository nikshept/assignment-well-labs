import contextlib
import io

import matplotlib.pyplot as plt
import streamlit as st

import assignment


# ----------------------------------------------------------------------------
# Calculation helpers
# ----------------------------------------------------------------------------

def scenario_daly(scenario_name, tanks):
    # Run one scenario from assignment.py with the slider settings below, hiding its printed output
    with contextlib.redirect_stdout(io.StringIO()):
        return assignment.run_scenario(scenario_name, tanks, quality_change[scenario_name], exposure_change, agri_share)


def daly_to_value(daly):
    # Convert DALY to lakh rupees
    return daly * value_per_daly / 100_000


def value_to_daly(value):
    # Convert lakh rupees back to DALY (needed for the graph's second axis)
    return value * 100_000 / value_per_daly


# ----------------------------------------------------------------------------
# Page
# ----------------------------------------------------------------------------

st.set_page_config(layout="wide")
st.header("Optimizing wastewater allocation")

### Inputs
col1, col2 = st.columns(2)
col1.space("medium")

# Share between scenarios
bau_percent = col1.slider("Share of wastewater towards lake recharge (%) [rest goes to direct irrigation]", 0, 100, 78)
s2_percent = 100 - bau_percent
#col1.caption(f"Share towards direct irrigation: {s2_percent}%")

# Total tanks
with col1.expander("Change total population"):
    total_tanks = st.number_input("Total tanks supplied to", min_value=1, value=242, step=1)
    population = round(assignment.TOWN_POPULATION / assignment.TOWN_TANKS * total_tanks)
    st.caption(f"Equivalent population: {population:,} people")

# Water quality
with col1.expander("Change water quality"):
    bau_quality = st.number_input("Lake recharge (BAU) water quality change (%)", step=10)
    s2_quality = st.number_input("Direct irrigation (S2) water quality change (%)", step=10)
    st.caption("Positive = cleaner water (lower concentrations), negative = dirtier water. Concentrations cannot go below 0")
quality_change = {"BAU": bau_quality / 100, "S2": s2_quality / 100}

# Exposure
with col1.expander("Change exposure to water"):
    exposure_percent = st.number_input("Change in ingestion (%)", step=10)
    st.caption("Each ingestion chance stays between 0% and 100%, so drinking (already 100%) cannot increase")
exposure_change = exposure_percent / 100

# Value of a DALY
with col1.expander("Change value of a DALY"):
    value_per_daly = st.number_input("Value of one DALY (rupees)", min_value=1, value=assignment.GSDP_PER_CAPITA_RUPEES, step=10_000)

# Population in agriculture
with col1.expander("Change share of population in agriculture"):
    agri_percent = st.number_input("Population in agriculture (%)", 0.0, 100.0, assignment.REGION_AGRI_SHARE * 100, step=0.1)
agri_share = agri_percent / 100

# Disease burden for the chosen split
bau_daly = scenario_daly("BAU", total_tanks * bau_percent / 100)
s2_daly = scenario_daly("S2", total_tanks * s2_percent / 100)
total_daly = bau_daly + s2_daly

# Total DALY for every split from 0% to 100% lake recharge
percents = list(range(101))
dalys = [scenario_daly("BAU", total_tanks * p / 100) + scenario_daly("S2", total_tanks * (100 - p) / 100) for p in percents]
best_percent = percents[dalys.index(min(dalys))]

### Outputs

# Disease burden results
col2.metric("Total value of disease burden", f"Rs. {daly_to_value(total_daly)/100:.2f} crores")
with col2.expander("Detailed results"):
    st.write(f"Total disease burden: {total_daly:.1f} DALY/year")
    st.write(f"Lake recharge (BAU): {bau_daly:.1f} DALY/year, worth {daly_to_value(bau_daly)/100:.2f} crore rupees")
    st.write(f"Direct irrigation (S2): {s2_daly:.1f} DALY/year, worth {daly_to_value(s2_daly)/100:.2f} crore rupees")

# graph
fig, ax = plt.subplots(figsize=(6.4, 3.6))
ax.plot(percents, dalys)
ax.scatter([bau_percent], [total_daly], color="red", zorder=3, label="chosen split")
ax.scatter([best_percent], [min(dalys)], color="green", zorder=3, label="minimum")
ax.set_xlabel("Share of wastewater towards lake recharge (%)  [rest goes to direct irrigation]")
ax.set_ylabel("Total disease burden (DALY/year)")
ax.secondary_yaxis("right", functions=(daly_to_value, value_to_daly)).set_ylabel("Value (lakh rupees)")
ax.legend()
col2.pyplot(fig)
col2.caption(f"Lowest total disease burden: {min(dalys):.1f} DALY/year at {best_percent}% lake recharge and {100 - best_percent}% direct irrigation.")