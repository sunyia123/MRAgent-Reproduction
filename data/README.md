# Data Notes

`dataset_locomo.json` is available and should be used for the first reproduction pass.

`dataset_LM.json` is intentionally not tracked in this private reproduction repository.
The upstream file is a Git LFS object, but the real object was not available during
repository setup. Keeping the unresolved LFS pointer breaks fresh clones because
Git LFS tries to download an object that is not present in this private repository.

Before running LongMemEval, obtain the real data from a legitimate source, record
the file size, checksum, and source in the experiment report, then convert it to
MRAgent's expected `data/dataset_LM.json` schema if needed.

Recommended source:

- HuggingFace dataset: `xiaowu0162/longmemeval-cleaned`
- Candidate file: `longmemeval_s_cleaned.json`

Do not directly rename a downloaded LongMemEval file to `dataset_LM.json` until
its fields have been inspected and shown to match `data/get_data.py`.

Do not commit the large dataset file.
