# -*-coding:utf-8 -*
"""
ElectreDistillation - This module performs distillation (upwards/downwards)
Usage:
    ElectreDistillation.py -i DIR -o DIR

Options:
    -i DIR     Specify input directory. It should contain the following files:
                   alternatives.xml
                   credibility.xml
                   selected.xml
    -o DIR     Specify output directory. Files generated as output:
                   descending.xml
                   ascending.xml
                   medianPreorder.xml
                   final.xml
                   messages.xml
    --version  Show version.
    -h --help  Show this screen.
"""

import os, sys, argparse, inspect
from docopt import docopt
import PyXMCDA as px
from common import comparisons_to_xmcda, create_messages_file, get_dirs, \
    get_error_message, get_input_data, get_linear, write_xmcda, Vividict

__version__ = '0.1.0'


compatibleWith2_0_0 = True

def main(argv=None):
    try:
        args = docopt(__doc__, version=__version__)
        output_dir = None
        input_dir, output_dir = get_dirs(args)
        exitStatus = 0
        files = {}
        filenames = [
            'alternatives.xml',
            'credibility.xml',
            'selected.xml',
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

        makeDistilation(files['selected'], files['alternatives'], files['credibility'], os.path.join(output_dir,'descending.xml'), \
         os.path.join(output_dir,'ascending.xml'), os.path.join(output_dir,'median_preorder.xml'), os.path.join(output_dir,'final.xml'))
        create_messages_file(None, ('Everything OK.',), output_dir)
    except ValueError as e:
        exitStatus = -1
        create_messages_file((e.message), ('error.',), output_dir)
    return exitStatus


def output_distillation(filename, alternativesID, concept='downwars distillation', atCriterion='Root'):
    outfile = open(filename, 'w')
    if compatibleWith2_0_0 != None :
        px.writeHeader(outfile, '2.0.0')
    else:
        px.writeHeader(outfile)
        outfile.write('\t<description>\n\t\t<comment>%s on criterion: %s</comment>\n\t</description>\n' % (concept, atCriterion))

    outfile.write('    <alternativesValues mcdaConcept="%s">\n' % concept)
    for id, val in sorted(alternativesID.items(), key=lambda alt : alt[1], reverse=True):
    #for id, val in criteria_ids.items():
        outfile.write('''
            <alternativeValue>
                <alternativeID>%s</alternativeID>
                <value>
                    <real>%s</real>
                </value>
            </alternativeValue>''' % (id, val))
    outfile.write('\n    </alternativesValues>\n')
    px.writeFooter(outfile)
    outfile.close()

def write_xmcda_content(filename, content=None):
    outfile = open(filename, 'w')
    px.writeHeader (outfile)
    if content != None:
            outfile.write(content)
    px.writeFooter(outfile)
    outfile.close()

def makeDistilation(in_selected, in_alternatives, in_credibility, out_descending, out_ascending, out_medianPreorder, out_final):
    xml_alternatives = px.parseValidate(in_alternatives)
    xml_selected = px.parseValidate(in_selected)
    xml_alternatives = px.parseValidate(in_alternatives)
    xml_credibility = px.parseValidate(in_credibility)
    if xml_selected == None:
        raise ValueError, "Invalid selected file"
    if xml_alternatives == None:
        raise ValueError, "Invalid alternative file"
    if xml_credibility == None:
        raise ValueError, "Invalid credibility file"

    onCriterion = px.getParameterByName(xml_selected, 'selectedCriterion')
    alternativesID = px.getAlternativesID(xml_alternatives)
    alternativesComparisions = getAlternativesComparisonsAtCriteria(xml_credibility, alternativesID)

    if not alternativesComparisions.has_key(onCriterion):
        raise ValueError, 'Invalid selected criterion'

    distillation = Distillation(alternativesID, alternativesComparisions[onCriterion])

    output_distillation(out_ascending, distillation.downwards(), 'downward distillation', onCriterion)
    output_distillation(out_descending, distillation.upwards(), 'upward distillation', onCriterion)
    output_distillation(out_medianPreorder, distillation.medianPreorder(), 'median Preorder', onCriterion)

    writeAlternativeComparision(out_final, distillation.intersectionUpDowns, 'outranks', onCriterion)

def writeAlternativeComparision(filename, intersectionMx, comparisionType=None, criterion=None):
    compatibleWith2_0_0 = True
    outfile = open(filename, 'w')
    if compatibleWith2_0_0 :
        px.writeHeader(outfile, '2.0.0')
        criterion = None #definicja jakiego kryterium dotyczny dane porwnanie dopiero w standardzie 2_2_1
    else:
        px.writeHeader(outfile)
    outfile.write('\t<alternativesComparisons mcdaConcept="intersection of upwards and downwards distillation ">\n')
    if comparisionType != None :
        outfile.write("\t\t<comparisonType>%s</comparisonType>\n" % comparisionType)
    if criterion != None:
        outfile.write("\t\t<criterionID>%s</criterionID>\n" % criterion)
    outfile.write('\t\t<pairs>\n')
    for key1, item1 in intersectionMx.items():
        for key2, item2 in item1.items():
#            if item2 == '?' :
#                continue
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
    px.writeFooter(outfile)
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

def getAlternativesComparisonsAtCriteria (xmltree, altId, mcdaConcept=None) :

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

                val = px.getNumericValue(pair)
                # Only the alternatives concerned
                if altId.count(init) > 0 :
                    if altId.count(term) > 0 :
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


    def forPrintOutrankingMx(self):
        ret = ""
        for alt in self.alternatives:
            ret += "&\t%s" % alt
        for alt in self.alternatives:
            ret += "\\\\\n%s" % alt
            for alt2 in self.alternatives:
                ret += "&\t%s" % self.intersectionUpDowns[alt][alt2]

        return ret

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
        print self.forPrintOutrankingMx()

    def forConsolePrint(self):
        ret = ""
        for alt in self.alternatives:
            ret += "%s placeInAscendingPreorder  %d placeInDescendingPreorder %d\n" % (alt, self.resultsHolder[alt].placeInAscendingPreorder, self.resultsHolder[alt].placeInDescendingPreorder)
        return ret

    def downwards(self):
        values = {}
        for a, val in self.resultsHolder.items():
            values[a] = val.placeInDescendingPreorder
        return values

    def upwards(self):
        values = {}
        places = {}
        for a, val in self.resultsHolder.items():
            place = -val.placeInAscendingPreorder
            values[a] = place
            if not place in places:
                places[place]=True
        for i in range(len(places)):
            num = i + 1
            while not num in values.values():
                for a in self.resultsHolder.keys():
                    if values[a] > num:
                        values[a] = values[a] - 1

        print values
        return values

    def medianPreorder(self):
        values = {}
        up = self.upwards()
        down = self.downwards()
        for a in self.resultsHolder.keys():
            values[a] = (up[a] + down[a]) / 2.0
            print values[a]
        return values

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
