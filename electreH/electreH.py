# -*-coding:utf-8 -*
import argparse, sys, os, inspect, re, subprocess
from contextlib import nested

#add path to local PyXMCDA and Criteria class
sys.path.append('/Users/wachu/mgr/src')
from Criterion import *       
import PyXMCDA


VERSION = "1.0"
'''DIVIZ PROGRAM
# 6 infiles
# 3 outfiles (1 message)
# script as file
#python script -a infile1 -c infile2 -l infile3 -t infile4 -w infile5 -p infile6 -r outfile1 -o outfile2 -m outfile3

###
'''
def main(argv=None):
    for_diviz = (inspect.stack()[0][1] != '/Users/wachu/mgr/src/electreH/electreH.py')
    #for_diviz = False
    
    if argv is None:
        argv = sys.argv
    
    parser = argparse.ArgumentParser(description=__doc__)

    grp_input = parser.add_argument_group("Inputs")
    grp_input.add_argument('-w', '--weights')
    grp_input.add_argument('-t', '--treeHierarchy')
    grp_input.add_argument('-l', '--concordanceLevel')
    grp_input.add_argument('-c', '--criteria')
    grp_input.add_argument('-a', '--alternatives')
    grp_input.add_argument('-p', '--performances')

    grp_output = parser.add_argument_group("Outputs")
    grp_output.add_argument('-r', '--outranking', metavar='output.xml')
    grp_output.add_argument('-o', '--credibility', metavar='output.xml')
    grp_output.add_argument('-m', '--messages', metavar='<file.xml>', help='All messages are redirected to this XMCDA file instead of being sent to stdout or stderr.  Note that if an output directory is specified (option -O), the path is relative to this directory.')

    args = parser.parse_args()

    if not for_diviz:
        in_dir = "/Users/wachu/mgr/src/electreH/test/mieszkaniePoznan/"
        #in_dir = "/Users/wachu/mgr/src/electreH/test/in1/"
        
        in_weights = in_dir + "weights.xml"
        in_hierarchy = in_dir + "hierarchyCOmplicated.xml"
        in_concorlevel = in_dir + "concordanceLevels.xml"
        in_criteria = in_dir + "criteriaAlphaBeta.xml"
        in_alternatives = in_dir + "alternatives.xml"
        in_performances = in_dir + "performances.xml"
        
        #in_hierarchy = in_dir + "hierarchy.xml"
        #in_criteria = in_dir + "criteria.xml"
                
        out_dir = "/Users/wachu/mgr/src/electreH/test/out1/"
        out_outranking = out_dir + "outranking.xml"
        out_messages = out_dir + "message.xml"
        out_credibility = out_dir + "credibility.xml"

    else :
        in_weights = args.weights
        in_hierarchy = args.treeHierarchy
        in_concorlevel = args.concordanceLevel
        in_criteria = args.criteria
        in_alternatives = args.alternatives
        in_performances = args.performances
    
        out_outranking = args.outranking
        out_credibility = args.credibility
        out_messages = args.messages
    
    if out_messages:
        messages_fd = open(out_messages, 'w')
        PyXMCDA.writeHeader(messages_fd)
    
    exitStatus = 0
    
    try:
        (alternativesIDs, criteriaIDs, performanceTable, criteriaWeight, preferenceDirections, hierarchyArray, criteriaThresholds, concordanceCutLev) = \
        parse_xmcda_files(in_weights, in_hierarchy, in_concorlevel, in_criteria, in_alternatives, in_performances)
        electreH = ElectreH(alternativesIDs, criteriaIDs, performanceTable, criteriaWeight, preferenceDirections, hierarchyArray, criteriaThresholds, concordanceCutLev)
        electreH.makeOutranking()
        electreH.writeOutranking(out_outranking)
        credibilityMx = electreH.makeCredibilityMatrix()
        electreH.writeCredibilityOutranking(out_credibility)
        
        if not for_diviz:
            print electreH.forPrintOutrankingMx()
    except ValueError as e:
        exitStatus = -1
        if out_messages:
            xmcda_write_method_messages(messages_fd, 'error', [e.message])
        else:
            sys.stderr.write(e.message)
    else:
       if out_messages: xmcda_write_method_messages(messages_fd, 'log', ['Execution ok'])
    finally:
        if out_messages:
            PyXMCDA.writeFooter(messages_fd)
            messages_fd.close()


#   
    return exitStatus        
    

    
class ElectreH():
    def __init__(self, alternativesIDs, criteriaIDs, performanceTable, criteriaWeight, preferenceDirections, hierarchyArray, criteriaThresholds, concordanceCutLev):
        self.alternativesIDs = alternativesIDs
        self.criteriaIDs = criteriaIDs
        self.performanceTable = performanceTable
        self.criteriaWeight = criteriaWeight
        self.weightsSumUpToOne()
        self.preferenceDirections = preferenceDirections
        self.hierarchyArray = hierarchyArray
        self.criteriaThresholds = criteriaThresholds
        self.concordanceCutLev = concordanceCutLev
        self.criteria = self.hierarchyArray
        self.makeCriteriaValues()
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
        PyXMCDA.writeHeader(outfile)
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
        PyXMCDA.writeFooter(outfile)
        outfile.close()
        
    def forPrintOutrankingMx(self):
        ret = ""
        sort = sorted(self.outrankingMatrix, key=lambda c:c.level, reverse=True)
        for criterion in sort:
            ret += "\\\\\\\\\n\n%s\n" % criterion.name
            for alt in self.alternativesIDs:
                ret += "&\t%s" % alt
            for alt in self.alternativesIDs:
                ret += "\\\\\n%s" % alt
                for alt2 in self.alternativesIDs:   
                    ret += "&\t%s" % self.outrankingMatrix[criterion][alt][alt2]
                    
        return ret
        
    def forPrintCredibilitygMx(self):
        ret = ""
        sort = sorted(self.credibilityMx, key=lambda c:c.level, reverse=True)
        for criterion in sort:
            ret += "\n\n%s\n" % criterion.name
            for alt in self.alternativesIDs:
                ret += "\t\t%s" % alt
            for alt in self.alternativesIDs:
                ret += "\n%s" % alt
                for alt2 in self.alternativesIDs:   
                    ret += "\t%f" % self.credibilityMx[criterion][alt][alt2]
                    
        return ret                    
    
    def makeCriteriaValues(self):
        for crit in self.criteriaThresholds :
            if self.criteriaIDs.count(crit) > 0 :
                self.criteria[crit].setIndPrefVetoFromArray(self.criteriaThresholds[crit])
                self.criteria[crit].setAlphaBetaFromArray(self.criteriaThresholds[crit])
                        
    def makeOutranking(self):    
        max = Criterion.getNumberOfLevelsOfCriteria(self.criteria)
        sort = sorted(self.criteria.values(), key=lambda c:c.level, reverse=True)
        values = {}
        for crit in sort:
            if crit.level < max :
                cutLevel = Criterion.getCuttinLevelAtCriterion(crit.name, self.criteria, self.concordanceCutLev, self.criteriaWeight)
                criteria = Criterion.getLeaves(crit.name, self.criteria)
                matrixAlt1 = {}
                for alt1 in self.alternativesIDs:
                    for alt2 in self.alternativesIDs:
                        cmpr = self.compareTwoAlternatives(alt1, alt2, crit, criteria, cutLevel)
                        matrixAlt1.setdefault(alt1, {}).update({alt2:cmpr['S']})
                values[crit] = matrixAlt1
        self.outrankingMatrix = values
    
    def makeCredibilityMatrix(self):
        max = Criterion.getNumberOfLevelsOfCriteria(self.criteria)
        sort = sorted(self.criteria.values(), key=lambda c:c.level, reverse=True)
        values = {}
        for crit in sort:
            if crit.level < max :
                cutLevel = Criterion.getCuttinLevelAtCriterion(crit.name, self.criteria, self.concordanceCutLev, self.criteriaWeight)
                criteria = Criterion.getLeaves(crit.name, self.criteria)
                matrixAlt1 = {}
                for alt1 in self.alternativesIDs:
                    for alt2 in self.alternativesIDs:
                        cmpr = self.compareTwoAltForCredibility(alt1, alt2, crit, criteria, cutLevel)
                        matrixAlt1.setdefault(alt1, {}).update({alt2:cmpr})
                values[crit] = matrixAlt1
        self.credibilityMx = values            
    
    def list(self):
        ret = "" 
        for alt1 in self.alternativesIDs:
            ret += "\t" + alt1
        return ret

    
    def compareTwoAlternatives(self, alt1, alt2, atCriterion, criteria, cutLevel):
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
    
    def compareTwoAltForCredibility(self, alt1, alt2, atCriterion, criteria, cutLevel):
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
        valA = self.performanceTable[altA][self.getOriginalName(atCriterion)]
        valB = self.performanceTable[altB][self.getOriginalName(atCriterion)]
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
                #TODO upewić się że to jest porawny wzór przy min!!
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
        valA = self.performanceTable[altA][self.getOriginalName(atCriterion)]
        valB = self.performanceTable[altB][self.getOriginalName(atCriterion)]
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
                #TODO upewić się że to jest porawny wzór przy min!!
                return {'disconc':(valA - (valB + pref)) / (veto - pref) , 'veto':boolVeto}
    
    

    
def getHierarchy(hierarchy, par='-', a={}, level=0):
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
            getHierarchy(node, parent, a, level + 1)
    return a
    

def getHierarchyArray(xmltree):
    hierarchy = xmltree.find(".//hierarchy")
    a = {}
    if hierarchy != None :
        a = getHierarchy(hierarchy)
    else:
        raise ValueError, 'Invalid hierarchy file. No hierarchy?'
    return a

    
def getCriterionConcordanceCuttingLevelValue (xmltree, mcdaConcept=None) :

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
        return PyXMCDA.getParameterByName(xmltree, 'percentage', 'concordanceLevel')
        
    values = {}
    
    for criterionValue in criteriaValues.findall("./criterionValue"):
        crit = criterionValue.find ("criterionID").text
        values[crit] = PyXMCDA.getValue (criterionValue)

    return values

def xmcda_write_method_messages(xmlfile, type, messages) :
    if type not in ('log', 'error'):
        raise ValueError, 'Invalid type: %s' % type
    xmlfile.write('<methodMessages>\n')
    for message in messages :
       xmlfile.write('<%sMessage><text><![CDATA[%s]]></text></%sMessage>\n' % (type, message, type))
    xmlfile.write('</methodMessages>\n')
    
def parse_xmcda_files(in_weights, in_hierarchy, in_concorlevel, in_criteria, in_alternatives, in_performances):
    xml_crit = PyXMCDA.parseValidate(in_criteria)
    xml_alt = PyXMCDA.parseValidate(in_alternatives)
    xml_pt = PyXMCDA.parseValidate(in_performances)
    xml_weight = PyXMCDA.parseValidate(in_weights)
    xml_hierarchy = PyXMCDA.parseValidate(in_hierarchy)
    xml_concordance = PyXMCDA.parseValidate(in_concorlevel)
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
        alternativesIDs = PyXMCDA.getAlternativesID(xml_alt)
        criteriaIDs = PyXMCDA.getCriteriaID(xml_crit)
        performanceTable = PyXMCDA.getPerformanceTable(xml_pt, alternativesIDs, criteriaIDs)
        criteriaWeight = PyXMCDA.getCriterionValue(xml_weight, criteriaIDs, 'Importance')
        preferenceDirections = PyXMCDA.getCriteriaPreferenceDirections(xml_crit, criteriaIDs)
        hierarchyArray = getHierarchyArray(xml_hierarchy)
        criteriaThresholds = PyXMCDA.getConstantThresholds(xml_crit, criteriaIDs)
        concordanceCutLev = getCriterionConcordanceCuttingLevelValue(xml_concordance, 'Concordance')
    except: 
        raise ValueError, "Failed to parse one or more file"
        return

    return alternativesIDs, criteriaIDs, performanceTable, criteriaWeight, preferenceDirections, hierarchyArray, criteriaThresholds, concordanceCutLev


if __name__ == "__main__":
    sys.exit(main())
