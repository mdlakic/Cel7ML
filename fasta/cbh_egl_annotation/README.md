#### `cbh_egl_annotation/`: Contains sequences retrieved from the databases that have been annotated as CBH or EG

`cbh_ncbi.fasta`: Full-length sequences from NCBI non-redundant database clearly annotated as CBH (291 sequences).

`egl_ncbi.fasta`: Full-length sequences from NCBI non-redundant database clearly annotated as EG (136 sequences).

`cbh_swiss.fasta`: Full-length sequences from UniProtKB/SwissProt database clearly annotated as CBH (30 sequences).

`egl_swiss.fasta`: Full-length sequences from UniProtKB/SwissProt database clearly annotated as EG (14 sequences).

`alignments/`: Folder containing MSA of the above sequences. All sequences in cbh_ncbi.fasta and egl_ncbi.fasta were combined in a single file (cbhegl_msa_ncbi.fasta) and aligned with MAFFT. Then, the alignment was split into CBH and EG subalignments (i.e alignments/cbh_ncbi_msa.fasta and alignments/egl_ncbi_msa.fasta). Similarly the alignment of a combination of cbh_swiss.fasta and egl_swiss.fasta (alignments/tre_blast_swiss_msa.fasta) was split to subalignments (alignments/cbh_swiss_msa.fasta and alignments/egl_swiss_msa.fasta).

