"""Every number the case-auditor rules compare against, in one place.

A value is either sourced (its comment names the kit page) or a proposed default with no
source, marked "proposed default" with the reason. The rule pages list the proposed ones;
change a number here and nowhere else.
"""

# base.dc_skeleton  (concepts/case-impedance-completeness.md)
DC_SKELETON_MEDIAN_XR = 1000.0   # sourced: median X/R above 1000 means R is a placeholder
TINY_R = 1e-6                    # sourced: the page's "R <= 1e-6" placeholder signature
DC_SKELETON_SHARE = 0.9          # proposed default: the page measured 97-100 % of closed lines with
                                 # R <= 1e-6 and B = 0 on three skeleton lineages; 0.9 leaves margin.
                                 # LineLength is not used: it reads 0 on every branch of both public
                                 # cases probed 2026-09-30, so "zero-length" cannot be counted.
DC_SKELETON_PARTIAL_SHARE = 0.05 # proposed default: a partial skeleton (at least 1 in 20 closed lines
                                 # with no R and no B) is Worth a look; both public cases read 0.001 or less

# base.gen_over_nameplate  (spec section 4 and the case-auditor brief set these; neither is a source)
GEN_OVER_MIN_MW = 0.1            # proposed default: below this an overshoot is solver noise
GEN_OVER_STOP_MW = 5.0           # proposed default: not measured - neither public case has a unit
GEN_OVER_STOP_SHARE = 0.01       # over its max. Stops past max(1 % of GenMWMax, 5 MW)

# LTC rules  (methods/ltc-regulation-checks.md)
LTC_BAND_CAN_ACT_PU = 0.2        # proposed default: bands measured to act are 0.02-0.065 pu wide; a
                                 # band copied from the tap range (about 1 pu) never acts
KV_SAME_REL = 0.01               # proposed default: terminals within 1 % nominal kV have no LV side
BAND_TOL_PU = 1e-4               # proposed default: BusVoltLimLow/High read back single-precision
                                 # (0.89999998 for 0.9, probed 2026-09-30)
FALLBACK_BAND = (0.94, 1.05)     # the study criterion of the kit's measured runs, not a PowerWorld
                                 # default; used only where a bus's limits read 0 or blank

# base.floating_stub  (concepts/unloaded-ehv-stub-overvoltage.md)
EHV_KV = 300.0                   # proposed default: catches 345, 500 and 765 kV, excludes 230
STUB_MAX_BUSES = 50              # proposed default: stops a whole radial region reading as a stub
STUB_LIGHT_PERCENT = 10.0        # proposed default: "carries almost no MW", rated bridge
STUB_LIGHT_MW = 10.0             # proposed default: the same, for a bridge with LineAMVA = 0
STUB_RISE_PU = 0.005             # proposed default: the page's far end sat at 1.06-1.08 pu with the plant off

# timestep  (the case-auditor brief, demos/timestep-and-pfw.md)
RENEWABLE_CODES = ("WND", "SUN") # sourced: GenFuelType contains one of these
PFW_MIN_CHARS = 2                # sourced: a PFW model string longer than 2 characters
WIND_CLASSES = (1, 2, 3, 4)      # sourced: Auto_PFW reads CustomInteger:1 1-4 or GenUnitType W1-W4
PWW_MAX_STATION_MILES = 25.0     # proposed default: a 0.25-degree grid puts every point inside its
                                 # footprint within about 12 miles of a station
