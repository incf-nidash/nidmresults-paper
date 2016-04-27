
COI_directory = 'pain_contrast'; %- This is the directory where data of the chosen contrast will be stored
iterations = 15000; %- Iterations of Monte Carlo method
dbname ='pain.csv'; %- Name of the database (must be a .txt file)

read_database; %- This genereates a .mat file named by the user containing the database information
DB=Meta_Setup (DB, 10);

mkdir(COI_directory);
cd(COI_directory);

DB=Meta_Select_Contrasts(DB); %- During this stage the specifies which variables (regressors) will be used during the analysis
save SETUP DB  
load SETUP.mat

MC_Setup = Meta_Activation_FWE('setup', DB); %- Here the user must specify which contrasts will be computed in the analysis. An MC_Info.mat file is created. Note, this may not happen if this file exists in another directory.
load MC_Info.mat

Meta_Activation_FWE('mc',iterations);
Meta_Activation_FWE('results', 1);