"""
Display a paragraph describing the method used for group statistics based on
two NIDM-Results export: one from SPM, one from FSL.

@author: Camille Maumet <c.m.j.maumet@warwick.ac.uk>
@copyright: University of Warwick 2015
"""

import os
import re
import glob
import logging
import zipfile
from urllib2 import urlopen, URLError, HTTPError
import tempfile
from rdflib.graph import Graph, Namespace
from nidmresults import latest_owlfile as owl_file
from nidmresults.objects.constants_rdflib import *

if __name__ == '__main__':

    SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
    data_dir = os.path.join(SCRIPT_DIR, "input", "data", "examples")
    assert os.path.isdir(data_dir)

    # Examples of NIDM-Results archives
    export_dirs = glob.glob(os.path.join(data_dir, '*.nidm.zip'))

    OBO = Namespace("http://purl.obolibrary.org/obo/")

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    tmpdir = tempfile.mkdtemp()

    def threshold_txt(owl_graph, thresh_type, value, stat_type):
        multiple_compa = ""
        is_p_value = True
        if thresh_type in [OBO_Q_VALUE_FDR, OBO_P_VALUE_FWER]:
            multiple_compa = "with correction for multiple comparisons "
            if thresh_type == OBO_Q_VALUE_FDR:
                thresh = "Q <= "
            else:
                thresh = "P <= "
        elif thresh_type == NIDM_P_VALUE_UNCORRECTED_CLASS:
            thresh = "P <= "
        elif thresh_type == OBO_STATISTIC:
            is_p_value = False
            stat_abv = owl_graph.label(stat_type).replace("-OBO_STATISTIC", "")
            thresh = stat_abv + " >= "
        else:
            raise Exception("Unknown threshold type:" + str(thresh_type))

        thresh += "%0.3f" % float(value)

        if is_p_value:
            thresh += " (%s)" % (owl_graph.label(
                thresh_type).replace(" p-value", "").replace("P-Value ", ""))

        return list([thresh, multiple_compa])

    for url in export_dirs:
        if url.startswith("http:"):
            # Copy .nidm.zip export locally in a temp directory
            try:
                f = urlopen(url)
                data_id = re.search('id=(\w+)', url).groups()[0]
                tmpzip = os.path.join(tmpdir, data_id + ".nidm.zip")

                logger.info("downloading " + url + " at " + tmpzip)
                with open(tmpzip, "wb") as local_file:
                    local_file.write(f.read())

            except HTTPError, e:
                raise Exception(["HTTP Error:" + e.code + url])
            except URLError, e:
                raise Exception(["URL Error:" + e.reason + url])

            nidm_dir = os.path.join(tmpdir, data_id)
        else:
            tmpzip = url
            nidm_dir = tmpzip.replace(".nidm.zip", "")

        # Unzip NIDM-Results export
        with zipfile.ZipFile(tmpzip, 'r') as zf:
            zf.extractall(nidm_dir)

        nidm_doc = os.path.join(nidm_dir, "nidm.ttl")
        nidm_graph = Graph()
        nidm_graph.parse(nidm_doc, format='turtle')

        # Retreive the information of interest for the report by querying the
        # NIDM-Results export
        query = """
        prefix prov: <http://www.w3.org/ns/prov#>
        prefix nidm: <http://purl.org/nidash/nidm#>

        prefix nidm_Data: <http://purl.org/nidash/nidm#NIDM_0000169>
        prefix ModelParamEstimation: <http://purl.org/nidash/nidm#NIDM_0000056>
        prefix withEstimationMethod: <http://purl.org/nidash/nidm#NIDM_0000134>
        prefix errorVarianceHomogeneous: <http://purl.org/nidash/nidm#NIDM_0000094>
        prefix SearchSpaceMaskMap: <http://purl.org/nidash/nidm#NIDM_0000068>
        prefix contrastName: <http://purl.org/nidash/nidm#NIDM_0000085>
        prefix statisticType: <http://purl.org/nidash/nidm#NIDM_0000123>
        prefix statisticMap: <http://purl.org/nidash/nidm#NIDM_0000076>
        prefix searchVolumeInVoxels: <http://purl.org/nidash/nidm#NIDM_0000121>
        prefix searchVolumeInUnits: <http://purl.org/nidash/nidm#NIDM_0000136>
        prefix HeightThreshold: <http://purl.org/nidash/nidm#NIDM_0000034>
        prefix userSpecifiedThresholdType: <http://purl.org/nidash/nidm#NIDM_0000125>
        prefix ExtentThreshold: <http://purl.org/nidash/nidm#NIDM_0000026>
        prefix ExcursionSetMap: <http://purl.org/nidash/nidm#NIDM_0000025>
        prefix softwareVersion: <http://purl.org/nidash/nidm#NIDM_0000122>
        prefix clusterSizeInVoxels: <http://purl.org/nidash/nidm#NIDM_0000084>
        prefix obo_studygrouppopulation: <http://purl.obolibrary.org/obo/STATO_0000193>
        prefix nidm_hasErrorDependence: <http://purl.org/nidash/nidm#NIDM_0000100>
        prefix nidm_dependenceMapWiseDependence: <http://purl.org/nidash/nidm#NIDM_0000089>
        prefix nidm_DesignMatrix: <http://purl.org/nidash/nidm#NIDM_0000019>
        prefix nidm_hasDriftModel: <http://purl.org/nidash/nidm#NIDM_0000088>
        prefix fsl_driftCutoffPeriod: <http://purl.org/nidash/fsl#FSL_0000004>
        prefix spm_SPMsDriftCutoffPeriod: <http://purl.org/nidash/spm#SPM_0000001>

        SELECT DISTINCT ?est_method ?homoscedasticity ?contrast_name ?stat_type
                ?search_vol_vox ?search_vol_units
                ?extent_thresh_value ?height_thresh_value
                ?extent_thresh_type ?height_thresh_type
                ?software ?excursion_set_id ?soft_version ?subjects_type
                ?var_spatial ?covar ?covar_spatial ?drift_model ?fsl_drift_cutoff
                ?spm_drift_cutoff
            WHERE {
            ?mpe a ModelParamEstimation: ;
                withEstimationMethod: ?est_method ;
                prov:used ?error_model ;
                prov:used ?data ;
                prov:used ?design_matrix .
            ?design_matrix a nidm_DesignMatrix: .
            OPTIONAL {
                ?design_matrix nidm_hasDriftModel: ?drift_model_id .
                ?drift_model_id a ?drift_model .

                FILTER(?drift_model NOT IN (prov:Entity))
            } .
            OPTIONAL {
                ?drift_model_id fsl_driftCutoffPeriod: ?fsl_drift_cutoff .
            } .
            OPTIONAL {
                ?drift_model_id spm_SPMsDriftCutoffPeriod: ?spm_drift_cutoff .
            } .
            ?error_model errorVarianceHomogeneous: ?homoscedasticity ;
                nidm_varianceMapWiseDependence: ?var_spatial ;
                nidm_hasErrorDependence: ?covar .
            OPTIONAL {?error_model nidm_dependenceMapWiseDependence: ?covar_spatial }.
            ?data a nidm_Data: ;
                prov:wasAttributedTo ?group_or_subject .
            {
                ?group_or_subject a prov:Person
            } UNION {
                ?group_or_subject a obo_studygrouppopulation:
            } .
            ?group_or_subject a ?subjects_type .
            ?stat_map prov:wasGeneratedBy/prov:used/prov:wasGeneratedBy ?mpe ;
                      a statisticMap: ;
                      statisticType: ?stat_type ;
                      contrastName: ?contrast_name .
            ?search_region prov:wasGeneratedBy ?inference ;
                           a SearchSpaceMaskMap: ;
                           searchVolumeInVoxels: ?search_vol_vox ;
                           searchVolumeInUnits: ?search_vol_units .
            ?extent_thresh a ExtentThreshold: ;
                           a ?extent_thresh_type .
            {
                ?extent_thresh prov:value ?extent_thresh_value
            } UNION {
                ?extent_thresh clusterSizeInVoxels: ?extent_thresh_value
            } .
            ?height_thresh a HeightThreshold: ;
                           a ?height_thresh_type ;
                           prov:value ?height_thresh_value .
            ?inference prov:used ?stat_map ;
                       prov:used ?extent_thresh ;
                       prov:used ?height_thresh ;
                       prov:wasAssociatedWith ?soft_id .
            ?soft_id a ?software ;
                       softwareVersion: ?soft_version .
            ?excursion_set_id a ExcursionSetMap: ;
                       prov:wasGeneratedBy ?inference .

            FILTER(?software NOT IN (prov:SoftwareAgent, prov:Agent))
            FILTER(?subjects_type NOT IN (prov:SoftwareAgent, prov:Agent))
            FILTER(?height_thresh_type NOT IN (prov:Entity, HeightThreshold:))
            FILTER(?extent_thresh_type NOT IN (prov:Entity, ExtentThreshold:))

        }

        """
        sd = nidm_graph.query(query)

        owl_graph = Graph()
        owl_graph.parse(owl_file, format='turtle')

        print "\n\n"
        print os.path.basename(url)

        if sd:
            for row in sd:
                est_method, homoscedasticity, contrast_name, stat_type, \
                    search_vol_vox, search_vol_units, extent_value, \
                    height_value, extent_thresh_type, height_thresh_type, \
                    software, exc_set, soft_version, subjects_type, var_spatial,\
                    covar, covar_spatial, drift_model, fsl_drift_cutoff,\
                    spm_drift_cutoff = row

                # Convert all info to text
                thresh = ""
                multiple_compa = ""

                if extent_thresh_type in [OBO_Q_VALUE_FDR, OBO_P_VALUE_FWER]:
                    inference_type = "Cluster-wise"
                    thresh, multiple_compa = threshold_txt(
                        owl_graph, extent_thresh_type, extent_value, stat_type)
                    clus_thresh, unused = threshold_txt(
                        owl_graph, height_thresh_type, height_value, stat_type)
                    thresh += " with a cluster defining threshold " + clus_thresh

                else:
                    inference_type = "Voxel-wise"
                    thresh, multiple_compa = threshold_txt(
                        owl_graph, height_thresh_type, height_value, stat_type)
                    if int(extent_value) > 0:
                        thresh += " and clusters smaller than %d were discarded" \
                            % int(extent_value)

                if homoscedasticity:
                    variance = 'equal'
                else:
                    variance = 'unequal'

                if subjects_type in [STATO_GROUP]:
                    subjects = "group"
                elif subjects_type in [PROV['Person']]:
                    subjects = "subject"
                else:
                    raise Exception('Unknown subject type: ' + str(subjects_type))

                if var_spatial == NIDM_SPATIALLY_LOCAL_MODEL:
                    var_spatial = "local"
                elif var_spatial == NIDM_SPATIALLY_GLOBAL_MODEL:
                    var_spatial = "global"
                elif var_spatial == NIDM_SPATIALLY_REGULARIZED_MODEL:
                    var_spatial = "spatially regularized"
                else:
                    raise Exception(
                        'Unknown spatial variance estimation: ' + str(var_spatial))

                if covar == NIDM_INDEPENDENT_ERROR:
                    covar = ""
                else:
                    if covar_spatial == NIDM_SPATIALLY_LOCAL_MODEL:
                        covar_spatial = "local"
                    elif covar_spatial == NIDM_SPATIALLY_GLOBAL_MODEL:
                        covar_spatial = "global"
                    elif covar_spatial == NIDM_SPATIALLY_REGULARIZED_MODEL:
                        covar_spatial = "spatially regularized"
                    else:
                        raise Exception(
                            'Unknown spatial variance estimation: ' +
                            str(covar_spatial))
                    covar = " and a " + covar_spatial + " " + \
                        owl_graph.label(covar)

                if drift_model:
                    drift_model = "Drift was fit with a " + \
                        owl_graph.label(drift_model).lower()
                    if spm_drift_cutoff:
                        drift_model = drift_model + \
                            " (" + spm_drift_cutoff + "s cut-off)."
                    if fsl_drift_cutoff:
                        drift_model = drift_model + \
                            " (" + fsl_drift_cutoff + "s FWHM)."
                else:
                    drift_model = ""

                print "-------------------"
                print "%s-level analysis was performed with %s (version %s). \
A linear regression was computed at each voxel, using %s \
(assuming %s variances) with a %s variance estimate%s. %s\
\n%s inference was performed %susing a threshold %s. \
The search volume was %d cm^3 (%d voxels)." % (
                    subjects.capitalize(),
                    owl_graph.label(software), soft_version,
                    owl_graph.label(est_method).replace(" estimation", ""),
                    variance, var_spatial, covar, drift_model,
                    inference_type,
                    multiple_compa, thresh, float(search_vol_units)/1000,
                    int(search_vol_vox))
                print "-------------------"
                # Create report for first contrast found
                break

        else:
            print "Query returned no results."
