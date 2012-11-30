# -*-coding:utf-8 -*
import sys

class Distillation:
    
    def __init__(self, alternativesIds, CredibilityMatrix):
        self.alternatives = alternativesIds
        self.CredibilityMatrix = CredibilityMatrix
        self.resultsHolder = self.createArrayOfAlternatives()
        self.lambd = 0
        self.options = self.Options(0.15, 0.3)
    
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
        pass
            
    def forConsolePrint(self):
        ret = ""
        for alt in self.alternatives:
            ret += "%s placeInAscendingPreorder  %d placeInDescendingPreorder %d\n" % (alt, self.resultsHolder[alt].placeInAscendingPreorder, self.resultsHolder[alt].placeInDescendingPreorder)
        return ret

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
#        
#def main(argv=None):
#    mx = {'Anal. Chem': {'s3': {'s3': 1, 's2': 1.0, 's1': 1.0, 's5': 1.0, 's4': 1.0}, 's2': {'s3': 0.6296296296296297, 's2': 1, 's1': 1.0, 's5': 0.8148148148148149, 's4': 1.0}, 's1': {'s3': 0.8148148148148149, 's2': 1.0, 's1': 1, 's5': 1.0, 's4': 1.0}, 's5': {'s3': 0.5000000000000001, 's2': 0.0, 's1': 0.24999999999999994, 's5': 1, 's4': 0.5000000000000001}, 's4': {'s3': 1.0, 's2': 1.0, 's1': 1.0, 's5': 1.0, 's4': 1}}, 'Algebra': {'s3': {'s3': 1, 's2': 0.8, 's1': 1.0, 's5': 0.6, 's4': 1.0}, 's2': {'s3': 0.24999999999999994, 's2': 1, 's1': 0.5, 's5': 1.0, 's4': 0.0}, 's1': {'s3': 1.0, 's2': 1.0, 's1': 1, 's5': 0.8, 's4': 0.8666666666666667}, 's5': {'s3': 0.0, 's2': 0.8666666666666667, 's1': 0.0, 's5': 1, 's4': 0.0}, 's4': {'s3': 1.0, 's2': 0.6, 's1': 0.8, 's5': 0.4, 's4': 1}}, 'Analysis': {'s3': {'s3': 1, 's2': 0.818181818181818, 's1': 1.0, 's5': 0.6363636363636362, 's4': 1.0}, 's2': {'s3': 0.1999999999999999, 's2': 1, 's1': 0.4, 's5': 1.0, 's4': 0.0}, 's1': {'s3': 1.0, 's2': 1.0, 's1': 1, 's5': 0.818181818181818, 's4': 0.8484848484848484}, 's5': {'s3': 0.0, 's2': 1.0, 's1': 0.1999999999999999, 's5': 1, 's4': 0.0}, 's4': {'s3': 1.0, 's2': 0.6363636363636362, 's1': 0.818181818181818, 's5': 0.45454545454545453, 's4': 1}}, 'Org. Chem': {'s3': {'s3': 1, 's2': 0.0, 's1': 0.0, 's5': 1.0, 's4': 0.1333333333333333}, 's2': {'s3': 0.7333333333333333, 's2': 1, 's1': 1.0, 's5': 0.8666666666666667, 's4': 1.0}, 's1': {'s3': 0.8666666666666667, 's2': 1.0, 's1': 1, 's5': 1.0, 's4': 1.0}, 's5': {'s3': 1.0, 's2': 0.0, 's1': 0.1333333333333333, 's5': 1, 's4': 0.2666666666666667}, 's4': {'s3': 1.0, 's2': 1.0, 's1': 1.0, 's5': 1.0, 's4': 1}}, 'Mathematics': {'s3': {'s3': 1, 's2': 0.8095238095238094, 's1': 1.0, 's5': 0.6190476190476191, 's4': 1.0}, 's2': {'s3': 0.0864197530864197, 's2': 1, 's1': 0.345679012345679, 's5': 1.0, 's4': 0.0}, 's1': {'s3': 1.0, 's2': 1.0, 's1': 1, 's5': 0.8095238095238094, 's4': 0.857142857142857}, 's5': {'s3': 0.0, 's2': 0.9365079365079365, 's1': 0.0, 's5': 1, 's4': 0.0}, 's4': {'s3': 1.0, 's2': 0.6190476190476191, 's1': 0.8095238095238094, 's5': 0.42857142857142855, 's4': 1}}, 'Chemistry': {'s3': {'s3': 1, 's2': 0.0, 's1': 0.0, 's5': 1.0, 's4': 0.43333333333333324}, 's2': {'s3': 0.6842105263157894, 's2': 1, 's1': 1.0, 's5': 0.8421052631578948, 's4': 1.0}, 's1': {'s3': 0.8421052631578948, 's2': 1.0, 's1': 1, 's5': 1.0, 's4': 1.0}, 's5': {'s3': 0.7894736842105263, 's2': 0.0, 's1': 0.06839999999999999, 's5': 1, 's4': 0.2736000000000001}, 's4': {'s3': 1.0, 's2': 1.0, 's1': 1.0, 's5': 1.0, 's4': 1}}, 'Root': {'s3': {'s3': 1, 's2': 0.0, 's1': 0.0, 's5': 0.7999999999999999, 's4': 0.85}, 's2': {'s3': 0.12345679012345662, 's2': 1, 's1': 0.7749999999999999, 's5': 0.925, 's4': 0.0}, 's1': {'s3': 0.925, 's2': 1.0, 's1': 1, 's5': 0.8999999999999999, 's4': 0.9249999999999999}, 's5': {'s3': 0.0, 's2': 0.0, 's1': 0.0, 's5': 1, 's4': 0.0}, 's4': {'s3': 1.0, 's2': 0.7999999999999999, 's1': 0.8999999999999999, 's5': 0.7, 's4': 1}}}
#    alt = ['s1', 's2', 's3', 's4', 's5']
#    for criterion in mx :
#        print "\t\t" + criterion
#        d = Distillation(alt, mx[criterion])
#        d.BuildDistillationPreorder(False)
#        d.BuildDistillationPreorder(True)
#        print d.forConsolePrint()    
##    d = Distillation(alt, mx['Algebra'])
##    d.BuildDistillationPreorder(True)
##    print d.forConsolePrint()
#if __name__ == "__main__":
#    sys.exit(main())
