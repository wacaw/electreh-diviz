# -*-coding:utf-8 -*
import os, sys, argparse, inspect

#PyXMCDA
sys.path.append('/Users/wachu/mgr/src')
import PyXMCDA


"""###############
# DIVIZ
#
# python script -o infile1 -s infile2 -r outfile1 -m outfile2
# 2 infiles
# 2 outfiles (1- message)
#
################
"""
compatibleWith2_0_0 = True
    

def write_xmcda_content(filename, content=None):
    outfile = open(filename, 'w')
    PyXMCDA.writeHeader (outfile)
    if content != None:
            outfile.write(content)
    PyXMCDA.writeFooter(outfile)
    outfile.close()
    
def makeSelection(in_selected, in_outranking, out_outranking):
    xml_outranking = PyXMCDA.parseValidate(in_outranking)
    xml_selected = PyXMCDA.parseValidate(in_selected)
    if xml_selected == None:
        raise ValueError, "Invalid selected file"
    if xml_outranking == None:
        raise ValueError, "Invalid xml_outranking file"
    
    onCriterion = PyXMCDA.getParameterByName(xml_selected, 'selectedCriterion')
    alternativesComparisions = getAlternativesComparisonsAtCriteria(xml_outranking)
    
    if not alternativesComparisions.has_key(onCriterion):
        raise ValueError, 'Invalid selected criterion'
    writeAlternativeComparisionOnCriterion(out_outranking, alternativesComparisions, onCriterion, 'outranks')
    
def writeAlternativeComparisionOnCriterion(filename, comparisionMx, criterion, comparisionType=None):
    compatibleWith2_0_0 = True
    outfile = open(filename, 'w')
    if compatibleWith2_0_0 :
        PyXMCDA.writeHeader(outfile, '2.0.0')
        writeCriterion = None
    else:
        PyXMCDA.writeHeader(outfile)
        writeCriterion = criterion #definicja jakiego kryterium dotyczny dane porównanie dopiero w standardzie 2_2_1
    #for key, item in comparisionMx.items() :
    outfile.write('\t<alternativesComparisons mcdaConcept="Pairwise comparison">\n')
    if comparisionType != None :
        outfile.write("\t\t<comparisonType>%s</comparisonType>\n" % comparisionType)
    if writeCriterion != None:
        outfile.write("\t\t<criterionID>%s</criterionID>\n" % writeCriterion)
    outfile.write('\t\t<pairs>\n')
    for key1, item1 in comparisionMx[criterion].items():
        for key2, item2 in item1.items():
            outfile.write("""\t\t\t<pair>
            <initial>
                <alternativeID>%s</alternativeID>
            </initial>
            <terminal>
                <alternativeID>%s</alternativeID>
            </terminal>
            <value>
                %s
            </value>  
        </pair>\n""" % (key1, key2, correctType(item2)))
    outfile.write('\t\t</pairs>\n')     
    outfile.write('\t</alternativesComparisons>\n')
    PyXMCDA.writeFooter(outfile)
    outfile.close()  
 
 
def correctType(value):
    if isinstance(value, float):
        return "<real>%s</real>" % value
    elif isinstance(value, int):
        return "<integer>%s</integer>" % value    
    elif isinstance(value, str):
        return "<label>%s</label>" % value
    else:
        return "<label>%s</label>" % value
       
def getAlternativesComparisonsAtCriteria (xmltree, mcdaConcept=None) :

    #Retourne le premier alternativeComparisons trouve avec le bon MCDAConcept (si precise)
    #Par la suite, retourner une liste ?
    
    if mcdaConcept == None :
        strSearch = ".//alternativesComparisons"
    else :
        strSearch = ".//alternativesComparisons[@mcdaConcept=\'" + mcdaConcept + "\']"

    comparisons = xmltree.xpath(strSearch)

    if comparisons == None :
        return {}
    
    else :
        datas = {}
        for comparison in comparisons :
            crit = comparison.find("criterionID").text
            for pair in comparison.findall ("pairs/pair") :
                init = pair.find("initial/alternativeID").text
                term = pair.find("terminal/alternativeID").text
                
                val = PyXMCDA.getNumericValue(pair)
                # Only the alternatives concerned
                if crit != None :
                    # We check if init is still an entry in the table
                    if not(datas.has_key(crit)) :
                        datas[crit] = {}
                    if not(datas[crit].has_key(init)) :
                        datas[crit][init] = {}
                    datas[crit][init][term] = val
                else :
                    if not(datas.has_key(init)) :
                        datas[init] = {}
                    datas[init][term] = val

        return datas

def xmcda_write_method_messages(xmlfile, type, messages) :
    if type not in ('log', 'error'):
        raise ValueError, 'Invalid type: %s' % type
    xmlfile.write('<methodMessages>\n')
    for message in messages :
       xmlfile.write('<%sMessage><text><![CDATA[%s]]></text></%sMessage>\n' % (type, message, type))
    xmlfile.write('</methodMessages>\n')


def main(argv=None):
    for_diviz = (inspect.stack()[0][1] != '/Users/wachu/mgr/src/selectOneCriterion/selectOneCriterion.py')    
    
    if argv is None:
        argv = sys.argv
    
    parser = argparse.ArgumentParser(description=__doc__)

    grp_input = parser.add_argument_group("Inputs")
    grp_input.add_argument('-s', '--selected')
    grp_input.add_argument('-o', '--outranking')

    grp_output = parser.add_argument_group("Outputs")
    grp_output.add_argument('-r', '--outrankingOut', metavar='output.xml')
    grp_output.add_argument('-m', '--messages', metavar='<file.xml>', help='All messages are redirected to this XMCDA file instead of being sent to stdout or stderr.  Note that if an output directory is specified (option -O), the path is relative to this directory.')

    args = parser.parse_args()

    if not for_diviz:
        in_dir = "tests/mieszkaniePoznan/"
        in_selected = in_dir + "selected.xml"
        in_outranking = in_dir + "outranking.xml"
        
        out_dir = "tests/mieszkaniePoznan/"
        out_outranking = out_dir + "outrankingOut.xml"
        out_messages = out_dir + "message.xml"

    else :
        in_selected = args.selected
        in_outranking = args.outranking
    
        out_outranking = args.outrankingOut
        out_messages = args.messages
    
    if out_messages:
        messages_fd = open(out_messages, 'w')
        PyXMCDA.writeHeader(messages_fd)
    
    exitStatus = 0
    
    try:
        makeSelection(in_selected, in_outranking, out_outranking)
    except ValueError as e:
        #(ValueError,RuntimeError, TypeError, NameError,KeyError) as e:
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
            
    return exitStatus        
 
 
 
 
# -*-coding:utf-8 -*
import sys

class Distillation:
    
    def __init__(self, alternativesIds, CredibilityMatrix):
        self.alternatives = alternativesIds
        self.CredibilityMatrix = CredibilityMatrix
        self.resultsHolder = self.createArrayOfAlternatives()
        self.lambd = 0
        self.options = self.Options(0.15, 0.3)
        
        self.dest()
    
    def dest(self):
        self.BuildDistillationPreorder(True)
        self.BuildDistillationPreorder(False)
        self.MakeIntersection()
        
        
    class Alternative:
        def __init__(self, name):
            self.name = name
            self.isGlobalSelected = None#False
            self.isLocalSelected = None#False
            self.qualification = 0
            self.placeInAscendingPreorder = 0
            self.placeInDescendingPreorder = 0
            
        def printInfo(self):
            print "%s : globl %s,  local %s,  qualification %s , placeinAscenfing %s, placeDESC %s." % (self.name, self.isGlobalSelected, self.isLocalSelected, self.qualification, self.placeInAscendingPreorder, self.placeInDescendingPreorder)   
            
    class Options:
        def __init__(self, Alpha, Beta):
            self.DistillationAlphaCoefficient = Alpha
            self.DistillationBetaCoefficient = Beta
     
    def MakeIntersection(self):
        final = {}
        for alt1 in self.alternatives:
            for alt2 in self.alternatives:
                if alt1 == alt2 :
                   final.setdefault(alt1, {}).update({alt2:'?'}) 
                else:
                    alt1Asc = self.resultsHolder[alt1].placeInAscendingPreorder
                    alt2Asc = self.resultsHolder[alt2].placeInAscendingPreorder
                    alt1Desc = self.resultsHolder[alt1].placeInDescendingPreorder
                    alt2Desc = self.resultsHolder[alt2].placeInDescendingPreorder
                    #print "alt1 %s; alt2 %s; alt1Asc %s ,alt2Asc %s , alt1Desc %s ,alt2Desc %s " % (alt1,alt2,alt1Asc, alt2Asc, alt1Desc, alt2Desc)
                    if alt1Asc <= alt2Asc:
                        if alt1Desc >= alt2Desc  :
                            
                            final.setdefault(alt1, {}).update({alt2:1.0})
                        else :
                            final.setdefault(alt1, {}).update({alt2:'?'})
                    else :
                        if alt1Desc >= alt2Desc  :
                            final.setdefault(alt1, {}).update({alt2:'?'})
                        else :
                            final.setdefault(alt1, {}).update({alt2:0})
                
        self.intersectionUpDowns = final
            
    def forConsolePrint(self):
        ret = ""
        for alt in self.alternatives:
            ret += "%s placeInAscendingPreorder  %d placeInDescendingPreorder %d\n" % (alt, self.resultsHolder[alt].placeInAscendingPreorder, self.resultsHolder[alt].placeInDescendingPreorder)
        return ret

    def downwards(self):
        value = {}
        for a, val in self.resultsHolder.items():
            value[a] = val.placeInDescendingPreorder
        return value
    
    def upwards(self):
        value = {}
        for a, val in self.resultsHolder.items():
            value[a] = -val.placeInAscendingPreorder  
        return value

    
    
    def createArrayOfAlternatives(self):
        value = {}
        for alt in self.alternatives:
            value[alt] = self.Alternative(alt)
        return value
        
    def PrepareToDistillation(self):
        self.lambd = 0.0

        for alternative1 in self.alternatives:
            if self.resultsHolder[alternative1].isGlobalSelected :
                for alternative2 in self.alternatives:
                    if (self.resultsHolder[alternative2].isGlobalSelected and 
                        alternative1 != alternative2 and 
                        self.CredibilityMatrix[alternative1][alternative2] > self.lambd):
                        self.lambd = self.CredibilityMatrix[alternative1][alternative2]
            self.resultsHolder[alternative1].isLocalSelected = self.resultsHolder[alternative1].isGlobalSelected

    def ComputeNewlambd(self):
        threshold = self.lambd - self.options.DistillationAlphaCoefficient * self.lambd - self.options.DistillationBetaCoefficient

        self.lambd = 0.0
        for alternative1 in self.alternatives:
            if self.resultsHolder[alternative1].isLocalSelected:
                for alternative2 in self.alternatives:
                    if (self.resultsHolder[alternative2].isLocalSelected and 
                        alternative1 != alternative2 and 
                        self.CredibilityMatrix[alternative1][alternative2] < threshold and 
                        self.CredibilityMatrix[alternative1][alternative2] > self.lambd) :
                        self.lambd = self.CredibilityMatrix[alternative1][alternative2]
            self.resultsHolder[alternative1].qualification = 0

    def ComputelambdQualification(self):
        credibility = 0

        for alternative1 in self.alternatives:
            if self.resultsHolder[alternative1].isLocalSelected:
                for alternative2 in self.alternatives:
                    credibility = self.CredibilityMatrix[alternative1][alternative2]

                    if (self.resultsHolder[alternative2].isLocalSelected and 
                        alternative1 != alternative2 and 
                        credibility > self.lambd and 
                        credibility > self.CredibilityMatrix[alternative2][alternative1] + self.options.DistillationAlphaCoefficient * credibility + self.options.DistillationBetaCoefficient) :
                        self.resultsHolder[alternative1].qualification += 1 
                        self.resultsHolder[alternative2].qualification -= 1
                        #self.resultsHolder[alternative1].printInfo()
                        #self.resultsHolder[alternative2].printInfo()

    def GetQualificationSet(self, isDescendingDistillation):
        currentQualification = 0
        alternativeCounter = 0
        maxQualification = -sys.maxint - 1
        minQualification = sys.maxint

        if isDescendingDistillation:
            for alternative in self.alternatives:
                if (self.resultsHolder[alternative].isLocalSelected and self.resultsHolder[alternative].qualification > maxQualification):
                        maxQualification = self.resultsHolder[alternative].qualification

            currentQualification = maxQualification
        else:
            for alternative in self.alternatives:
                if (self.resultsHolder[alternative].isLocalSelected and self.resultsHolder[alternative].qualification < minQualification):
                        minQualification = self.resultsHolder[alternative].qualification

            currentQualification = minQualification

        for alternative in self.alternatives:
            #print self.resultsHolder[alternative].qualification
            #print currentQualification
            LC = self.resultsHolder[alternative].qualification
            if (self.resultsHolder[alternative].isLocalSelected and LC == currentQualification):
                    alternativeCounter += 1 
            else:
                self.resultsHolder[alternative].isLocalSelected = False

        return alternativeCounter

    def ModifyDistillationSet(self, isDescendingDistillation, distillationNumber):
        if isDescendingDistillation:
            for alternative in self.alternatives:
                if self.resultsHolder[alternative].isLocalSelected:
                    self.resultsHolder[alternative].placeInDescendingPreorder = distillationNumber
                    self.resultsHolder[alternative].isGlobalSelected = False
        else:
            for alternative in self.alternatives:
                if self.resultsHolder[alternative].isLocalSelected:
                    self.resultsHolder[alternative].placeInAscendingPreorder = distillationNumber
                    self.resultsHolder[alternative].isGlobalSelected = False
        
        for alternative in self.alternatives:
            if self.resultsHolder[alternative].isGlobalSelected:
                return True
        return False

    def BuildDistillationPreorder(self, isDescendingDistillation):
        distillationNumber = 0
        alternativeCounter = 0
        if isDescendingDistillation:
            distillationNumber = 1
        else:
            distillationNumber = -self.alternatives.__len__() - 1

        for alternative in self.alternatives:
            self.resultsHolder[alternative].isGlobalSelected = True

        while True :
            if isDescendingDistillation:
                distillationNumber += alternativeCounter    
            self.PrepareToDistillation()
            while True : 
                self.ComputeNewlambd()
                self.ComputelambdQualification()
                alternativeCounter = self.GetQualificationSet(isDescendingDistillation)
                if not (alternativeCounter != 1 and self.lambd != 0) :
                    break

            if not isDescendingDistillation:
                distillationNumber += alternativeCounter
                
            if not self.ModifyDistillationSet(isDescendingDistillation, distillationNumber) :
                break

       
if __name__ == "__main__":
    sys.exit(main())
        
        
        
