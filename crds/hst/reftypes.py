"""This modules consolidates different kinds of information related to each
instrument and reference type under one data structure. Most of the information
contained here was reverse engineered from CDBS in a piecemeal fashion,  then
consolidated into the single common data structure to support future maintenance
and the addition of new types.
"""

import sys
import os.path
import pprint

from crds import rmap, log, utils, data_file
from crds.certify import TpnInfo

# =============================================================================

HERE = (os.path.dirname(__file__) + "/") or "./"

# =============================================================================
#  Global table loads used at operational runtime:

def _evalfile_with_fail(filename):
    """Evaluate and return a dictionary file,  returning {} if the file
    cannot be found.
    """
    if os.path.exists(filename):
        result = utils.evalfile(filename)
    else:
        log.warning("Couldn't load CRDS config file", repr(filename))
        result = {}
    return result

def _invert_instr_dict(map):
    """Invert a set of nested dictionaries of the form {instr: {key: val}}
    to create a dict of the form {instr: {val: key}}.
    """
    inverted = {}
    for instr in map:
        inverted[instr] = utils.invert_dict(map[instr])
    return inverted

# =============================================================================

def consolidate():
    """One time generation function to consolidate piecemeal spec files."""
    from crds.hst import tpn, INSTRUMENTS, FILEKINDS
    rowkeys = _evalfile_with_fail("./row_keys.dat")
    tpn_cat = _evalfile_with_fail("./crds_tpn_catalog.dat")
    ld_tpn_cat = _evalfile_with_fail("./crds_ld_tpn_catalog.dat")
    parkeys = _evalfile_with_fail("./parkeys.dat")
    consolidated = {}
    for instr in tpn.FILEKIND_TO_SUFFIX:
        if instr not in consolidated:
            consolidated[instr] = {}
        for filekind in tpn.FILEKIND_TO_SUFFIX[instr]:
            if filekind in ["comptab", "graphtab"]:  # unsupported synphot types
                continue
            if instr == "wfc3" and filekind == "dgeofile":  # unimplemented type
                continue
            if instr =="cos" and filekind in ["proftab", "tracetab", "twozxtab"]:  # first types added manually
                continue
            if filekind not in consolidated[instr]:
                consolidated[instr][filekind] = {}
            suffix = assign_field(consolidated, instr, filekind, "suffix", lambda: tpn.FILEKIND_TO_SUFFIX[instr][filekind])
            assign_field(consolidated, instr, filekind, "filetype", lambda: tpn.SUFFIX_TO_FILETYPE[instr][suffix])
            if instr == "stis" and filekind in ["lfltfile", "pfltfile"]:
                assign_field(consolidated, instr, filekind, "tpn", lambda: tpn_cat[instr][filekind][0][1][0])
                assign_field(consolidated, instr, filekind, "reffile_format", lambda: tpn_cat[instr][filekind][0][1][2])
                assign_field(consolidated, instr, filekind, "file_ext", lambda: tpn_cat[instr][filekind][0][1][3])
            else:
                assign_field(consolidated, instr, filekind, "tpn", lambda: tpn_cat[instr][filekind][0])
                assign_field(consolidated, instr, filekind, "reffile_format", lambda: tpn_cat[instr][filekind][2])
                assign_field(consolidated, instr, filekind, "file_ext", lambda: tpn_cat[instr][filekind][3])
            assign_field(consolidated, instr, filekind, "ld_tpn", lambda: ld_tpn_cat[instr][filekind][0])
            if consolidated[instr][filekind]["reffile_format"] == "table":  # only tables have rowkeys
                assign_field(consolidated, instr, filekind, "unique_rowkeys", lambda: rowkeys[instr][filekind])
            else:
                assign_field(consolidated, instr, filekind, "unique_rowkeys", lambda: None)
            assign_field(consolidated, instr, filekind, "reffile_required", lambda: parkeys[instr][filekind]["reffile_required"])
            assign_field(consolidated, instr, filekind, "reffile_switch", lambda: parkeys[instr][filekind]["reffile_switch"])
            assign_field(consolidated, instr, filekind, "parkeys", lambda: tuple(parkey.upper() for parkey in parkeys[instr][filekind]["parkeys"]))
            assign_field(consolidated, instr, filekind, "rmap_relevance", lambda: parkeys[instr][filekind]["rmap_relevance"])
            assign_field(consolidated, instr, filekind, "parkey_relevance", lambda: parkeys[instr][filekind]["parkey_relevance"])
            assign_field(consolidated, instr, filekind, "extra_keys", lambda: parkeys[instr][filekind]["not_in_db"])
    assign_field(consolidated, "stis", "lfltfile", "tpn", lambda: [("OBSTYPE == 'IMAGING'", "stis_ilflt.tpn"),
                                                                   ("OBSTYPE == 'SPECTROSCOPIC", "stis_slflt.tpn")])
    assign_field(consolidated, "stis", "pfltfile", "tpn", lambda: [("OBSTYPE == 'IMAGING'", "stis_ipflt.tpn"),
                                                                   ("OBSTYPE == 'SPECTROSCOPIC", "stis_spflt.tpn")])
                
    open("./reftypes.dat", "wb").write(str(log.PP(consolidated)))


def assign_field(consolidated, instr, filekind, field, valuef):
    try:
        value = consolidated[instr][filekind][field] = valuef()
    except Exception, exc:
        log.warning("Skipping", instr, filekind, field, ":", exc)
        value = consolidated[instr][filekind][field] = None
    return value

# =============================================================================

UNIFIED_DEFS = _evalfile_with_fail(os.path.join(HERE, "reftypes.dat"))

# .e.g. FILEKIND_TO_SUFFIX = {                 
# 'acs': {'atodtab': 'a2d',
#         'biasfile': 'bia',
FILEKIND_TO_SUFFIX = { instr : { filekind : UNIFIED_DEFS[instr][filekind]["suffix" ] 
                                 for filekind in UNIFIED_DEFS[instr] 
                                } 
                      for instr in UNIFIED_DEFS }
SUFFIX_TO_FILEKIND = _invert_instr_dict(FILEKIND_TO_SUFFIX)

#.e.g. FILETYPE_TO_SUFFIX = {
# 'acs': {'analog-to-digital': 'a2d',
#         'bad pixels': 'bpx',
FILETYPE_TO_SUFFIX = { instr : { UNIFIED_DEFS[instr][filekind]["filetype"] : UNIFIED_DEFS[instr][filekind]["suffix" ] 
                                 for filekind in UNIFIED_DEFS[instr] 
                                } 
                      for instr in UNIFIED_DEFS }
SUFFIX_TO_FILEKIND = _invert_instr_dict(FILEKIND_TO_SUFFIX)

# =============================================================================

def filetype_to_filekind(instrument, filetype):
    """Map the value of a FILETYPE keyword onto it's associated
    keyword name,  i.e.  'dark image' --> 'darkfile'
    """
    instrument = instrument.lower()
    filetype = filetype.lower()
    if instrument == "nic":
        instrument = "nicmos"
    ext = FILETYPE_TO_SUFFIX[instrument][filetype]
    return SUFFIX_TO_FILEKIND[instrument][ext]

def extension_to_filekind(instrument, extension):
    """Map the value of an instrument and TPN extension onto it's
    associated filekind keyword name,  i.e. drk --> darkfile
    """
    if instrument == "nic":
        instrument = "nicmos"
    return SUFFIX_TO_FILEKIND[instrument][extension]

# =============================================================================

def mapping_validator_key(mapping):
    """Return (_ld.tpn name, ) corresponding to CRDS ReferenceMapping `mapping` object."""
    return (UNIFIED_DEFS[mapping.instrument][mapping.filekind]["ld_tpn"],)

def reference_name_to_validator_key(filename):
    """Given a reference filename `fitsname`,  return a dictionary key
    suitable for caching the reference type's Validator.
    
    This revised version supports computing "subtype" .tpn files based
    on the parameters of the reference.   Most references have unconditional
    associations based on (instrument, filekind).   A select few have
    conditional lookups which select between several .tpn's for the same
    instrument and filetype.
    
    Returns (.tpn filename,)
    """
    header = data_file.get_header(filename)
    instrument = header["INSTRUME"].lower()
    filetype = header["FILETYPE"].lower()
    filekind = filetype_to_filekind(instrument, filetype)
    tpnfile = UNIFIED_DEFS[instrument][filekind]["tpn"]
    if isinstance(tpnfile, basestring):
        key = (tpnfile,)  # tpn filename
    else: # it's a list of conditional tpns
        for (condition, tpn) in tpnfile:
            if eval(condition, header):
                key = (tpn,)  # tpn filename
                break
        else:
            raise ValueError("No TPN match for reference='{}' instrument='{}' reftype='{}'" % \
                                 (os.path.basename(filename), instrument, filekind))
    log.verbose("Validator key for", repr(filename), instrument, filekind, "=", key)
    return key

reference_name_to_tpn_key = reference_name_to_validator_key

def reference_name_to_ld_tpn_key(filename):
    """Return the _ld.tpn file key associated with reference `filename`.
    Strictly speaking this should be driven by mapping_validator_key...  but the interface
    for that is wrong so slave it to reference_name_to_tpn_key instead,  historically
    one-for-one.
    """
    return (reference_name_to_tpn_key(filename)[0].replace(".tpn", "_ld.tpn"),)
