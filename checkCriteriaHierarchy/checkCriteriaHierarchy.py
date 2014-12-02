import argparse, csv, sys, os, inspect, re
from contextlib import nested
from lxml import etree

#add path to PyXMCDA
sys.path.append('/Users/wachu/mgr/src')
from Criterion import *
import PyXMCDA
from optparse import OptionParser

"""
#python script -c infile1 -t infile2 -l infile3 -w infile4 -W outfile1 -T outfile2 -C outfile3 -L outfile4 -m outfile5
# 4 inputes
# 5 outputs
"""
# not using PyXMCDA, to avoid the unnecessary dependency to lxml
def xmcda_write_header(xmlfile)     :
    xmlfile.write("<?xml version='1.0' encoding='UTF-8'?>\n")
    xmlfile.write("<xmcda:XMCDA xmlns:xmcda='http://www.decision-deck.org/2009/XMCDA-2.1.0' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' xsi:schemaLocation='http://www.decision-deck.org/2009/XMCDA-2.1.0 http://www.decision-deck.org/xmcda/_downloads/XMCDA-2.1.0.xsd'>\n")


def xmcda_write_footer(xmlfile) :
    xmlfile.write("</xmcda:XMCDA>\n")


def xmcda_write_method_messages(xmlfile, type, messages) :
    if type not in ('log', 'error'):
        raise ValueError, 'Invalid type: %s' % type
    xmlfile.write('<methodMessages>\n')
    for message in messages :
        xmlfile.write('<%sMessage><text><![CDATA[%s]]></text></%sMessage>\n' % (type, message, type))
    xmlfile.write('</methodMessages>\n')

def write_xmcda_content(filename, content=None):
    outfile = open(filename, 'w')
    PyXMCDA.writeHeader (outfile)
    if content != None:
            outfile.write(content)
    PyXMCDA.writeFooter(outfile)
    outfile.close()



def get_hierarchy(hierarchy, par='-', a={}, b={}, level=0):
    if hierarchy != None :
        rootNodes = hierarchy.findall("node")
        for node in rootNodes :
            parent = node.find("criterionID").text
            if not a.has_key(parent):
                a[parent] = Criterion(parent)
                a[parent].setParent(par)
                a[parent].level = level
            else:
                a[parent].setParent(par)
            get_hierarchy(node, parent, a, b, level + 1)
    return a


def get_hierarchy_array(xmltree):
    hierarchy = xmltree.find(".//hierarchy")
    a = {}
    if hierarchy != None :
        a = get_hierarchy(hierarchy)
    else:
        raise ValueError, 'Invalid hierarchy file. No hierarchy?'
    return a

def get_level(levelArray, sth):
    if levelArray.has_key(getOriginalName(sth)):
        return str(levelArray[getOriginalName(sth)])
    else:
        return "0"

def printArray(hierarchyArray, levelArray):
    ret = ""
    for sth in hierarchyArray:
        ret += "\n" + sth + " : " + str(hierarchyArray[sth]) + " len:" + str(len(hierarchyArray[sth])) + " level:" + get_level(levelArray, sth)
    return ret


def checkLevel(item, array, level=0):
    for sth in array:
        if sth == item:
            return level

def getNewCriterionName(name, ordinalNumer):
    return "%s#%s" % (name, ordinalNumer)

def getOriginalName(criterionWithHash):
    """
    from Criterion Ex. Name#1 get Criterion Ex. Name
    """
    return criterionWithHash.split('#')[0]

def divideCriteria(item, array):
    a = {}
    for sth, crit in array.items():
        if sth == item:
            i = 0
            for parent in crit.parent :
                i += 1
                new_name = getNewCriterionName(item, parent)
                a[new_name] = Criterion(new_name)
                a[new_name].setParent(parent)
        else :
            a[sth] = array[sth]
    return a

def copyNested(item, array, times):
    a = {}

    for sth, crit in array.items():
        if crit.name == item.name :
            for i in xrange(times):
                new_name = getNewCriterionName(crit.name, crit.parent[i])
                a[new_name] = Criterion(new_name)
                a[new_name].setParent(crit.parent[i])
        else:
            a[sth] = array[sth]
    return a


def checkNewParetsName(item, array):
    a = {}
    for sth, crit in array.items():
        if crit.name == item.name :
            for i in xrange(times):
                new_name = getNewCriterionName(crit.name, crit.parent[i])
                a[new_name] = Criterion(new_name)
                a[new_name].setParent(crit.parent[i])
        else:
            a[sth] = array[sth]
    return a

def buildNewHierarchy(a, root, hierarchyArray, newParentName=None):
    if newParentName == None :
        newParentName = root
    for criterion in hierarchyArray.values():
        if criterion.hasParent(root):
           if criterion.parentsNumber() > 1:
               for i in xrange(criterion.parentsNumber()):
                   newName = getNewCriterionName(criterion.name, newParentName)
                   a[newName] = Criterion(newName)
                   a[newName].level = hierarchyArray[criterion.name].level
                   a[newName].setParent(newParentName)
                   buildNewHierarchy(a, criterion.name, hierarchyArray, newName)
           else :
               a[criterion.name] = hierarchyArray[criterion.name]
               buildNewHierarchy(a, criterion.name, hierarchyArray)
    return a


def xml_node_label(a, b='', space=''):
    return '''\n\t%s<node>
\t\t%s<criterionID>%s</criterionID>%s%s
\t%s</node>''' % (space, space, a, space, b, space)

def make_tree(root, parents, level=0, maxlevel=100):
    ret = ''
    space = '\t\t'
    if level > maxlevel:
        return ''
    for key, crit in parents.items():
        if crit.getParent() == root:
            #print crit.getParent()
            ret += xml_node_label(crit.name, make_tree(crit.name, parents, level + 1, maxlevel), level * space)
    return ret

def get_hierarchyTree(xmltree):
    hierarchyArray = get_hierarchy_array(xmltree)
    hierarchyArray = buildNewHierarchy({}, '-', hierarchyArray)
    ret = make_tree('-', hierarchyArray)
    hierarchy = '''  <hierarchy>
    <description>
      <comment>A hierarchy of criteria</comment>
    </description>''' + ret + '''
    </hierarchy>'''
    return hierarchy, hierarchyArray

def check_hierarchy(xmltree, outfile):
    ret, hierarchyArray = get_hierarchyTree(xmltree)
    write_xmcda_content(outfile, ret)
    return hierarchyArray

def printArr(arr):
    ret = str(len(arr))
    for sth in arr:
        ret += "\n" + sth + " : " + str(arr[sth])
    return ret

def calculate_new_weights(weights, hierarchyArray):
    values = {}
    occur = {}
    for criterion in hierarchyArray.values():
        originalName = getOriginalName(criterion.name)
        if weights.has_key(originalName):
            if occur.has_key(originalName):
                occur[originalName] += 1
            else:
                occur[originalName] = 1
    for criterion in hierarchyArray.values():
        originalName = getOriginalName(criterion.name)
        if weights.has_key(originalName):
            values[criterion.name] = weights[originalName] / occur[originalName]
    return values


def calculate_new_concordance(concordances, hierarchyArray):
    values = {}
    occur = {}
    for criterion in hierarchyArray.values():
        originalName = getOriginalName(criterion.name)
        if concordances.has_key(originalName):
            if occur.has_key(originalName):
                occur[originalName] += 1
            else:
                occur[originalName] = 1
    for criterion in hierarchyArray.values():
        originalName = getOriginalName(criterion.name)
        if concordances.has_key(originalName):
            values[criterion.name] = concordances[originalName] / occur[originalName]
    return values

xml_value_real = '''
      <value>
        <real>%s</real>
      </value>'''[1:]
xml_value_label = '''
      <value>
        <label>%s</label>
      </value>'''[1:]

def output_criteriaValues(filename, weights, mcdaConcept):
    outfile = open(filename, 'w')
    PyXMCDA.writeHeader(outfile)
    outfile.write('  <criteriaValues mcdaConcept="%s">' % mcdaConcept)

    try:
        xmlWeights = [ xml_value_real % k for v, k in weights.items() ]
    except ValueError:
        xmlWeights = [ xml_value_label % k for v, k in weights.items() ]

    for id, weight in map(None, weights, xmlWeights):
        outfile.write("""
    <criterionValue>
      <criterionID>%s</criterionID>
%s
    </criterionValue>
""" % (id, weight))
    outfile.write('  </criteriaValues>\n')
    PyXMCDA.writeFooter(outfile)
    outfile.close()



def check_weights(xml_weights, hierarchyArray, outfile):
    ret = ""
    weights = PyXMCDA.getCriterionValue(xml_weights, [(getOriginalName(v)) for v, k in hierarchyArray.items()], 'Importance')
    weights = calculate_new_weights(weights, hierarchyArray)
    output_criteriaValues(outfile, weights, 'Importance')


def check_concordance(xml_concordance, hierarchyArray, outfile):
    ret = ""
    concordances = PyXMCDA.getCriterionValue(xml_concordance, [(getOriginalName(v)) for v, k in hierarchyArray.items()], 'Concordance')
    if concordances.__len__() > 0 :
        concordances = calculate_new_concordance(concordances, hierarchyArray)
        output_criteriaValues(outfile, concordances, 'Concordance')
    else :
        check = PyXMCDA.getParameterByName(xml_concordance, 'percentage', 'concordanceLevel')
        if check != None :
            content = """
    <methodParameters name="concordanceLevel">
        <parameter name="percentage">
            <value><real>%f</real></value>
        </parameter>
    </methodParameters>""" % check
            write_xmcda_content(outfile, content)

def copyfile(source, dest, buffer_size=1024 * 1024):
    """
    Copy a file from source to dest. source and dest
    can either be strings or any object with a read or
    write method, like StringIO for example.
    """
    if not hasattr(source, 'read'):
        source = open(source, 'rb')
    if not hasattr(dest, 'write'):
        dest = open(dest, 'wb')

    while 1:
        copy_buffer = source.read(buffer_size)
        if copy_buffer:
            dest.write(copy_buffer)
        else:
            break

    source.close()
    dest.close()

def trivialCopy(xmltree, critId) :
    oryginalValues = {}
    for crit in critId :
        xml_cri = xmltree.find(".//criterion[@id='" + crit + "']")
        ret= etree.tostring(xml_cri).split('\n',1)[1].rsplit('\n',2)[0]
        oryginalValues[crit] = ret

    return oryginalValues


def output_criteria(filename, criteria_ids, xml_crit):
    oldCriteriaIDs = PyXMCDA.getCriteriaID(xml_crit)
    trivial = trivialCopy(xml_crit, oldCriteriaIDs)
    #critScale = PyXMCDA.getCriteriaScalesTypes(xml_crit, oldCriteriaIDs)
    #critThresholds = PyXMCDA.getConstantThresholds(xml_crit, oldCriteriaIDs)
    #critPreference = PyXMCDA.getCriteriaPreferenceDirections(xml_crit, oldCriteriaIDs)

    outfile = open(filename, 'w')
    PyXMCDA.writeHeader(outfile)
    outfile.write('  <criteria>\n')
    for id in sorted(criteria_ids):
        oldID = getOriginalName(id)
        if not oldID in oldCriteriaIDs:
            pass
            #outfile.write('''
        #<criterion id="%s" name="%s"/>
        #''' % (id,id))
        else:
            #print trivial
            #print oldID
            outfile.write('''
        <criterion id="%s" name="%s">\n%s
        </criterion>''' % (id,id,trivial[oldID]))
    outfile.write('  </criteria>\n')
    PyXMCDA.writeFooter(outfile)
    outfile.close()

def check_criteria_hierarchy(in_weights, in_hierarchy, in_concorlevel, in_criteria, out_criteria, out_weights, out_hierarchy, out_concorlevel):
    weights_xmltree = PyXMCDA.parseValidate(in_weights)
    hierarchy_xmtree = PyXMCDA.parseValidate(in_hierarchy)
    concordance_xmltree = PyXMCDA.parseValidate(in_concorlevel)
    criteria_xmltree = PyXMCDA.parseValidate(in_criteria)

    if weights_xmltree == None:
        raise ValueError, 'Invalid weights file'
    if hierarchy_xmtree == None:
        raise ValueError, 'Invalid hierarchy file'
    if concordance_xmltree == None:
        raise ValueError, 'Invalid concordance level file'
    if criteria_xmltree == None:
        raise ValueError, 'Invalid criterioa file'

    hierarchyArray = check_hierarchy(hierarchy_xmtree, out_hierarchy)
    check_weights(weights_xmltree, hierarchyArray, out_weights)
    check_concordance(concordance_xmltree, hierarchyArray, out_concorlevel)
    output_criteria(out_criteria, [(v) for v, k in hierarchyArray.items()], criteria_xmltree)
    return None


def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = argparse.ArgumentParser(description=__doc__)

    grp_input = parser.add_argument_group("Inputs")
    grp_input.add_argument('-w', '--weights')
    grp_input.add_argument('-t', '--treeHierarchy')
    grp_input.add_argument('-l', '--concordanceLevel')
    grp_input.add_argument('-c', '--criteriaThresholds')

    grp_output = parser.add_argument_group("Outputs")
    grp_output.add_argument('-W', '--newWeights', metavar='output.xml')
    grp_output.add_argument('-T', '--newHiererchy', metavar='output.xml')
    grp_output.add_argument('-C', '--newCriteria', metavar='output.xml')
    grp_output.add_argument('-L', '--newconcordanceLevel', metavar='output.xml')


    grp_output.add_argument('-m', '--messages', metavar='<file.xml>', help='All messages are redirected to this XMCDA file instead of being sent to stdout or stderr.  Note that if an output directory is specified (option -O), the path is relative to this directory.')

    args = parser.parse_args()

    if False:
        in_dir ="/Users/wachu/mgr/src/electreH/test/mieszkaniePoznan/"
        in_weights = in_dir + "weights.xml" # in_dir + "weights.xml"
        in_hierarchy = in_dir + "hierarchyComplicated.xml" #in_dir + "hierarchy.xml"
        in_concorlevel = in_dir + "concordanceLevels.xml"
        in_criteria = in_dir + "criteria.xml"

        out_dir = "/Users/wachu/mgr/src/electreH/test/out1/"
        out_criteria = out_dir + "crt.xml"
        out_weights = out_dir + "wei.xml"
        out_hierarchy = out_dir + "hier.xml"
        out_concorlevel = out_dir + "conc.xml"

    else :
        in_weights = args.weights
        in_hierarchy = args.treeHierarchy
        in_concorlevel = args.concordanceLevel
        in_criteria = args.criteriaThresholds

        out_criteria = args.newCriteria
        out_weights = args.newWeights
        out_hierarchy = args.newHiererchy
        out_concorlevel = args.newconcordanceLevel

    if args.messages is not None:
        messages = args.messages
    else:
        messages = '/Users/wachu/mgr/src/electreH/test/out1/messages.xml'

    if messages:
        messages_fd = open(messages, 'w')
        xmcda_write_header(messages_fd)

    exitStatus = 0


    try:
        check_criteria_hierarchy(in_weights, in_hierarchy, in_concorlevel, in_criteria, out_criteria, out_weights, out_hierarchy, out_concorlevel)
    except (ValueError, KeyError) as e:
        exitStatus = -1
        if messages:
            xmcda_write_method_messages(messages_fd, 'error', [e.message])
        else:
            sys.stderr.write(e.message)
    else:
       if messages: xmcda_write_method_messages(messages_fd, 'log', ['Execution ok'])
    finally:
        if messages:
            xmcda_write_footer(messages_fd)
            messages_fd.close()

    return exitStatus

if __name__ == "__main__":
    sys.exit(main())
