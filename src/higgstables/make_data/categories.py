# Don't use the n_jets_bdt.
no_iso = "(n_iso_leptons == 0) & (n_iso_photons == 0) & "
categories = dict(
    cc=no_iso
    + "(n_pfos > 20) & (b_tag2 < 0.7) & (m_h > 100) & (c_tag1 > 0.5) & (c_tag2 > 0.5)",
    bb_tight=no_iso + "(b_tag1 > .8) & (b_tag2 > .8)",
    bb=no_iso + "(b_tag1 > .8)",
    e2e2="(e2e2_mass > 100) & (e2e2_mass < 130)",
    aZ="(aZ_a_energy > 20) & (aZ_a_energy < 50) & (aZ_other_mass > 75) & (aZ_other_mass < 100) & (abs(aZ_a_cos_theta) < 0.9)",
    aa="(n_iso_photons > 0) & (e_h > 125) & (n_pfos < 15) & (n_iso_leptons == 0) & (abs(aZ_a_cos_theta) < 0.9) & (aZ_a_energy > 35)",
    tau="(n_pfos < 15) & (n_iso_leptons == 0)",
    # tau='(y_45 < 1e-5) & (n_iso_leptons == 0)',
    light_quark=no_iso + "(b_tag1 + c_tag1 < .5)",
    light_quark2=no_iso + "(b_tag2 + c_tag2 < .5)",
    # Isolepton collector.
    isolep1="(n_iso_leptons == 1)",
    isolep2="(n_iso_leptons == 2)",
    isolep_many="(n_iso_leptons > 2)",
    isophoton1="(n_iso_photons == 1)",
    isophoton_many="(n_iso_photons > 1)",
    rest="(hDecay > 0)",  # Cannot have empty expression -> Always true.
)
