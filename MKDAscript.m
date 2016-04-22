
COI_directory = 'pain_subset_contrast_test'; %- This is the directory where data of the chosen contrast will be stored
iterations = 300; %- Iterations of Monte Carlo method
dbname ='pain_subset.txt'; %- Name of the database (must be a .txt file)

read_database;
DB=Meta_Setup (DB, 10);

mkdir(COI_directory);
cd(COI_directory);

DB=Meta_Select_Contrasts(DB);
save SETUP DB
load SETUP.mat

MC_Setup = Meta_Activation_FWE('setup', DB); %- This should create a MC_Info.mat file. This may not happen if this file exists in another directory.
load MC_Info.mat

Meta_Activation_FWE('mc',iterations);
Meta_Activation_FWE('results', 1);