# Public paper snapshot structure

- src/diabetes_pipeline contains the original research implementation. Core numerical/model/inference modules are unchanged from the verified research baseline. Journal handoff curation has a filename/documentation adapter for the public metadata projection only.
- config contains dataset-native contracts, availability panels and the retained frozen/draft governance configurations. A frozen historical receipt is not authorization to rerun experiments.
- tests contains all 37 inherited test files byte-identically and three additional snapshot checks. Private-data tests retain their marker.
- scripts retains research entrypoints, including workflows that require unavailable private artifacts. Only REPRODUCIBILITY.md commands are advertised as public working paths.
- results/final_publication retains 85 unchanged aggregate/artwork/provenance files from the original 101-entry research export. Its scoped public checksum list is explicit; the original checksum index remains separately named.
- analysis/journal_revision contains aggregate comparison/routing/selective/repeat/cost sources and the 47-table handoff index. The separately named PUBLIC statistical-verification table omits private path metadata only.
- publication_release contains the paper source map, current plot inputs/artwork, verifiers, public manifest and scope/verification reports.
- evidence retains endpoint-separated study identity, clearly labelled development regression evidence and 14 safe correction-support files.

Raw datasets, individual outputs, fitted objects, private split/bootstrap/timing samples, preservation archives and original Git history are outside this snapshot. Start with the top-level README.md and REPRODUCIBILITY.md.
