---
name: New transpiler pass
about: If you want to propose a new transpilation routine to go in UCC
title: "[NEW PASS]"
labels: feature
assignees: ''

---

Hooray, glad you're interested in proposing a new technique to add to [UCC's transpiler](https://github.com/unitaryfund/ucc/blob/main/ucc/transpilers/ucc_defaults.py)!
Please fill out the following template and we will triage and get back to you with next steps. 

1. How the technique works:
    a. In a written abstract without too much jargon, citing the source of the technique
    b. (Optional, recommended): In a diagram showing an example circuit and how it would be affected by this pass

2. Performance expectations:
    a. How much is the technique expected to reduce gate counts/compile time?
        (A rough estimate is okay, but this is how we prioritize which techniques to pursue)
    b. Which types of circuits do we expect this technique to improve/not improve?
