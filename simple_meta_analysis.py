"""
Perform a simple meta-analysis (as the third level of a hierarchical GLM)
based on a set of NIDM-Results exports.

@author: Camille Maumet <c.m.j.maumet@warwick.ac.uk>
@copyright: University of Warwick 2015
"""
import os
from rdflib.graph import Graph, Namespace
from subprocess import check_call
import collections

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
data_dir = os.path.join(SCRIPT_DIR, "data", "data_spm_fsl")
pre_dir = os.path.join(SCRIPT_DIR, "pre")

if not os.path.exists(pre_dir):
    os.makedirs(pre_dir)

studies = next(os.walk(data_dir))[1]

con_maps = dict()
varcon_maps = dict()
mask_maps = dict()

ma_mask_name = os.path.join(pre_dir, "meta_analysis_mask")
ma_mask = None

NLX = Namespace("http://neurolex.org/wiki/")
SPM_SOFTWARE = NLX["nif-0000-00343"]
FSL_SOFTWARE = NLX["birnlex_2067"]


# studies = studies[0:3]

for study in studies:
    print "\nStudy: " + study

    nidm_dir = os.path.join(data_dir, study)
    assert os.path.isdir(nidm_dir)

    nidm_doc = os.path.join(nidm_dir, "nidm.ttl")

    nidm_graph = Graph()
    nidm_graph.parse(nidm_doc, format='turtle')

    query = """
    prefix prov: <http://www.w3.org/ns/prov#>
    prefix nidm: <http://purl.org/nidash/nidm#>

    prefix contrast_estimation: <http://purl.org/nidash/nidm#NIDM_0000001>
    prefix contrast_map: <http://purl.org/nidash/nidm#NIDM_0000002>
    prefix stderr_map: <http://purl.org/nidash/nidm#NIDM_0000013>
    prefix contrast_name: <http://purl.org/nidash/nidm#NIDM_0000085>
    prefix statistic_map: <http://purl.org/nidash/nidm#NIDM_0000076>
    prefix mask_map: <http://purl.org/nidash/nidm#NIDM_0000054>

    SELECT ?contrastName ?con_file ?std_file
    ?mask_file ?software WHERE {
     ?con_id a contrast_map: ;
          contrast_name: ?contrastName ;
          prov:atLocation ?con_file ;
          prov:wasGeneratedBy ?con_est .
     ?std_id a stderr_map: ;
          prov:atLocation ?std_file ;
          prov:wasGeneratedBy ?con_est .
     ?mask_id a mask_map: ;
          prov:atLocation ?mask_file .
     ?soft_id a ?software .
     ?con_est a contrast_estimation: ;
              prov:wasAssociatedWith ?soft_id ;
              prov:used ?mask_id .

      FILTER(?software NOT IN (
        prov:SoftwareAgent, prov:Agent))
    }

    """
    sd = nidm_graph.query(query)

    if sd:
        for row in sd:
            con_name, con_file, std_file, mask_file, software = row

            if str(con_name) == "pain: group mean ac" or \
               str(con_name) == "pain: group mean" or \
               str(con_name) == "Group: pain":

                if str(software) == SPM_SOFTWARE:
                    print "--> analyzed with SPM"
                    # If study was performed with SPM, reslice to FSL's
                    # template space
                    for to_reslice in [con_file, std_file, mask_file]:
                        file_name = os.path.basename(to_reslice).split(".")[0]
                        resliced_file = os.path.join(
                            pre_dir, study + "_" + file_name + "_r")
                        check_call(
                            ["cd \"" + nidm_dir + "\";" +
                             " flirt -in " + file_name + " -ref " +
                             "$FSLDIR/data/standard/MNI152_T1_2mm -applyxfm " +
                             "-usesqform " +
                             "-out " + resliced_file],
                            shell=True)

                        if to_reslice == mask_file:
                            mask_file = resliced_file
                        elif to_reslice == con_file:
                            con_maps[study] = resliced_file
                        elif to_reslice == std_file:
                            std_file = resliced_file

                elif str(software == FSL_SOFTWARE):
                    print "--> analyzed with FSL"
                    # If study was performed with FSL, rescale to a target
                    # value of 100
                    for to_rescale in [con_file, std_file]:
                        file_name = os.path.basename(to_rescale).split(".")[0]
                        rescaled_file = os.path.join(
                            pre_dir, study + "_" + file_name + "_s")
                        check_call(
                            ["cd \"" + nidm_dir + "\";" +
                             " fslmaths \"" + file_name + "\" -div 100 " +
                             " \"" + rescaled_file + "\""],
                            shell=True)
                        if to_rescale == con_file:
                            con_maps[study] = "\"" + rescaled_file + "\""
                        elif to_rescale == std_file:
                            std_file = "\"" + rescaled_file + "\""

                    mask_file = mask_file.replace("file://.", nidm_dir)

                varcope_file = "\"" + \
                               os.path.join(pre_dir, study + "_varcope") + \
                               "\""
                check_call([" fslmaths " + std_file + " -sqr " + varcope_file],
                           shell=True)
                varcon_maps[study] = varcope_file

                # Compute meta-analysis mask as the intersection of all
                # study analysis masks
                if ma_mask is None:
                    ma_mask = mask_file
                else:
                    check_call(
                        [" fslmaths \"" + mask_file + "\" -min " +
                         "\"" + ma_mask + "\" \"" + ma_mask_name + "\""],
                        shell=True)
                    ma_mask = ma_mask_name
            else:
                print "Ignore contrast '" + str(con_name) + "'."

    else:
        print "Query returned no results for study "+study+"."

# Binarize the analysis mask
print ["fslmaths \"" + ma_mask + "\" -thr 0.9 -bin " + ma_mask]
check_call(["fslmaths \"" + ma_mask + "\" -thr 0.9 -bin \"" +
            ma_mask + "\""], shell=True)

# Sort copes and varcopes by study names
to_merge = {'copes': collections.OrderedDict(sorted(con_maps.items())),
            'varcopes': collections.OrderedDict(sorted(varcon_maps.items()))}
for file_name, files in to_merge.items():

    check_call(
        ["fslmerge -t \""+os.path.join(pre_dir, file_name) +
         ".nii.gz\" "+" ".join(files.values())],
        shell=True)

check_call([
    "cd " + pre_dir + "; flameo --cope=copes --vc=varcopes --ld=stats "
    " --dm=../fsl_design/simple_meta_analysis.mat"
    " --cs=../fsl_design/simple_meta_analysis.grp"
    " --tc=../fsl_design/simple_meta_analysis.con "
    " --mask=\""+ma_mask_name+"\" --runmode=flame1"], shell=True)

# print ["cd " + pre_dir + "; fslmaths stats/zstat1 -ztop stats/p_unc"]
# check_call(["cd " + pre_dir + "; fslmaths stats/zstat1 -ztop stats/p_unc"])
# print ["cd " + pre_dir + "; fdr -i stats/p_unc -q 0.05 -a stats/thresh_fdr05_p_adj"]
# check_call(["cd " + pre_dir + "; fdr -i stats/p_unc -q 0.05 -a stats/thresh_fdr05_p_adj"])
# fslmaths stats/thresh_fdr05_p_adj_m.nii.gz -mul -1 -add 1 -thr 0.95 -mas stats/mask.nii.gz stats/thresh_fdr05_1mp_adj_m.nii.gz
# fslmaths stats/zstat1.nii.gz -mas stats/thresh_fdr05_1mp_adj_m.nii.gz -mas stats/mask.nii.gz stats/thresh_zstat1.nii.gz
# ttologp -logpout logp1 varcope1 cope1 20
# fslmaths logp1.nii.gz -div -2.3026 -mas mask.nii.gz -mas thresh_zstat1.nii.gz thresh_minuslog10p1.nii.gz