# -*-coding:utf-8 -*
import sys, os, argparse, inspect, re, subprocess
import pymprog
import itertools
from contextlib import nested
from compiler.ast import Sub
#add path to local PyXMCDA
sys.path.append('/Users/wachu/mgr/src')
from Criterion import *
import PyXMCDA
sys.path.append('/Users/wachu/mgr/src/electreH')
#from distillation import *

from time import gmtime, strftime


VERSION = "1.0"
"""#DIVIZ PROGRAM
#cmd: python script -a infile1 -c infile2 -p infile3 -t infile4 -ac infile5 -r outfile1 -m outfile2
#
# 5 x infile
# 2 x outfile
###
"""
def main(argv=None):
    #zmenna do testów
    for_diviz = (inspect.stack()[0][1] != '/Users/wachu/mgr/src/electreH-ROR/electreHROR.py')

    if argv is None:
        argv = sys.argv

    parser = argparse.ArgumentParser(description=__doc__)

    grp_input = parser.add_argument_group("Inputs")
    grp_input.add_argument('-a', '--alternatives')
    grp_input.add_argument('-p', '--performances')
    grp_input.add_argument('-t', '--treeHierarchy')
    grp_input.add_argument('-c', '--criteria')
    grp_input.add_argument('-ac', '--alternativecomparisions')


    grp_output = parser.add_argument_group("Outputs")
    grp_output.add_argument('-r', '--outranking', metavar='output.xml')
    #grp_output.add_argument('-o', '--credibility', metavar='output.xml')
    grp_output.add_argument('-m', '--messages', metavar='<file.xml>', help='All messages are redirected to this XMCDA file instead of being sent to stdout or stderr.  Note that if an output directory is specified (option -O), the path is relative to this directory.')

    args = parser.parse_args()

    if not for_diviz:
        in_dir = "/Users/wachu/mgr/src/electreH-ROR/test/mieszkaniePoznan/"

        in_dir = "/Users/wachu/mgr/src/electreH-ROR/test/in1/"

        in_hierarchy = in_dir + "hierarchyComplicated.xml"
        in_criteria = in_dir + "criteria.xml"
        in_alternatives = in_dir + "alternatives.xml"
        in_performances = in_dir + "performances.xml"
        in_alternativecomparisions = in_dir + "alternativeComparisions.xml"

        in_hierarchy = in_dir + "hierarchy.xml"

        out_dir = "/Users/wachu/mgr/src/electreH-ROR/test/in1"
        out_outranking = out_dir + "outranking.xml"
        out_messages = out_dir + "message.xml"
        #out_credibility = out_dir + "credibility.xml"

    else :
        in_hierarchy = args.treeHierarchy
        in_criteria = args.criteria
        in_alternatives = args.alternatives
        in_performances = args.performances
        in_alternativecomparisions = args.alternativecomparisions

        out_outranking = args.outranking
        #out_credibility = args.credibility
        out_messages = args.messages

    if out_messages:
        messages_fd = open(out_messages, 'w')
        PyXMCDA.writeHeader(messages_fd)

    exitStatus = 0

    try:
        alternativesIDs, criteriaIDs, performanceTable, criteria, criteriaThresholds, outranking = \
        parse_xmcda_files(in_hierarchy, in_criteria, in_performances, in_alternatives, in_alternativecomparisions)
        method = ElectreHROR(alternativesIDs, criteriaIDs, performanceTable, criteria, criteriaThresholds, outranking)
        method.solve()
        method.writeOutranking(out_outranking)
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


class Comparable():
    def __init__(self):
        self.value = 0
        self.shouldBeEqualTo = []
        self.shouldBeLessThan = []
        self.shouldBeGreaterThan = []

    def addConstraints(self, sth, type):
        if '=' in type :
            self.shouldBeEqualTo.append(sth)
        if '>' in type:
            self.shouldBeGreaterThan.append(sth)
        if '<' in type:
            self.shouldBeLessThan.append(sth)

    def check(self, value=None):
        if value == None:
            value = self.value
        for i in self.shouldBeEqualTo :
            if i <> value :
                return False
        for i in self.shouldBeLessThan :
            if i >= value :
                return False
        for i in self.shouldBeGreaterThan :
            if i <= value :
                return False
        return True


class ElectreHROR():
    def __init__(self, alternativesIDs, criteriaIDs, performanceTable, criteria, criteriaThresholds, outranking):
        self.alternativesIDs = alternativesIDs
        self.criteriaIDs = criteriaIDs
        self.performanceTable = performanceTable
        self.criteria = criteria
        self.criteriaThresholds = criteriaThresholds
        self.makeCriteriaArray()
        self.extremeValOnCrit = {}
        self.makeextremeValOnCrit()
        self.outranking = outranking

        self.EL = Criterion.getLeaves('Root', self.criteria)
        self.LBO = Criterion.getLB('Root', self.criteria)
        self.TreeWithoutLeaves = self.criteria.keys()
        for x in self.EL:
            self.TreeWithoutLeaves.remove(x)

        self.checkConditions()



        #self.solver.solvopt(integer='advanced')

        self.initVariables(True)

        #self.solve()


    def initVariables(self,necessary=True, maxEpsilon=0):
        self.solver = pymprog.model('electreHROR')
        self.epsilon = self.solver.var()
        self.v = self.solver.var(self.EL, 'veto', int)
        #słowo lambda jest zarezerowane w pythonie
        self.lamba = self.solver.var(self.TreeWithoutLeaves, 'lambda')
        mrBoard = pymprog.iprod(self.TreeWithoutLeaves,self.alternativesIDs, self.alternativesIDs)
        self.Mr = self.solver.var(mrBoard, 'Mr', bool)
        self.delta = self.solver.var(self.TreeWithoutLeaves, 'delta', int)
        mtBoard = pymprog.iprod(self.EL, self.alternativesIDs, self.alternativesIDs)
        self.Mt = self.solver.var(mtBoard, 'Mt', bool)
        aBoard = pymprog.iprod(self.EL, self.alternativesIDs, self.alternativesIDs)
        self.psi = self.solver.var(aBoard, 'psi', float)
        #self.solver.min(self.epsilon)
        self.solver.max(self.epsilon)
        self.addConstraints(necessary)

    def addConstraints(self,necessary=True):
        self.addFromPairwiseComparisions()
        self.addFromConcordanceCutAndValuesInterCriteria()
        self.addFromValuesOfMarginalConcordance()
        self.addMonotonicity()

        if necessary:
            self.addNecessary()
        elif necessary==False:
            self.addPossible()

    def addFromPairwiseComparisions(self):
        for key, onCriterion in self.outranking.items():
            E = Criterion.getLeaves(key, self.criteria)
            LB = Criterion.getLB(key, self.criteria)
            crit=key
            for altA, objectB in onCriterion.items():
                altB = objectB.keys()[0]
                value = objectB.values()[0]
                if value == 1:
                    self.solver.st(sum(self.psi[crit, altA, altB] for crit in E) >= self.lamba[key])
                    #self.solver.st(sum(self.psi[crit, altA, altB] for crit in E) >= sum(self.lamba[t] for t in LB))
                    for crit in E:
                        valA = self.performanceTable[altA][self.getOriginalName(crit)]
                        valB = self.performanceTable[altB][self.getOriginalName(crit)]
                        self.solver.st(valB - valA + self.epsilon <= self.v[crit])
                if value == 0:
                    self.solver.st(sum(self.psi[crit, altA, altB] + self.epsilon for crit in E) \
                                   <= sum(self.lamba[t] for t in LB) + self.Mr[key, altA, altB])


                    maxGr = 0
                    for crit in E:
                        if self.extremeValOnCrit[self.getOriginalName(crit)]['delta'] > maxGr:
                            maxGr = self.extremeValOnCrit[self.getOriginalName(crit)]['delta']
                    self.solver.st(self.delta[key] >= max(self.extremeValOnCrit[self.getOriginalName(crit)]['delta'] for crit in E))
                    for crit in E:
                        valA = self.performanceTable[altA][self.getOriginalName(crit)]
                        valB = self.performanceTable[altB][self.getOriginalName(crit)]
                        self.solver.st(valB - valA >= self.v[crit] - maxGr * self.Mt[crit, altA, altB])
                    self.solver.st(self.Mr[key,altA, altB] + sum(self.Mt[criterion, altA, altB] for criterion in E) <= len(E))



    def addFromConcordanceCutAndValuesInterCriteria(self):
        for criterion in self.LBO:
            E = Criterion.getLeaves(criterion, self.criteria)
            self.solver.st(self.lamba[criterion] >= sum(self.psi[crit, self.extremeValOnCrit[self.getOriginalName(crit)]['max_alt'], self.extremeValOnCrit[self.getOriginalName(crit)]['min_alt']] for crit in E) / 2)
            self.solver.st(self.lamba[criterion] <= sum(self.psi[crit, self.extremeValOnCrit[self.getOriginalName(crit)]['max_alt'], self.extremeValOnCrit[self.getOriginalName(crit)]['min_alt']] for crit in E))

        for criterion in self.criteria:
            if not criterion in self.EL and not criterion in self.LBO:
                #print criterion
                subcriteria = Criterion.getChildren(criterion, self.criteria)
                #print subcriteria
                self.solver.st(self.lamba[criterion] == sum(self.lamba[crit] for crit in subcriteria))

        #Dodałem to ograniczenie
        self.solver.st(self.lamba['Root'] == 1)

        self.solver.st(sum(self.psi[crit, self.extremeValOnCrit[self.getOriginalName(crit)]['max_alt'], self.extremeValOnCrit[self.getOriginalName(crit)]['min_alt']] for crit in self.EL) == 1)



        for criterion in self.EL:
            self.solver.st(self.v[criterion] >= self.criteria[criterion].pg + self.epsilon)

        for key, onCriterion in self.outranking.items():
            if key in self.EL:
                for altA, objectB in onCriterion.items():
                    altB = objectB.keys()[0]
                    value = objectB.values()[0]
                    if value == '?':
                        valA = self.performanceTable[altA][self.getOriginalName(key)]
                        valB = self.performanceTable[altB][self.getOriginalName(key)]
                        if valA<=valB :
                            self.solver.st(self.v[key] >= valA-valB + self.epsilon)


    def addFromValuesOfMarginalConcordance(self):
        combinations = itertools.permutations(self.EL, 2)
        for pair in combinations:
            self.solver.st(self.psi[pair[0], self.extremeValOnCrit[self.getOriginalName(pair[0])]['max_alt'], self.extremeValOnCrit[self.getOriginalName(pair[0])]['min_alt']] == \
                           self.psi[pair[1], self.extremeValOnCrit[self.getOriginalName(pair[1])]['max_alt'], self.extremeValOnCrit[self.getOriginalName(pair[1])]['min_alt']])


        for criterion in self.EL:
            crit = self.criteria[criterion]
            for altA in self.alternativesIDs :
                for altB in self.alternativesIDs :
                     #FOR EL1
                     valA = self.performanceTable[altA][self.getOriginalName(crit.name)]
                     valB = self.performanceTable[altB][self.getOriginalName(crit.name)]

                     if valA - valB <= -crit.pg:
                         self.solver.st(self.psi[crit.name, altA, altB] == 0)
                     elif valA - valB <= -crit.ps:
                         self.solver.st(self.psi[crit.name, altA, altB] >= self.epsilon)
                     elif valA - valB >= -crit.qs:
                         self.solver.st(self.psi[crit.name, altA, altB] == \
                                         self.psi[crit.name, self.extremeValOnCrit[crit.orgname()]['max_alt'], self.extremeValOnCrit[crit.orgname()]['min_alt']])
                     elif valA - valB < -crit.qg:
                         self.solver.st(self.psi[crit.name, altA, altB] + self.epsilon <= \
                                         self.psi[crit.name, self.extremeValOnCrit[crit.orgname()]['max_alt'], self.extremeValOnCrit[crit.orgname()]['min_alt']])
                     #FOR EL2

                     if self.outranking.has_key(criterion) and \
                     self.outranking[criterion].has_key(altB) and \
                    self.outranking[criterion][altB].has_key(altA) and self.outranking[criterion][altB][altA] == 1:
                        self.solver.st(self.psi[crit.name, altA, altB] == 0)

                     if self.outranking.has_key(criterion) and \
                        self.outranking[criterion].has_key(altB) and \
                        self.outranking[criterion][altB].has_key(altA) and self.outranking[criterion][altB][altA] == '?':
                         self.solver.st(self.psi[crit.name,altA,altB]==\
                                        self.psi[crit.name, self.extremeValOnCrit[crit.orgname()]['max_alt'], self.extremeValOnCrit[crit.orgname()]['min_alt']])
                         self.solver.st(self.psi[crit.name,altA,altB]==\
                                        self.psi[crit.name, self.extremeValOnCrit[crit.orgname()]['max_alt'], self.extremeValOnCrit[crit.orgname()]['min_alt']])


    def addMonotonicity(self):
        for crit in self.EL:
            combinations = itertools.permutations(self.alternativesIDs, 4)
            for four in combinations:
                valA = self.performanceTable[four[0]][self.getOriginalName(crit)]
                valB = self.performanceTable[four[1]][self.getOriginalName(crit)]
                valC = self.performanceTable[four[2]][self.getOriginalName(crit)]
                valD = self.performanceTable[four[3]][self.getOriginalName(crit)]

                if valA - valB > valC - valD:
                    self.solver.st(self.psi[crit, four[0], four[1]] >= self.psi[crit, four[2], four[3]])
                elif valA - valB == valC - valD:
                    self.solver.st(self.psi[crit, four[0], four[1]] == self.psi[crit, four[2], four[3]])

    def addPossible(self):
        for crit in self.TreeWithoutLeaves:
            criterion = crit
            combinations = itertools.permutations(self.alternativesIDs, 2)
            E = Criterion.getLeaves(crit, self.criteria)
            LB = Criterion.getLB(crit, self.criteria)
            for pair in combinations:
                altA = pair[0]
                altB = pair[1]
                self.solver.st(sum(self.psi[crit, altA, altB] for crit in E) + self.epsilon >= self.lamba[criterion])
                for crit in E:
                    valA = self.performanceTable[altA][self.getOriginalName(crit)]
                    valB = self.performanceTable[altB][self.getOriginalName(crit)]
                    self.solver.st(valB - valA + self.epsilon <= self.v[crit])

    def addNecessary(self):
        for crit in self.TreeWithoutLeaves:
            criterion = crit
            combinations = itertools.permutations(self.alternativesIDs, 2)
            E = Criterion.getLeaves(crit, self.criteria)
            LB = Criterion.getLB(crit, self.criteria)
            for pair in combinations:
                altA = pair[0]
                altB = pair[1]
                self.solver.st(sum(self.psi[crit, altA, altB] + self.epsilon for crit in E ) \
                                   <= (self.lamba[criterion] + self.Mr[criterion,altA, altB]))
                maxGr = 0
                for crit in E:
                    if self.extremeValOnCrit[self.getOriginalName(crit)]['delta'] > maxGr:
                        maxGr = self.extremeValOnCrit[self.getOriginalName(crit)]['delta']
                #self.solver.st(self.delta[criterion] >= max(self.extremeValOnCrit[self.getOriginalName(crit)]['delta'] for crit in E))
                for crit in E:
                    valA = self.performanceTable[altA][self.getOriginalName(crit)]
                    valB = self.performanceTable[altB][self.getOriginalName(crit)]
                    #print "%s %s %s" % (valA,valB,maxGr)
                    #self.solver.st(valB - valA >= self.v[crit] - maxGr * self.Mt[crit, altA, altB])
                self.solver.st(self.Mr[criterion,altA, altB] + sum(self.Mt[crit, altA, altB] for crit in E) <= len(E))

    def solve(self):

        self.solver.solve()
        #print self.solver.status()
        epsilon = self.solver.vobj()
        self.makeOutrankingROR()

        #print epsilon
        #print strftime("%H:%M:%S", gmtime())
        #print self.forPrintCriterionAltAltMx()

        #print self.solver.reportKKT()


        #print self.forPrintOutrankingMx()

        #print '\n'.join('%s = %g ' % (self.v[i].name, self.v[i].primal) for i in self.EL)

        #print '\n'.join('%s = %g ' % (self.lamba[i].name, self.lamba[i].primal) for i in self.LBO)


        #self.initVariables(epsilon)
        #self.addConstraints()
        #self.solve()

        #for crit in self.EL :
        #    print self.psi[crit, self.extremeValOnCrit[crit]['max_alt'], self.extremeValOnCrit[crit]['min_alt']].primal

        #lmb = self.criteria.keys()
        #for x in self.EL:
        #    lmb.remove(x)
#        for c in lmb:
#            for a in self.alternativesIDs:
#                for b in self.alternativesIDs:
#                    print self.psi[c,a,b]

#        for item in self.psi:
#            print "%s %s %s" % (item[0], item[1], item[2])
#            for i in item:
#                print i
#



    def makeextremeValOnCrit(self):
        for criterion in self.criteria.values() :
             if self.criteriaIDs.count(criterion.name) > 0 :
                 crit = self.getOriginalName(criterion.name)
                 self.extremeValOnCrit[crit] = {}
                 self.extremeValOnCrit[crit]['max'] = -sys.maxint
                 self.extremeValOnCrit[crit]['min'] = sys.maxint
                 for alt in self.alternativesIDs :
                     if self.performanceTable[alt][crit] > self.extremeValOnCrit[crit]['max'] :
                         self.extremeValOnCrit[crit]['max'] = self.performanceTable[alt][crit]
                         self.extremeValOnCrit[crit]['max_alt'] = alt
                     if self.performanceTable[alt][crit] < self.extremeValOnCrit[crit]['min'] :
                         self.extremeValOnCrit[crit]['min'] = self.performanceTable[alt][crit]
                         self.extremeValOnCrit[crit]['min_alt'] = alt
                 self.extremeValOnCrit[crit]['delta'] = self.extremeValOnCrit[crit]['max'] - self.extremeValOnCrit[crit]['min']

    def makeCriteriaArray(self):
        for crit in self.criteriaThresholds :
            if self.criteriaIDs.count(crit) > 0 :
                self.criteria[crit].setThresholdsIndPrefFromArray(self.criteriaThresholds[crit])

    def forPrintCriteria(self):
        ret = ''
        for key, crit in self.criteria.items():
            ret += crit.forPrint()
        return ret

    def checkConditions(self):
        """
        a) qt,∗ ≤qt∗, pt,∗ ≤p∗t and qt∗ ≤pt,∗, for all t∈EL1,
        b) |gt(a)−gt(b)|<gt(c)−gt(d),ifa∼t b and c≻t d,forallt∈EL2,
        c) p∗t should be not greater than βt − αt, t ∈ EL1, where αt = min a∈A gt(a), and βt = maxa∈A gt(a).
        """
        for criterion in self.criteria.values():
            if criterion.name in self.EL:
                if not criterion.validateThresholdsIndPref():
                    raise ValueError , "Wrong thresholds"
                if criterion.pg > self.extremeValOnCrit[criterion.orgname()]['delta']  :
                    raise ValueError, 'Greatest value of the preference thresholds on "%s" criterion is too large (p*=%s, max-min=%s)' % (criterion.name, criterion.pg, self.extremeValOnCrit[criterion.orgname()]['delta'])
            #b)
        indiffSmallThanPreference = True
        outrank = {}
        indiff = {}
        for key, onCriterion in self.outranking.items():
            if key in self.EL:
                for altA, objectB in onCriterion.items():
                    altB = objectB.keys()[0]
                    value = objectB.values()[0]
                    if value == 1 :
                        outrank[key] = {'dif':self.performanceTable[altA][self.getOriginalName(key)] - self.performanceTable[altB][self.getOriginalName(key)], 'c':altA, 'd':altB}
                    if value == '?':
                        indiff[key] = {'dif':abs(self.performanceTable[altA][self.getOriginalName(key)] - self.performanceTable[altB][self.getOriginalName(key)]), 'a':altA, 'b':altB}
                if key in outrank and key in indiff :
                    cd = outrank[key]
                    ab = indiff[key]
                    if ab['a'] != cd['c'] and ab['a'] != cd['d'] and ab['b'] != cd['c'] and ab['b'] != cd['d']:
                        if ab['dif'] >= cd['dif'] :
                            raise ValueError, 'Incorrect indifference and outranking preferences on criterion %s' % key



    def __str__(self):
        return """alternatives:\t%s\ncriteria:\t%s\nperformance:\t%s\nextremeVal:\t%s\nhierarchy:\t%s\noutranking:\t%s\n
        """ % (
               self.alternativesIDs, self.criteria, self.performanceTable, self.extremeValOnCrit, self.criteria, self.outranking
               )
    def getOriginalName(self, criterionWithHash):
        """
        from Criterion Ex. Name#1 get Criterion Ex. Name
        """
        return criterionWithHash.split('#')[0]


    def forPrintCriterionAltAltMx(self):
        ret = ""

        for criterion in self.EL:
            ret += "\n\n%s\n" % criterion
            for alt in self.alternativesIDs:
                ret += "\t%s" % alt
            for alt in self.alternativesIDs:
                ret += "\n%s" % alt
                for alt2 in self.alternativesIDs:
                    ret += "\t%s" % self.psi[criterion, alt, alt2].primal
        return ret

    def makeOutrankingROR(self):
        max = Criterion.getNumberOfLevelsOfCriteria(self.criteria)
        sort = sorted(self.criteria.values(), key=lambda c:c.level, reverse=True)
        values = {}
        for crit in sort:
            if crit.level < max :
                cutLevel = self.lamba[crit.name].primal
                criteria = Criterion.getLeaves(crit.name, self.criteria)
                matrixAlt1 = {}
                for alt1 in self.alternativesIDs:
                    row = ""
                    for alt2 in self.alternativesIDs:
                        cmpr = self.compare_two_alternativesROR(alt1, alt2, crit, criteria, cutLevel)
                        matrixAlt1.setdefault(alt1, {}).update({alt2:cmpr['S']})

                values[crit] = matrixAlt1
        self.outrankingMatrix = values

    def compare_two_alternativesROR(self, alt1, alt2, atCriterion, criteria, cutLevel):
        if alt1==alt2:
            return {'S':'?'}
        CutLevelAtCriterion = 0
        veto = True
        for crit in criteria:
            concordanceTemp = self.psi[crit, alt1, alt2].primal
            if 1 == self.Mt[crit, alt1, alt2].primal:
                veto = False
            CutLevelAtCriterion += concordanceTemp

        fi = CutLevelAtCriterion # / sumOfWeights
        #print "CutLevelAtCriterion %s podzielone %s cutlevel %s" % (CutLevelAtCriterion , fi ,cutLevel)
        if fi >= cutLevel and veto :
            #print 'C(%s)(%s,%s) = %s >= λ(%s) =%s => %sS(%s)%s' % (atCriterion, alt1, alt2, CutLevelAtCriterion, atCriterion, cutLevel, alt1, atCriterion, alt2)
            return {'S':1.0, 'info':"CutLevelAtCriterion %s podzielone %s cutlevel %s" % (CutLevelAtCriterion , fi , cutLevel)}
        elif fi < cutLevel or not veto :
            #print 'C(%s)(%s,%s) = %s < λ(%s) =%s => %sSc(%s)%s' % (atCriterion,alt1,alt2,CutLevelAtCriterion,atCriterion, cutLevel,alt1,atCriterion, alt2 )
            return {'S':'0', 'info':"CutLevelAtCriterion %s podzielone %s cutlevel %s" % (CutLevelAtCriterion , fi , cutLevel)}
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

    def forPrintOutrankingMx2(self):
        ret = ""
        sort = sorted(self.outrankingMatrix, key=lambda c:c.level, reverse=True)
        #for criterion in [self.criteria['Root']]:#sort:
        for criterion in sort:

            sumOfOutranking = 0
            ret += "\n\n%s\n" % criterion.name
            for alt in self.alternativesIDs:
                ret += "\t%s" % alt
            for alt in self.alternativesIDs:
                ret += "\n%s" % alt
                for alt2 in self.alternativesIDs:
                    ret += "\t%s" % self.outrankingMatrix[criterion][alt][alt2]
                    if self.outrankingMatrix[criterion][alt][alt2]==1.0:
                         sumOfOutranking += 1
            ret += "\tsum of Outranking: %s (%s)" % ((sumOfOutranking - self.alternativesIDs.__len__()), sumOfOutranking)
        return ret


    def writeOutranking(self, filename):
        self.writeAlternativeComparision(filename, self.outrankingMatrix, 'outranks')

    def writeAlternativeComparision(self, filename, comparisionMx, comparisionType=None):
        outfile = open(filename, 'w')
        PyXMCDA.writeHeader(outfile)#, '2.0.0')
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
                            %s
                        </value>
                    </pair>\n""" % (key1, key2, correctType(item2)))
                outfile.write('\t\t</pairs>\n')
                outfile.write('\t</alternativesComparisons>\n')
            else:
                pass
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
    return a


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

                val = PyXMCDA.getValue(pair)
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

def parse_xmcda_files(in_hierarchy, in_criteria, in_performances, in_alternatives, in_alternativecomparisions):
#def parse_xmcda_files(in_dir):
    xml_crit = PyXMCDA.parseValidate(in_criteria)
    xml_alt = PyXMCDA.parseValidate(in_alternatives)
    xml_pt = PyXMCDA.parseValidate(in_performances)
    xml_hierarchy = PyXMCDA.parseValidate(in_hierarchy)
    xml_alternativeComp = PyXMCDA.parseValidate(in_alternativecomparisions)

    if xml_crit == None:
        raise ValueError, "Invalid criteria file"
        return
    if xml_alt == None:
        raise ValueError, "Invalid alternative file"
        return
    if xml_pt == None:
        raise ValueError, "Invalid performance table file"
        return
    if xml_hierarchy == None:
        raise ValueError, "Invalid assignment file"
        return
    if xml_alternativeComp == None:
        raise ValueError, "Invalid alternative comparisions file"
        return
    try:
        alternativesIDs = PyXMCDA.getAlternativesID(xml_alt)
        criteriaIDs = PyXMCDA.getCriteriaID(xml_crit)
        performanceTable = PyXMCDA.getPerformanceTable(xml_pt, alternativesIDs, criteriaIDs)
        criteria = get_hierarchy_array(xml_hierarchy)
        criteriaThresholds = PyXMCDA.getConstantThresholds(xml_crit, criteriaIDs)
        outranking = getAlternativesComparisonsAtCriteria(xml_alternativeComp, alternativesIDs)
    except:
        raise ValueError, "Failed to parse one or more file"
        return

    return alternativesIDs, criteriaIDs, performanceTable, criteria, criteriaThresholds, outranking


if __name__ == "__main__":
    sys.exit(main())
