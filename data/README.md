# Data Notes

`dataset_locomo.json` is available and should be used for the first reproduction pass.

`dataset_LM.json` is intentionally not tracked in this private reproduction repository.
The upstream file is a Git LFS object, but the real object was not available during
repository setup. Keeping the unresolved LFS pointer breaks fresh clones because
Git LFS tries to download an object that is not present in this private repository.

Before running LongMemEval, obtain the real `dataset_LM.json` from a legitimate
source, place it under this directory, and record the file size, checksum, and
source in the experiment report. Do not commit the large dataset file.
