"""
Prediction of GH7 subtypes (CBH/EG) with hidden Markov models (HMM)
"""




# Imports
#=============#

import pandas as pd
import numpy as np
import subprocess

from sklearn.model_selection import KFold

import warnings
warnings.filterwarnings("ignore")

import bioinformatics as bioinf






# Split sequences into 5 folds for training/testing HMM
#============================================================#

def kfold_split(fasta, k, path, root='kfold'):
    '''Spilt sequences in fasta file into k-folds and save them as k-separate fasta files
    for k-fold training and testing (saved as ${root}_train1.fasta, ${root}_test1.fasta, 
    etc.)'''
    
    [h,s] = bioinf.split_fasta(fasta)
    kf = KFold(n_splits=5, random_state=0, shuffle=True)
    dummy=0
    for train_index, test_index in kf.split(range(len(s))):
        dummy += 1
        bioinf.combine_fasta([h[x] for x in train_index], [s[x] for x in train_index], 
                             f'{path}/{root}_train{dummy}.fasta')
        bioinf.combine_fasta([h[x] for x in test_index], [s[x] for x in test_index], 
                             f'{path}/{root}_test{dummy}.fasta')

# UniProtKB/Swiss-Prot sequences (44 total, 30 CBH, 14 EGL)
cbh_file = 'fasta/cbh_egl_annotation/alignments/cbh_swiss_msa.fasta'
egl_file = 'fasta/cbh_egl_annotation/alignments/egl_swiss_msa.fasta'
kfold_split(cbh_file, k=5, path='hmm_train_test/swiss_kfold', root='cbh')
kfold_split(egl_file, k=5, path='hmm_train_test/swiss_kfold', root='egl')
    
# NCBI sequences (427 total, 291 CBH, 136 EGL)
cbh_file = 'fasta/cbh_egl_annotation/alignments/cbh_ncbi_msa.fasta'
egl_file = 'fasta/cbh_egl_annotation/alignments/egl_ncbi_msa.fasta'
kfold_split(cbh_file, k=5, path='hmm_train_test/ncbi_kfold', root='cbh')
kfold_split(egl_file, k=5, path='hmm_train_test/ncbi_kfold', root='egl')






# Train and test HMM on 5 folds of sequences
#=================================================#t

def implement_hmm_bash(path, k=5):
    '''Implement HMM with Python's subprocess function. HMMMER should be installed on your
    machine and the commands, hmmbuild and hmmsearch, should be callable from the command
    line.  Train/test fasta sequences should be present in $path (as cbh_train1.fasta, 
    cbh_test1.fasta, egl_train1.fasta, egl_test1.fasta, etc.) HMMs are tested on a 
    left-out fold, and trained on all other folds.'''
    
    # Loop through all k folds, train HMMs on train fold sequences
    # and test on test fold sequences
    for i in range(1, k+1):
        # Build/train HMM
        cbh_train_hmm = f'{path}/cbh{i}.hmm'
        cbh_train_fasta = f'{path}/cbh_train{i}.fasta'
        egl_train_hmm = f'{path}/egl{i}.hmm'
        egl_train_fasta = f'{path}/egl_train{i}.fasta'
        cbh_command = f'hmmbuild {cbh_train_hmm} {cbh_train_fasta}'
        egl_command = f'hmmbuild {egl_train_hmm} {egl_train_fasta}'
        
        subprocess.call(cbh_command, shell=True)
        subprocess.call(egl_command, shell=True)

        # Test HMM on cbh and egl test fold
        cbh_test_fasta = f'{path}/cbh_test{i}.fasta'
        egl_test_fasta = f'{path}/egl_test{i}.fasta'
        cbh_to_cbh_out = f'{path}/cbhhmm_cbh{i}.out'
        cbh_to_egl_out = f'{path}/cbhhmm_egl{i}.out'
        egl_to_cbh_out = f'{path}/eglhmm_cbh{i}.out'
        egl_to_egl_out = f'{path}/eglhmm_egl{i}.out'
        cbh_to_cbh_command = f'hmmsearch -T 0 --incT 0 --nobias {cbh_train_hmm} ' \
                             f'{cbh_test_fasta} > {cbh_to_cbh_out}'
        cbh_to_egl_command = f'hmmsearch -T 0 --incT 0 --nobias {cbh_train_hmm} ' \
                             f'{egl_test_fasta} > {cbh_to_egl_out}'
        egl_to_cbh_command = f'hmmsearch -T 0 --incT 0 --nobias {egl_train_hmm} ' \
                             f'{cbh_test_fasta} > {egl_to_cbh_out}'
        egl_to_egl_command = f'hmmsearch -T 0 --incT 0 --nobias {egl_train_hmm} ' \
                             f'{egl_test_fasta} > {egl_to_egl_out}'
        
        subprocess.call(cbh_to_cbh_command, shell=True)
        subprocess.call(cbh_to_egl_command, shell=True)
        subprocess.call(egl_to_cbh_command, shell=True)
        subprocess.call(egl_to_egl_command, shell=True)



# UniProtKB/Swiss-Prot sequences (44 total, 30 CBH, 14 EGL)
implement_hmm_bash(path='hmm_train_test/swiss_kfold', k=5)
    
# NCBI sequences (427 total, 291 CBH, 136 EGL)
implement_hmm_bash(path='hmm_train_test/ncbi_kfold', k=5)






# Retrieve and compare HMM scores from HMM output files, store results
#=======================================================================#

def get_acc_and_scores(hmm_output):
    '''Read an HMMER align output file and retrieve
    the accession codes and HMM scores in the file.
    Return the list, [accessions, scores].'''
    
    with open(hmm_output,'r') as file:
        text = file.read()
    text = text[text.index('E-value'):text.index('Domain')]
    text_lines = text.split('\n')[2:-3]
    text_lines = [x for x in text_lines if '---' not in x]
    scores = [line.split()[1] for line in text_lines]
    scores = [float(x) for x in scores]
    accessions = [line.split()[8] for line in text_lines]
    return [accessions, scores]



def compare_hmmscores(fasta, hmm1, hmm2):
    '''Return a dataframe whose columns are the accession 
    numbers in fasta and the corresponding hmm scores from 
    the hmm output files, hmm1 and hmm2, respectively.'''
    
    acc_all = bioinf.get_accession(fasta)
    [acc1, score1] = get_acc_and_scores(hmm1)
    [acc2, score2] = get_acc_and_scores(hmm2)
    hmm1_scores,hmm2_scores = [],[]
    for i in range(len(acc_all)):
        try:
            hmm1_scores.append(score1[acc1.index(acc_all[i])])
        except:
            hmm1_scores.append(0)  # Assign a score of 0 if it's below the threshold
            
        try:
            hmm2_scores.append(score2[acc2.index(acc_all[i])])
        except:
            hmm2_scores.append(0)
    store = pd.DataFrame([acc_all, hmm1_scores, hmm2_scores]).transpose()
    store.columns = ['accession', 'hmm1_scores', 'hmm2_scores']
    return store

  

# UniProtKB/Swiss-Prot sequences (44 total, 30 CBH, 14 EGL)
cbh_store = pd.DataFrame()
egl_store = pd.DataFrame()
path = 'hmm_train_test/swiss_kfold/'
k = 5
for i in range(k):
    fasta_cbh = path + f'cbh_test{i+1}.fasta'
    hmm1_cbh = path + f'cbhhmm_cbh{i+1}.out'
    hmm2_cbh = path + f'eglhmm_cbh{i+1}.out'
    cbh_store = cbh_store.append(compare_hmmscores(fasta_cbh, hmm1_cbh, hmm2_cbh), 
                                 ignore_index=True)
    
    fasta_egl = path + f'egl_test{i+1}.fasta'
    hmm1_egl = path + f'cbhhmm_egl{i+1}.out'
    hmm2_egl = path + f'eglhmm_egl{i+1}.out'
    egl_store = egl_store.append(compare_hmmscores(fasta_egl, hmm1_egl, hmm2_egl), 
                                 ignore_index=True)

cbh_store['diff_score'] = pd.Series(np.array(cbh_store.iloc[:,1]) - 
                                     np.array(cbh_store.iloc[:,2]))
cbh_store['true_class'] = pd.Series([1]*len(cbh_store))
cbh_store['pred_class'] = pd.Series([1 if x > 0 else 0 for x in cbh_store.iloc[:,3]])
egl_store['diff_score'] = pd.Series(np.array(egl_store.iloc[:,1]) - 
                                     np.array(egl_store.iloc[:,2]))
egl_store['true_class'] = pd.Series([0]*len(egl_store))
egl_store['pred_class'] = pd.Series([1 if x > 0 else 0 for x in egl_store.iloc[:,3]])
store = cbh_store.append(egl_store, ignore_index=True)
store.to_csv('results_final/swiss_kfold.csv')



# NCBI sequences (427 total, 291 CBH, 136 EGL)
cbh_store = pd.DataFrame()
egl_store = pd.DataFrame()
path = 'hmm_train_test/ncbi_kfold/'
k = 5
for i in range(k):
    fasta_cbh = path + f'cbh_test{i+1}.fasta'
    hmm1_cbh = path + f'cbhhmm_cbh{i+1}.out'
    hmm2_cbh = path + f'eglhmm_cbh{i+1}.out'
    cbh_store = cbh_store.append(compare_hmmscores(fasta_cbh, hmm1_cbh, hmm2_cbh), 
                                 ignore_index=True)
    
    fasta_egl = path + f'egl_test{i+1}.fasta'
    hmm1_egl = path + f'cbhhmm_egl{i+1}.out'
    hmm2_egl = path + f'eglhmm_egl{0}.out'
    egl_store = egl_store.append(compare_hmmscores(fasta_egl, hmm1_egl, hmm2_egl), 
                                 ignore_index=True)

cbh_store['diff_score'] = pd.Series(np.array(cbh_store.iloc[:,1]) - 
                                     np.array(cbh_store.iloc[:,2]))
cbh_store['true_class'] = pd.Series([1]*len(cbh_store))
cbh_store['pred_class'] = pd.Series([1 if x > 0 else 0 for x in cbh_store.iloc[:,3]])
egl_store['diff_score'] = pd.Series(np.array(egl_store.iloc[:,1]) - 
                                     np.array(egl_store.iloc[:,2]))
egl_store['true_class'] = pd.Series([0]*len(egl_store))
egl_store['pred_class'] = pd.Series([1 if x > 0 else 0 for x in egl_store.iloc[:,3]])
store = cbh_store.append(egl_store, ignore_index=True)
store.to_csv('results_final/ncbi_kfold.csv')






# Train final HMMs on all data (all 5 folds), store for future use
#===================================================================#

# UniProtKB/Swiss-Prot HMMs
swiss_cbh_fasta = 'fasta/cbh_egl_annotation/alignments/cbh_swiss_msa_fasta'
swiss_egl_fasta = 'fasta/cbh_egl_annotation/alignments/egl_swiss_msa_fasta'
swiss_cbh_hmm = 'hmm_train_test/final_hmm/cbh_swiss.hmm'
swiss_egl_hmm = 'hmm_train_test/final_hmm/egl_swiss.hmm'
cbh_command = f'hmmbuild {swiss_cbh_hmm} {swiss_cbh_fasta}'
egl_command = f'hmmbuild {swiss_egl_hmm} {swiss_egl_fasta}'
subprocess.call(cbh_command, shell=True)
subprocess.call(egl_command, shell=True)

# NCBI HMMs
ncbi_cbh_fasta = 'fasta/cbh_egl_annotation/alignments/cbh_ncbi_msa_fasta'
ncbi_egl_fasta = 'fasta/cbh_egl_annotation/alignments/egl_ncbi_msa_fasta'
ncbi_cbh_hmm = 'hmm_train_test/final_hmm/cbh_ncbi.hmm'
ncbi_egl_hmm = 'hmm_train_test/final_hmm/egl_ncbi.hmm'
cbh_command = f'hmmbuild {ncbi_cbh_hmm} {ncbi_cbh_fasta}'
egl_command = f'hmmbuild {ncbi_egl_hmm} {1=ncbi_egl_fasta}'
subprocess.call(cbh_command, shell=True)
subprocess.call(egl_command, shell=True)
    





# Apply NCBI HMM and UniProtKB/Swiss-Prot HMM to 1,748 sequences
#================================================================#

# File paths
fastafile = 'fasta/initial_blast/cel7_nr99.fasta'
swiss_cbh_out = 'hmm_train_test/final_hmm/hmm_to_1748/cel7_nr_cbhswiss.out'
swiss_egl_out = 'hmm_train_test/final_hmm/hmm_to_1748/cel7_nr_eglswiss.out'
ncbi_cbh_out = 'hmm_train_test/final_hmm/hmm_to_1748/cel7_nr_cbhncbi.out'
ncbi_egl_out = 'hmm_train_test/final_hmm/hmm_to_1748/cel7_nr_eglncbi.out'

# Commands
swiss_cbh_command = f'hmmsearch -T 0 --incT 0 --nobias {swiss_cbh_hmm} {fastafile} > ' \
                    f'{swiss_cbh_out}'
swiss_egl_command = f'hmmsearch -T 0 --incT 0 --nobias {swiss_egl_hmm} {fastafile} > ' \
                    f'{swiss_egl_out}'
ncbi_cbh_command = f'hmmsearch -T 0 --incT 0 --nobias {ncbi_cbh_hmm} {fastafile} > ' \
                   f'{ncbi_cbh_out}'
ncbi_egl_command = f'hmmsearch -T 0 --incT 0 --nobias {ncbi_egl_hmm} {fastafile} > ' \
                   f'{ncbi_egl_out}'

# Run commands to align 1,748 sequences to HMM
subprocess.call(swiss_cbh_command, shell=True)
subprocess.call(swiss_cbh_command, shell=True)
subprocess.call(swiss_cbh_command, shell=True)
subprocess.call(swiss_cbh_command, shell=True)


# Collect results and write to spreadsheet
swiss_results = compare_hmmscores(fasta=fastafile, hmm1=swiss_cbh_out, 
                                  hmm2=swiss_egl_out)
swiss_results['diff_score'] = pd.Series(np.array(swiss_results.iloc[:,1]) - 
                                       np.array(swiss_results.iloc[:,2]))
swiss_results['pred_class'] = pd.Series([1 if x > 0 else 0 for x in swiss_results.iloc[:,3]])
ncbi_results = compare_hmmscores(fasta=fastafile, hmm1=ncbi_cbh_out,
                               hmm2=ncbi_egl_out)
ncbi_results['diff_score'] = pd.Series(np.array(ncbi_results.iloc[:,1]) - 
                                      np.array(ncbi_results.iloc[:,2]))
ncbi_results['pred_class'] = pd.Series([1 if x > 0 else 0 for x in ncbi_results.iloc[:,3]])
all_results = swiss_results.append(ncbi_results)
all_results.columns = ['Accession', 'swiss_cbh_scores', 'swiss_egl_scores', 
                       'swiss_diff_scores', 'swiss_pred_class', 'ncbi_cbh_scores', 
                       'ncbi_egl_scores', 'ncbi_diff_scores','ncbi_pred_class']
all_results.index = range(1, len(store) + 1)
all_results.to_csv('results_final/cel7_subtypes.csv')


