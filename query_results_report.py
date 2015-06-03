# import glob
import os
from rdflib.graph import Graph

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
data_dir = os.path.join(SCRIPT_DIR, "data", "data_spm_fsl")

studies = next(os.walk(data_dir))[1]

con_maps = dict()
sterr_maps = dict()

SPM_SOFTWARE = "http://neurolex.org/wiki/nif-0000-00343"
FSL_SOFTWARE = "http://neurolex.org/wiki/birnlex_2067"

owl_file = "https://raw.githubusercontent.com/incf-nidash/nidm/master/nidm/\
nidm-results/terms/releases/nidm-results_100.owl"

for study in [studies[0], studies[15]]:
    nidm_dir = os.path.join(data_dir, study)
    assert os.path.isdir(nidm_dir)

    nidm_doc = os.path.join(nidm_dir, "nidm.ttl")
    print nidm_doc
    nidm_graph = Graph()
    nidm_graph.parse(nidm_doc, format='turtle')

    query = """
    prefix prov: <http://www.w3.org/ns/prov#>
    prefix nidm: <http://purl.org/nidash/nidm#>

    prefix ModelParamEstimation: <http://purl.org/nidash/nidm#NIDM_0000056>
    prefix withEstimationMethod: <http://purl.org/nidash/nidm#NIDM_0000134>
    prefix errorVarianceHomogeneous: <http://purl.org/nidash/nidm#NIDM_0000094>
    prefix SearchSpaceMaskMap: <http://purl.org/nidash/nidm#NIDM_0000068>
    prefix contrastName: <http://purl.org/nidash/nidm#NIDM_0000085>
    prefix StatisticMap: <http://purl.org/nidash/nidm#NIDM_0000076>
    prefix searchVolumeInVoxels: <http://purl.org/nidash/nidm#NIDM_0000121>
    prefix searchVolumeInUnits: <http://purl.org/nidash/nidm#NIDM_0000136>
    prefix HeightThreshold: <http://purl.org/nidash/nidm#NIDM_0000034>
    prefix userSpecifiedThresholdType: <http://purl.org/nidash/\
nidm#NIDM_0000125>
    prefix ExtentThreshold: <http://purl.org/nidash/nidm#NIDM_0000026>
    prefix ExcursionSetMap: <http://purl.org/nidash/nidm#NIDM_0000025>
    prefix softwareVersion: <http://purl.org/nidash/nidm#NIDM_0000122>

    SELECT DISTINCT ?est_method ?homoscedasticity ?contrast_name
            ?search_vol_vox ?search_vol_units
            ?extent_thresh ?user_extent_thresh ?height_thresh
            ?user_height_thresh ?software ?excursion_set_id ?soft_version
        WHERE {
        ?mpe a ModelParamEstimation: .
        ?mpe withEstimationMethod: ?est_method .
        ?mpe prov:used ?error_model .
        ?error_model errorVarianceHomogeneous: ?homoscedasticity .
        ?stat_map prov:wasGeneratedBy/prov:used/prov:wasGeneratedBy ?mpe ;
                  a StatisticMap: ;
                  contrastName: ?contrast_name .
        ?search_region prov:wasGeneratedBy ?inference ;
                       a SearchSpaceMaskMap: ;
                       searchVolumeInVoxels: ?search_vol_vox ;
                       searchVolumeInUnits: ?search_vol_units .
        ?extent_thresh a ExtentThreshold: .
        OPTIONAL {
            ?extent_thresh userSpecifiedThresholdType: ?user_extent_thresh
        } .
        ?height_thresh a HeightThreshold: ;
                       userSpecifiedThresholdType: ?user_height_thresh .
        ?inference prov:used ?stat_map ;
                   prov:used ?extent_thresh ;
                   prov:used ?height_thresh ;
                   prov:wasAssociatedWith ?soft_id .
        ?soft_id a ?software ;
                   softwareVersion: ?soft_version .
        ?excursion_set_id a ExcursionSetMap: ;
                   prov:wasGeneratedBy ?inference .

        FILTER(?software NOT IN (prov:SoftwareAgent, prov:Agent))

    }

    """
    sd = nidm_graph.query(query)

    Z_STATISTIC = 'Z-Statistic'
    P_VALUE_FWER = 'p-value FWE'
    P_VALUE_FDR = 'p-value FDR'
    P_VALUE_UNCORRECTED = 'p-value uncorrected'
    P_VALUE_UNC = 'p-value unc.'
    CLUSTER_SIZE = 'Cluster size'

        # ?inference prov:used ?height_thresh .
        # ?height_thresh a HeightThreshold: ;
        #                userSpecifiedThresholdType: ?height_thresh_type ;
        #                prov:value ?height_thresh_value .

    owl_graph = Graph()
    owl_graph.parse(owl_file, format='turtle')

    if sd:
        for row in sd:
            est_method, homoscedasticity, contrast_name, \
                search_vol_vox, search_vol_units, extent_thresh, \
                user_extent_thresh, height_thresh, user_height_thresh, \
                software, exc_set, soft_version = row

            if user_extent_thresh is None:
                user_extent_thresh = CLUSTER_SIZE

            user_extent_thresh = str(user_extent_thresh)
            user_height_thresh = str(user_height_thresh)

            if str(contrast_name) == "pain: group mean ac" or \
               str(contrast_name) == "pain: group mean" or \
               str(contrast_name) == "Group: pain":

                thresh = {
                    Z_STATISTIC: 'prov:value',
                    CLUSTER_SIZE: 'nidm:NIDM_0000084',
                    P_VALUE_FWER: 'pValueFWER:',
                    P_VALUE_FDR: 'pValueFDR:',
                    P_VALUE_UNCORRECTED: 'pValueUncorrected:',
                    P_VALUE_UNC: 'pValueUncorrected:'}

    # FIXME: add pvalueFDR
                query = """
        prefix prov: <http://www.w3.org/ns/prov#>
        prefix nidm: <http://purl.org/nidash/nidm#>

        prefix pValueFWER: <http://purl.org/nidash/nidm#NIDM_0000115>
        prefix pValueUncorrected: <http://purl.org/nidash/nidm#NIDM_0000116>

        SELECT DISTINCT ?extent_value ?height_value WHERE {
            OPTIONAL {<"""+str(extent_thresh)+"> " + \
                    thresh[user_extent_thresh] + """ ?extent_value }.
            <"""+str(height_thresh)+"> " + \
                    thresh[user_height_thresh]+""" ?height_value .
        }
                """
                thresholds = nidm_graph.query(query)
                if thresholds:
                    assert len(thresholds) == 1
                    for th_row in thresholds:
                        extent_value, height_value = th_row
                        if extent_value is None:
                            extent_value = 0

                # Convert all info to text
                thresh = ""
                multiple_compa = ""
                if str(user_extent_thresh) in [P_VALUE_FDR, P_VALUE_FWER]:
                    inference_type = "Cluster-wise"
                    multiple_compa = "with correction for multiple \
comparisons "
                    thresh = "P < %0.2f" % float(extent_value)
                    if user_extent_thresh == P_VALUE_FDR:
                        thresh += " FDR-corrected"
                    else:
                        thresh += " FWER-corrected"

                    thresh += " (cluster defining threshold "
                    if user_height_thresh == P_VALUE_UNCORRECTED:
                        thresh += "P < %0.2f)" % float(height_value)
                    if user_height_thresh == Z_STATISTIC:
                        thresh += "Z > %0.2f)" % float(height_value)
                else:
                    inference_type = "Voxel-wise"
                    if user_height_thresh in [P_VALUE_FDR, P_VALUE_FWER]:
                        multiple_compa = "with correction for multiple \
comparisons "
                        thresh = "P < %0.2f" % float(height_value)
                        if user_height_thresh == P_VALUE_FDR:
                            thresh += " FDR-corrected"
                        else:
                            thresh += " FWER-corrected"
                    elif user_height_thresh in \
                            [P_VALUE_UNCORRECTED, P_VALUE_UNC]:
                        thresh = "P < %0.2f uncorrected" % float(height_value)
                    elif user_height_thresh == Z_STATISTIC:
                        thresh = "Z > %0.2f uncorrected" % float(height_value)

                    thresh += " and clusters smaller than %d were discarded" \
                              % int(extent_value)

                if homoscedasticity:
                    variance = 'equal'
                else:
                    variance = 'unequal'

                print "-------------------"
                print "Group statistic was performed in %s (version %s). \
%s was performed assuming %s variances. %s inference \
was performed %susing a threshold %s. The search volume was %d cm^3 \
(%d voxels)." % (
                    owl_graph.label(software), soft_version,
                    owl_graph.label(est_method).capitalize(), variance, inference_type,
                    multiple_compa, thresh, float(search_vol_units)/1000,
                    int(search_vol_vox))

                print "-------------------"



                # print "row:"
                # for el in row:
                #     print str(el)
                # print "\n"
            else:
                print str(contrast_name)

    else:
        print "not found"

    # print "%s activated? %d" % (study, study_activated)
