
COI_directory = 'pain_contrast'; %- This is the directory where data of the chosen contrast will be stored.
iterations = 15000; %- Iterations of Monte Carlo method.
dbname ='pain.csv'; %- Name of the database (must be a .txt file).

read_database; %- This genereates a .mat file named by the user containing the database information. For this study the file was called 'pain'.
DB=Meta_Setup (DB, 10);

mkdir(COI_directory);
cd(COI_directory);

DB=Meta_Select_Contrasts(DB); %- During this stage the user specifies which variables (regressors) will be used during the analysis numerically after choosing one of the database fields.
								%- For this study the field name is 'Name' and the pain variable is chosen numerically with the value '1'. 
save SETUP DB  
load SETUP.mat

MC_Setup = Meta_Activation_FWE('setup', DB); %- Here the user must specify which contrasts will be computed in the analysis. An MC_Info.mat file is created. Note, this may not happen if this file exists in another directory.
												%- For this study we compute the pain vs baseline contrast. First enter the value '1' to compute contrasts across conditions. Pick 'Name' for the field name, choose pain as the variable numerically with the value '1', then use '[1]' as the contrast, and call the contrast 'pain_vs_baseline'.
load MC_Info.mat

Meta_Activation_FWE('mc',iterations); %- 15000 iterations were used for the pain study. 
Meta_Activation_FWE('results', 1);