
### _What's a compiler pass?_
In UCC (Unitary Compiler Collection), we consider any technique which takes a "raw" uncompiled quantum circuit and returns a circuit which performs better on our [benchmarks](https://github.com/unitaryfoundation/ucc-bench?tab=readme-ov-file#latest-results) (see below) to be a good compiler pass. You can work at any layer of the quantum computing stack, from low-level hardware control to high-level algorithmic optimization.

## Steps to add a new compiler pass to UCC
#### <------Starting filling in the template here------>

### Propose your compiler pass
We're very excited you want to implement a new compilation technique in UCC! To get started, please provide us the following:  
1. How the technique works:  
    a. In a written abstract without too much jargon, citing the source of the technique (e.g. arXiv paper or Github repo)  
    b. (Optional, recommended): In a diagram showing an example circuit and how it would be affected by this pass 

2. Performance expectations:  
    a. Which types of circuits do we expect this technique to improve/not improve? (e.g. dynamic circuits, quantum error correction, etc.)  
    b. Which [UCC benchmark](https://ucc.readthedocs.io/en/latest/benchmarking.html) will it improve? (e.g. gate counts, relative errors, etc.)

> **Important:**  
> Once you've filled out your answers to 1-2, click the green Start Discussion button. **Leave the rest of this template intact!**  
One of the UCC maintainers will respond promptly with either a "go ahead" if your proposed pass looks good, or we may provide feedback/suggestions if the technique isn't quite aligned with our development roadmap.

#### <------Stop here and wait for us to approve your proposal------>

We recommend coming back to this discussion and editing as you move along through the development process. 
### Develop your compiler pass
Once the maintainers have given you the go-ahead...

3. Create a [fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo) of UCC to develop in: [link your fork here]  
    **Hint:** We recommending [syncing your fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/syncing-a-fork) with the main branch of UCC to stay up to date with changes. 
5. Implement and Validate a Prototype of the Pass:  
    A Jupyter notebook or a small script is sufficient for the prototype: [link prototype script/notebook here].  
    **Important:** Make sure your compiler pass works as you expect on the circuits you defined in step 2a.

6. Implement the New Pass in the UCC Codebase:  
Documentation to guide you through this process is available in the [user guide](https://ucc.readthedocs.io/en/latest/user_guide.html). For more detailed information and examples, refer to the [Qiskit documentation](https://docs.quantum.ibm.com/guides/custom-transpiler-pass).


### Benchmark performance
UCC benchmarks live in the separate repo called [ucc-bench](https://github.com/unitaryfoundation/ucc-bench). We have a [suite of quantum circuits](https://github.com/unitaryfoundation/ucc-bench/tree/main/benchmarks) that we regularly benchmark UCC and other popular quantum compilers on. Several of the key metrics we track are:

- Pure compilation:
    - 2-qubit gate count after circuit compilation (lower is better)
    - Total runtime of compilation (lower is better)
- Simulation
    - Relative errors in simulated expectation values for a defined set of observables (lower is better)

Your new pass should improve one or more of these metrics on our existing benchmark suite.  
**Note:** If you are introducing a technique whose effect on performance is not currently measurable by our [benchmark suite](https://github.com/unitaryfoundation/ucc-bench/tree/main/benchmarks) (e.g. a new qubit mapping pass that performs very well on sparsely connected qubit layouts), let us know and we can work with you to add the metric into [ucc-bench](github.com/unitaryfoundation/ucc-bench).

#### When you are ready to run benchmarks...  

6. Open a [pull request (PR) to merge your fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork) of UCC in main (mark it as a Draft unless you are ready for final review), ping a UCC maintainer, and we will trigger the benchmarking suite to run. Alternately, you can also run the benchmarks locally by comparing your UCC version to main, as explained in the [ucc-bench README](https://github.com/unitaryfoundation/ucc-bench#). 

---

### Useful documentation
[Contributing Guide](https://ucc.readthedocs.io/en/latest/contributing.html)  
[Setting up your Developer Environment](https://ucc.readthedocs.io/en/latest/contributing.html#setting-up-your-development-environment)  
[Writing a Custom Transpiler Pass](https://ucc.readthedocs.io/en/latest/user_guide.html#writing-a-custom-pass) 
-We use "transpiler pass" to refer to transformations that act only on the Directed Acyclic Graph (DAG) representation of the quantum circuit. Higher or lower-level optimizations (e.g. algorithm-level or pulse-level, respectively), we call "compiler passes." 

