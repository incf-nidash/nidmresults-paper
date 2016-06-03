"""
Perform a simple meta-analysis (as the third level of a hierarchical GLM)
based on a set of NIDM-Results exports.

@author: Camille Maumet <c.m.j.maumet@warwick.ac.uk>
@copyright: University of Warwick 2015
"""
import os
from rdflib.graph import Graph
from rdflib.term import URIRef
from subprocess import check_call
from nidmresults.objects.constants import SCR_FSL, SCR_SPM
import collections
import glob
import zipfile

if __name__ == '__main__':
    SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
    data_dir = os.path.join(SCRIPT_DIR, "input", "data", "pain")
    print data_dir
    assert os.path.isdir(data_dir)

    FSL_DESIGN_DIR = os.path.join(
        SCRIPT_DIR, "input", "IBMA", "fsl_design")
    assert os.path.isdir(FSL_DESIGN_DIR)

    out_dir = os.path.join(SCRIPT_DIR, "output", "IBMA", "data")
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    studies = glob.glob(os.path.join(data_dir, '*.nidm.zip'))

    con_maps = dict()
    varcon_maps = dict()
    mask_maps = dict()

    ma_mask_name = os.path.join(out_dir, "mask_ma")
    ma_mask = None

    # studies = studies[0:3]

    for nidm_file in studies:
        study = os.path.basename(nidm_file.replace(".nidm.zip", ""))
        nidm_dir = os.path.join(out_dir, "pre", study)
        print "\nStudy: " + study

        with zipfile.ZipFile(nidm_file) as z:
            if not os.path.exists(nidm_dir):
                os.makedirs(nidm_dir)
            z.extractall(nidm_dir)

        nidm_doc = os.path.join(nidm_dir, "nidm.ttl")
        assert os.path.isfile(nidm_doc)

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
                con_file = os.path.join(nidm_dir, con_file)
                std_file = os.path.join(nidm_dir, std_file)
                mask_file = os.path.join(nidm_dir, mask_file)

                if str(con_name) == "pain":
                    if software == URIRef(SCR_SPM.uri):
                        print "--> analyzed with SPM"
                        # If study was performed with SPM, reslice to FSL's
                        # template space
                        for to_reslice in [con_file, std_file, mask_file]:
                            file_name = os.path.basename(
                                to_reslice).split(".")[0]
                            resliced_file = os.path.join(
                                out_dir, study + "_" + file_name + "_r")
                            cmd = [
                                "cd \"" + nidm_dir + "\";" +
                                " flirt -in " + file_name + " -ref " +
                                "$FSLDIR/data/standard/MNI152_T1_2mm " +
                                "-applyxfm -usesqform " +
                                "-out " + resliced_file
                                ]
                            print "Running " + ",".join(cmd)
                            check_call(cmd, shell=True)

                            if to_reslice == mask_file:
                                mask_file = resliced_file
                            elif to_reslice == con_file:
                                con_maps[study] = resliced_file
                            elif to_reslice == std_file:
                                std_file = resliced_file

                    elif software == URIRef(SCR_FSL.uri):
                        print "--> analyzed with FSL"
                        # If study was performed with FSL, rescale to a target
                        # value of 100
                        for to_rescale in [con_file, std_file]:
                            file_name = os.path.basename(
                                to_rescale).split(".")[0]
                            rescaled_file = os.path.join(
                                out_dir, study + "_" + file_name + "_s")
                            cmd = [
                                "cd \"" + nidm_dir + "\";" +
                                " fslmaths \"" + file_name + "\" -div 100 " +
                                " \"" + rescaled_file + "\""
                                ]
                            print "Running " + ",".join(cmd)
                            check_call(cmd, shell=True)

                            if to_rescale == con_file:
                                con_maps[study] = "\"" + rescaled_file + "\""
                            elif to_rescale == std_file:
                                std_file = "\"" + rescaled_file + "\""

                        mask_file = mask_file.replace("file://.", nidm_dir)

                    else:
                        raise Exception(
                            'Unknown neuroimaging software: ' + str(software))

                    # Create varcope from standard error map
                    varcope_file = "\"" + \
                                   os.path.join(out_dir, study + "_varcope") +\
                                   "\""
                    cmd = [" fslmaths " + std_file + " -sqr " + varcope_file]
                    print "Running " + ",".join(cmd)
                    check_call(cmd, shell=True)

                    varcon_maps[study] = varcope_file

                    # Compute meta-analysis mask as the intersection of all
                    # study analysis masks
                    if ma_mask is None:
                        ma_mask = mask_file
                    else:
                        cmd = [
                            " fslmaths \"" + mask_file + "\" -min " +
                            "\"" + ma_mask + "\" \"" + ma_mask_name + "\""
                            ]
                        print "Running " + ",".join(cmd)
                        check_call(cmd, shell=True)
                        ma_mask = ma_mask_name
                else:
                    print "Ignore contrast '" + str(con_name) + "'."

        else:
            print "Query returned no results for study "+study+"."

    # Binarize the analysis mask
    cmd = ["fslmaths \"" + ma_mask + "\" -thr 0.9 -bin \"" + ma_mask + "\""]
    print "Running " + ",".join(cmd)
    check_call(cmd, shell=True)

    # Sort copes and varcopes by study names
    to_merge = {'copes': collections.OrderedDict(sorted(con_maps.items())),
                'varcopes': collections.OrderedDict(
                    sorted(varcon_maps.items()))}
    for file_name, files in to_merge.items():
        cmd = [
            "fslmerge -t \""+os.path.join(out_dir, file_name) +
            ".nii.gz\" "+" ".join(files.values())
        ]
        print "Running " + ",".join(cmd)
        check_call(cmd, shell=True)

    # Remove NaNs from copes and varcopes
    # (SPM code background with NaNs while FSL uses zeros)
    cmd = ["cd " + out_dir + "; fslmaths copes.nii.gz -nan copes"]
    print "Running " + ",".join(cmd)
    check_call(cmd, shell=True)

    cmd = ["cd " + out_dir + "; fslmaths varcopes.nii.gz -nan varcopes"]
    print "Running " + ",".join(cmd)
    check_call(cmd, shell=True)

    # Mixed-effects GLM (study-level)
    cmd = [
        "cd " + out_dir + "; flameo --cope=copes --vc=varcopes --ld=stats "
        " --dm=" + os.path.join(FSL_DESIGN_DIR, "simple_meta_analysis.mat") +
        " --cs=" + os.path.join(FSL_DESIGN_DIR, "simple_meta_analysis.grp") +
        " --tc=" + os.path.join(FSL_DESIGN_DIR, "simple_meta_analysis.con ") +
        " --mask=\""+ma_mask_name+"\" --runmode=flame1"]
    print "Running " + ",".join(cmd)
    check_call(cmd, shell=True)

    stat_dir = os.path.join(out_dir, "stats")

    # FWE Voxel-wise corrected threshold p<0.05 (with a cluster forming
    # threshold of p<0.001 uncorrected)
    # Scripts from http://blogs.warwick.ac.uk/nichols/entry/flame_without_1st/
    cmd = [
        "cd " + out_dir + "; " +
        "echo $($FSLDIR/bin/fslnvols copes) - 1 | bc -l  > stats/dof ;" +
        "/bin/rm -f stats/zem* stats/zols* stats/mask* ;" +
        "$FSLDIR/bin/smoothest -d $(cat stats/dof) -m " + ma_mask_name +
        " -r stats/res4d > stats/smoothness ;" +
        "awk '/VOLUME/ {print $2}' stats/smoothness > thresh_zstat1.vol ;" +
        "awk '/DLH/ {print $2}' stats/smoothness > thresh_zstat1.dlh ;" +
        "$FSLDIR/bin/fslmaths stats/zstat1 -mas " + ma_mask_name +
        " thresh_zstat1;" +
        "$FSLDIR/bin/cluster -i thresh_zstat1 -c stats/cope1 -t 3.1 -p 0.05" +
        " -d $(cat thresh_zstat1.dlh) --volume=$(cat thresh_zstat1.vol) " +
        "--othresh=thresh_zstat1 -o cluster_mask_zstat1 --connectivity=26 " +
        "--mm --olmax=lmax_zstat1_tal.txt > cluster_zstat1_std.txt;" +
        "$FSLDIR/bin/cluster2html . cluster_zstat1 -std;" +
        "MinMax=$($FSLDIR/bin/fslstats thresh_zstat1 -l 0.0001 -R);" +
        "$FSLDIR/bin/overlay 1 0 $FSLDIR/data/standard/MNI152_T1_1mm.nii.gz " +
        "-a thresh_zstat1 $MinMax " +
        "rendered_thresh_zstat1;" +
        "$FSLDIR/bin/slicer rendered_thresh_zstat1 -S 2 750 " +
        "rendered_thresh_zstat1.png;" +
        "cp $FSLDIR/etc/luts/ramp.gif .ramp.gif"
    ]
    print "Running " + ",".join(cmd)
    check_call(cmd, shell=True)
