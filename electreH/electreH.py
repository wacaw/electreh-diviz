"""
ElectreH method for multiple-criteria decision aiding with hierarchical structure of criteria
Usage:
    ElectreH.py -i DIR -o DIR

Options:
    -i DIR     Specify input directory. It should contain the following files:
                   alternatives.xml
                   criteria.xml
                   concordance_levels.xml
                   hierarchy.xml
                   performances.xml
                   weights.xml
    -o DIR     Specify output directory. Files generated as output:
                   outranking.xml
                   credibility..xml
                   messages.xml
    --version  Show version.
    -h --help  Show this screen.
"""


# -*-coding:utf-8 -*
import argparse, sys, os, inspect, re, subprocess
import PyXMCDA as px
from contextlib import nested
from docopt import docopt
from Criterion import *
from common import comparisons_to_xmcda, create_messages_file, get_dirs, \
    get_error_message, get_input_data, get_linear, write_xmcda, Vividict

__version__ = '0.2.0'

def main(argv=None):
    try:
        args = docopt(__doc__, version=__version__)
        output_dir = None
        input_dir, output_dir = get_dirs(args)

        files = {}
        filenames = [
            'alternatives.xml',
            'criteria.xml',
            'concordance.xml',
            'hierarchy.xml',
            'performance_table.xml',
            'weights.xml',
        ]

        for f in filenames:
            file_name = os.path.join(input_dir, f)
            if not os.path.isfile(file_name):
                raise RuntimeError("Problem with the input file: '{}'."
                                        .format(f))
            tree_name = os.path.splitext(f)[0]
            if 'classes' in tree_name:
                tree_name = tree_name.replace('classes', 'categories')
            files.update({tree_name: file_name})

        exitStatus = 0
        (alternatives_ids, criteria_ids, performance_table, criteriaWeight, preferenceDirections, hierarchyArray, criteria_thresholds, concordanceCutLev) = \
        parse_xmcda_files(files['weights'], files['hierarchy'], files['concordance'], files['criteria'], files['alternatives'], files['performance_table'])
        electreH = ElectreH(alternatives_ids, criteria_ids, performance_table, criteriaWeight, preferenceDirections, hierarchyArray, criteria_thresholds, concordanceCutLev)
        electreH.make_outranking()
        electreH.writeOutranking(os.path.join(output_dir,'outranking.xml'))
        credibilityMx = electreH.make_credibility_matrix()
        electreH.writeCredibilityOutranking(os.path.join(output_dir,'credibility.xml'))
        create_messages_file(None, ('Everything OK.',), output_dir)

    except ValueError as e:
        exitStatus = -1
        create_messages_file((e.message), ('error.',), output_dir)
    return exitStatus



class ElectreH():
    def __init__(self, alternatives_ids, criteria_ids, performance_table, criteriaWeight, preferenceDirections, hierarchyArray, criteria_thresholds, concordanceCutLev):
        self.alternatives_ids = alternatives_ids
        self.criteria_ids = criteria_ids
        self.performance_table = performance_table
        self.criteriaWeight = criteriaWeight
        self.weightsSumUpToOne()
        self.preferenceDirections = preferenceDirections
        self.hierarchyArray = hierarchyArray
        self.criteria_thresholds = criteria_thresholds
        self.concordanceCutLev = concordanceCutLev
        self.criteria = self.hierarchyArray
        self.make_criteria_values()
        self.outrankingMatrix = {}
        self.credibilityMx = {}


    def weightsSumUpToOne(self):
        sum = 0.0
        for val in self.criteriaWeight.values():
            sum += val
        for crit in self.criteriaWeight:
            self.criteriaWeight[crit] /= sum

    def writeOutranking(self, filename):
        self.writeAlternativeComparision(filename, self.outrankingMatrix, 'outranks')

    def writeCredibilityOutranking(self, filename):
        self.writeAlternativeComparision(filename, self.credibilityMx, 'credibility')

    def writeAlternativeComparision(self, filename, comparisionMx, comparisionType=None):
        outfile = open(filename, 'w')
        px.writeHeader(outfile)
        for key, item in comparisionMx.items() :
            if self.criteria.has_key(key.name):
                outfile.write('\t<alternativesComparisons mcdaConcept="Pairwise comparison">\n')
                if comparisionType != None :
                    outfile.write("\t\t<comparisonType>%s</comparisonType>\n" % comparisionType)
                outfile.write("\t\t<criterionID>%s</criterionID>\n" % key.name)
                outfile.write('\t\t<pairs>\n')
                for key1, item1 in item.items():
                    for key2, item2 in item1.items():
                        outfile.write("""\t\t\t<pair>
                <initial>
                    <alternativeID>%s</alternativeID>
                </initial>
                <terminal>
                    <alternativeID>%s</alternativeID>
                </terminal>
                <value>
                    <real>%s</real>
                </value>
            </pair>\n""" % (key1, key2, item2))
                outfile.write('\t\t</pairs>\n')
                outfile.write('\t</alternativesComparisons>\n')
            else:
                pass
        px.writeFooter(outfile)
        outfile.close()

    def forPrintOutrankingMx(self):
        ret = ""
        sort = sorted(self.outrankingMatrix, key=lambda c:c.level, reverse=True)
        for criterion in sort:
            ret += "\\\\\\\\\n\n%s\n" % criterion.name
            for alt in self.alternatives_ids:
                ret += "&\t%s" % alt
            for alt in self.alternatives_ids:
                ret += "\\\\\n%s" % alt
                for alt2 in self.alternatives_ids:
                    ret += "&\t%s" % self.outrankingMatrix[criterion][alt][alt2]

        return ret

    def forPrintCredibilitygMx(self):
        ret = ""
        sort = sorted(self.credibilityMx, key=lambda c:c.level, reverse=True)
        for criterion in sort:
            ret += "\n\n%s\n" % criterion.name
            for alt in self.alternatives_ids:
                ret += "\t\t%s" % alt
            for alt in self.alternatives_ids:
                ret += "\n%s" % alt
                for alt2 in self.alternatives_ids:
                    ret += "\t%f" % self.credibilityMx[criterion][alt][alt2]

        return ret

    def make_criteria_values(self):
        for crit in self.criteria_thresholds :
            if self.criteria_ids.count(crit) > 0 :
                self.criteria[crit].setIndPrefVetoFromArray(self.criteria_thresholds[crit])
                self.criteria[crit].setAlphaBetaFromArray(self.criteria_thresholds[crit])

    def make_outranking(self):
        max = Criterion.get_number_of_levels_of_criteria(self.criteria)
        sort = sorted(self.criteria.values(), key=lambda c:c.level, reverse=True)
        values = {}
        for crit in sort:
            if crit.level < max :
                cutLevel = Criterion.get_cuttin_level_at_criterion(crit.name, self.criteria, self.concordanceCutLev, self.criteriaWeight)
                criteria = Criterion.getLeaves(crit.name, self.criteria)
                matrixAlt1 = {}
                for alt1 in self.alternatives_ids:
                    for alt2 in self.alternatives_ids:
                        cmpr = self.compare_two_alternatives(alt1, alt2, crit, criteria, cutLevel)
                        matrixAlt1.setdefault(alt1, {}).update({alt2:cmpr['S']})
                values[crit] = matrixAlt1
        self.outrankingMatrix = values

    def make_credibility_matrix(self):
        max = Criterion.get_number_of_levels_of_criteria(self.criteria)
        sort = sorted(self.criteria.values(), key=lambda c:c.level, reverse=True)
        values = {}
        for crit in sort:
            if crit.level < max :
                cutLevel = Criterion.get_cuttin_level_at_criterion(crit.name, self.criteria, self.concordanceCutLev, self.criteriaWeight)
                criteria = Criterion.getLeaves(crit.name, self.criteria)
                matrixAlt1 = {}
                for alt1 in self.alternatives_ids:
                    for alt2 in self.alternatives_ids:
                        cmpr = self.compare_two_alt_for_credibility(alt1, alt2, crit, criteria, cutLevel)
                        matrixAlt1.setdefault(alt1, {}).update({alt2:cmpr})
                values[crit] = matrixAlt1
        self.credibilityMx = values

    def list(self):
        ret = ""
        for alt1 in self.alternatives_ids:
            ret += "\t" + alt1
        return ret


    def compare_two_alternatives(self, alt1, alt2, atCriterion, criteria, cutLevel):
        if alt1 == alt2:
            return {'S':1, 'info':"Sama do siebie"}
        CutLevelAtCriterion = 0
        veto = True
        for crit in criteria:
            concordanceTemp = self.concordance(alt1, alt2, crit)
            if not concordanceTemp['veto'] :
                veto = False
            CutLevelAtCriterion += (concordanceTemp['conlev'] * self.criteriaWeight[crit])
        if CutLevelAtCriterion >= cutLevel and veto :
            return {'S':1, 'info':"CutLevelAtCriterion %s podzielone %s cutlevel %s" % (atCriterion , CutLevelAtCriterion , cutLevel)}
        elif CutLevelAtCriterion < cutLevel or not veto :
            return {'S':0, 'info':"CutLevelAtCriterion %s podzielone %s cutlevel %s" % (atCriterion , CutLevelAtCriterion , cutLevel)}

    def compare_two_alt_for_credibility(self, alt1, alt2, atCriterion, criteria, cutLevel):
        if alt1 == alt2 :
            return 1
        CutLevelAtCriterion = 0
        multyplyAr = []
        multyplyBy = 1
        sumOfWeights = 0
        for crit in criteria:
            concordanceTemp = self.concordance(alt1, alt2, crit)
            discordanceTemp = self.discordance(alt1, alt2, crit)
            multyplyAr.append(discordanceTemp['disconc'])
            CutLevelAtCriterion += (concordanceTemp['conlev'] * self.criteriaWeight[crit])
            sumOfWeights += self.criteriaWeight[crit]
        credibility = (CutLevelAtCriterion / sumOfWeights)
        for m in multyplyAr :
            if m > credibility:
                multyplyBy *= ((1 - m) / (1 - credibility))
        return (credibility * multyplyBy)



    def concordance(self, altA, altB, atCriterion):
        if altA == altB :
            return {'conlev':1, 'veto':True}
        valA = self.performance_table[altA][self.getOriginalName(atCriterion)]
        valB = self.performance_table[altB][self.getOriginalName(atCriterion)]
        ind, pref, veto = self.criteria[atCriterion].getAlphaBeta(valA, valB)

        if self.preferenceDirections[atCriterion] == 'max' or\
            self.preferenceDirections[atCriterion] == 1:
            boolVeto = True if (valB - valA) < veto else False
            if valA >= (valB - ind) :
                return {'conlev':1, 'veto':boolVeto}
            elif ((valB - pref) <= valA and valA < (valB - ind)) :
                return {'conlev':(valA - (valB - pref)) / (pref - ind) , 'veto':boolVeto}
            elif valA < (valB - pref) :
                return {'conlev':0, 'veto':boolVeto}
        else :
            boolVeto = True if (valA - valB) < veto else False
            if valA <= valB + ind :
                return {'conlev':1 , 'veto':boolVeto}
            elif valA > valB + pref :
                return {'conlev':0 , 'veto':boolVeto}
            elif (valB + pref >= valA and valA > valB + ind) :
                #TODO
                con = (valB - (valA - pref)) / (pref - ind)
                #if con < 0 or con > 1 :
                    #raise ValueError, "con=%s, valA= %s, valB=%s, pref=%s, ind=%s" % (con, valA, valB, pref, ind)
                    #print "con=%s, valA= %s, valB=%s, pref=%s, ind=%s" % (con, valA, valB, pref, ind)
                    #raise ValueError, "con=%s, valA= %s, valB=%s, pref=%s, ind=%s" % (con, valA, valB, pref, ind)
                return {'conlev':con , 'veto':boolVeto}


    def getOriginalName(self, criterionWithHash):
        """
        from Criterion Ex. Name#1 get Criterion Ex. Name
        """
        return criterionWithHash.split('#')[0]

    def discordance(self, altA, altB, atCriterion):
#        if altA == altB:
#            return {'disconc':0, 'veto':True}
        valA = self.performance_table[altA][self.getOriginalName(atCriterion)]
        valB = self.performance_table[altB][self.getOriginalName(atCriterion)]
        ind, pref, veto = self.criteria[atCriterion].getAlphaBeta(valA, valB)
#
#        print ind
#        print pref
#        print veto
#        print '-----'

        if self.preferenceDirections[atCriterion] == 'max' or \
            self.preferenceDirections[atCriterion] == 1:
            boolVeto = True if (valB - valA) < veto else False
            if valA <= (valB - veto) :
                return {'disconc':1, 'veto':boolVeto}
            elif valA >= (valB - pref) :
                return {'disconc':0, 'veto':boolVeto}
            elif ((valB - veto) < valA < (valB - pref)) :
                return {'disconc': abs((valA - (valB - pref)) / (veto - pref)) , 'veto':boolVeto}
        else :
            boolVeto = True if (valA - valB) < veto else False
            if valA >= (valB - veto) :
                return {'disconc':1, 'veto':boolVeto}
            elif valA <= (valB + pref) :
                return {'disconc':0, 'veto':boolVeto}
            else :
                #TODO
                return {'disconc':(valA - (valB + pref)) / (veto - pref) , 'veto':boolVeto}




def get_hierarchy(hierarchy, par='-', a={}, level=0):
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
            get_hierarchy(node, parent, a, level + 1)
    return a


def get_hierarchy_array(xmltree):
    hierarchy = xmltree.find(".//hierarchy")
    a = {}
    if hierarchy != None :
        a = get_hierarchy(hierarchy)
    else:
        raise ValueError, 'Invalid hierarchy file. No hierarchy?'
    return a


def get_criterion_concordance_cutting_level_value (xmltree, mcdaConcept=None) :

    if mcdaConcept == None :
        strSearch = "criteriaValues"
    else :
        strSearch = "criteriaValues[@mcdaConcept=\'" + mcdaConcept + "\']"
    try:
        criteriaValues = xmltree.xpath(strSearch)[0]
    except:
        criteriaValues = None
        #return {}

    if criteriaValues is None:
        return px.getParameterByName(xmltree, 'percentage', 'concordanceLevel')

    values = {}

    for criterionValue in criteriaValues.findall("./criterionValue"):
        crit = criterionValue.find ("criterionID").text
        values[crit] = px.getValue (criterionValue)

    return values

def xmcda_write_method_messages(xmlfile, type, messages) :
    if type not in ('log', 'error'):
        raise ValueError, 'Invalid type: %s' % type
    xmlfile.write('<methodMessages>\n')
    for message in messages :
       xmlfile.write('<%sMessage><text><![CDATA[%s]]></text></%sMessage>\n' % (type, message, type))
    xmlfile.write('</methodMessages>\n')

def parse_xmcda_files(in_weights, in_hierarchy, in_concorlevel, in_criteria, in_alternatives, in_performances):
    xml_crit = px.parseValidate(in_criteria)
    xml_alt = px.parseValidate(in_alternatives)
    xml_pt = px.parseValidate(in_performances)
    xml_weight = px.parseValidate(in_weights)
    xml_hierarchy = px.parseValidate(in_hierarchy)
    xml_concordance = px.parseValidate(in_concorlevel)
    if xml_crit == None:
        raise ValueError, "Invalid criteria file"
    if xml_alt == None:
        raise ValueError, "Invalid alternative file"
    if xml_pt == None:
        raise ValueError, "Invalid performance table file"
    if xml_weight == None:
        raise ValueError, "Invalid weight file"
    if xml_hierarchy == None:
        raise ValueError, "Invalid assignment file"
    if xml_concordance == None:
        raise ValueError, "Invalid concordance file"

    try:
        alternatives_ids = px.getAlternativesID(xml_alt)
        criteria_ids = px.getCriteriaID(xml_crit)
        performance_table = px.getPerformanceTable(xml_pt, alternatives_ids, criteria_ids)
        criteriaWeight = px.getCriterionValue(xml_weight, criteria_ids, 'Importance')
        preferenceDirections = px.getCriteriaPreferenceDirections(xml_crit, criteria_ids)
        hierarchyArray = get_hierarchy_array(xml_hierarchy)
        criteria_thresholds = px.getConstantThresholds(xml_crit, criteria_ids)
        concordanceCutLev = get_criterion_concordance_cutting_level_value(xml_concordance, 'Concordance')
    except:
        raise ValueError, "Failed to parse one or more file"
        return

    return alternatives_ids, criteria_ids, performance_table, criteriaWeight, preferenceDirections, hierarchyArray, criteria_thresholds, concordanceCutLev


if __name__ == "__main__":
    sys.exit(main())
