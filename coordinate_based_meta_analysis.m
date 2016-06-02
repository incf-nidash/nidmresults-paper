
COI_directory = 'pain_contrast'; % directory where data will be stored
iterations = 15000; % iterations of Monte Carlo method
% Path to the database
dbname = fullfile(pwd, 'input', 'coordinate-based meta-analysis', 'pain.csv'); 

% Genereates a .mat file containing the database information. 
% - When prompted 'Enter name of file to save (without .mat extension):'
%   enter 'pain'.
read_database; 
DB=Meta_Setup(DB, 15);

mkdir(COI_directory);
cd(COI_directory);

% Specify which variables (regressors) will be used during the analysis
% - When prompted 'Enter field name or end if finished:' enter 'Name'.
% - When prompted 'Enter vector of levels to use: :' enter '1'.
% - When prompted 'Enter field name or end if finished:' press return.
DB=Meta_Select_Contrasts(DB); 
								
save SETUP DB  
load SETUP.mat

% Specify which contrasts will be computed in the analysis. 
% An MC_Info.mat file is created. Note, this may not happen if this file 
% exists in another directory.
% - When prompted 'Compute contrasts across conditions also? (1/0)' enter '1'. 
% - When prompted 'Enter field name or end if finished:' enter 'Name'.
% - When prompted 'Enter vector of levels to use:' enter '1'.
% - When prompted 'Enter contrast across 1 conditions in [], return to quit:' 
%   enter '[1]'.
% - When prompted 'Enter short name for this contrast, no spaces or special 
%   chars:' enter 'pain_vs_baseline'
% - When prompted 'Enter contrast across 1 conditions in [], return to quit:' 
%   press return.
% - When prompted 'Enter field name or end if finished:' press return.
MC_Setup = Meta_Activation_FWE('setup', DB); 

load MC_Info.mat

Meta_Activation_FWE('mc',iterations);
Meta_Activation_FWE('results', 1, 'stringent');