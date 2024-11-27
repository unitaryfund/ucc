API-doc
=======

This page details the publicly accessible functions available in ``ucc``.

.. automodule:: ucc
    :members: compile

.. autoclass:: ucc.transpilers.UCCTranspiler
    :members:

.. automodule:: ucc.transpiler_passes
    :members: BasisTranslator, 
              CommutativeCancellation, 
              Collect2qBlocks,
              CommutationAnalysis, 
              ConsolidateBlocks,
              UnitarySynthesis,
              Collect1qRuns,
              Optimize1qGatesDecomposition,
              SpectralMapping,
              SabreLayout