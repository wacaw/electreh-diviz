# -*-coding:utf-8 -*

class Criterion():
    def __init__(self, name):
        self.name = name
        self.level = 0
        self.parent = []
        self.change = False
        self.clear()
        self.indiff = None
        self.pref = None
        self.veto = None
        self.indiffAlpha = 1
        self.indiffBeta = 0
        self.prefAlpha = 1
        self.prefBeta = 0
        self.vetoAlpha = 1
        self.vetoBeta = 0
    
    def setParent(self, parent, one=False):
    	if one :
            self.parent = []
        self.parent.append(parent)
    
    def getParent(self):
        if self.parent.__len__() != 0:
            return self.parent[0]
        else :
            return ''
    
    def hasParent(self, parentName):
        return parentName in self.parent
    
    def parentsNumber(self):
        return len(self.parent)  
    
    def setWeight(self, weight):
        self.weight = weight

    def setIndPrefVetoFromArray(self, arr):
        if ('indiff' in arr or 'indifference' in arr) \
           and ('pref' in arr or 'preference' in arr) \
           and 'veto' in arr: 
            if 'indiff' in arr:
                self.indiff = arr['indiff']
            else:
                self.indiff = arr['indifference']
            if 'pref' in arr:
                self.pref = arr['pref']
            else:
                self.pref = arr['preference']
            self.veto = arr['veto']
        #nie potrzeba, bo są w zamian progi alfa beta
        #else:
            #raise ValueError, 'setIndPrefVetoFromArray erro! Arr have no ind, pref or veto! Criterion: Arr: %s' % (self.name, arr)
    
    def getOneFromArray(self, arr, default, args):
        for a in args.split(','):
            if a in arr:
                return arr[a]
        return default
    
    def setAlphaBetaFromArray(self, arr):
        self.indiffAlpha = self.getOneFromArray(arr, 1, 'indiffa,indiffA,indiffalpha,indiffAlpha,indifferencea,indifferenceA,indifferencealpha,indifferenceAlpha,indiff_a,indiff_A,indiff_alpha,indiff_Alpha,indifference_a,indifference_A,indifference_alpha,indifference_Alpha')
        self.indiffBeta = self.getOneFromArray(arr, 0, 'indiffb,indiffB,indiffbeta,indiffBeta,indifferenceb,indifferenceB,indifferencebeta,indifferenceBeta,indiff_b,indiff_B,indiff_beta,indiff_Beta,indifference_b,indifference_B,indifference_beta,indifference_Beta')
        
        self.prefAlpha = self.getOneFromArray(arr, 1, 'prefa,prefA,prefalpha,prefAlpha,preferencea,preferenceA,preferencealpha,preferenceAlpha,pref_a,pref_A,pref_alpha,pref_Alpha,preference_a,preference_A,preference_alpha,preference_Alpha')
        self.prefBeta = self.getOneFromArray(arr, 0, 'prefb,prefB,prefbeta,prefBeta,preferenceb,preferenceB,preferencebeta,preferenceBeta,pref_b,pref_B,pref_beta,pref_Beta,preference_b,preference_B,preference_beta,preference_Beta')
        
        self.vetoAlpha = self.getOneFromArray(arr, 1, 'vetoa,vetoA,vetoalpha,vetoAlpha,veto_a,veto_A,veto_alpha,veto_Alpha')
        self.vetoBeta = self.getOneFromArray(arr, 0, 'vetob,vetoB,vetobeta,vetoBeta,veto_b,veto_B,veto_beta,veto_Beta')
    
    def getAlphaBeta(self, valA, valB):
        indiff = self.getIndiff(valA, valB)
        pref = self.getPref(valA, valB)
        veto = self.getVeto(valA, valB)
        if not 0 <= indiff <= pref <= veto:
            raise ValueError, 'test 0≤q(a)≤p(a)≤v(a) is not fulfilled on criterion "%s"' % self.name
        else:
            return indiff, pref, veto
            
    
    def getVeto(self, valA, valB):
        if self.veto != None :
            return self.veto
        else:
            return self.vetoAlpha * min(valA, valB) + self.vetoBeta
    
    def getPref(self, valA, valB):
        if self.pref != None :
            return self.pref
        else:
            return self.prefAlpha * min(valA, valB) + self.prefBeta

    def getIndiff(self, valA, valB):
        if self.indiff != None :
            return self.pref
        else:
            return self.indiffAlpha * min(valA, valB) + self.indiffBeta        

    def setThresholdsIndPrefFromArray(self, arr):
        if 'smallestInd' in arr and 'greatestInd' in arr and 'smallestPref' in arr and 'greatestPref' in arr :
            self.setThresholdsIndPref(arr['smallestInd'], arr['greatestInd'], arr['smallestPref'], arr['greatestPref'])
        else:
            raise ValueError, 'Thresholds have no smallestInd, greatestInd, smallestPref or greatestPref! on "%s", array=' % (self.name, arr)
            
    def setThresholdsIndPref(self, indifferenceS, indifferenceG, preferenceS, preferenceG):
        self.qs = indifferenceS
        self.qg = indifferenceG
        self.ps = preferenceS
        self.pg = preferenceG
        #if not self.validateThresholdsIndPref() :
        #    self.clear()
        
    def validateThresholdsIndPref(self):
        if not self.qs <= self.qg <= self.ps <= self.pg:
            raise ValueError, 'Wrong threshold on "%s". Not valid: %s<=%s<=%s<=%s' % (self.name, self.qs, self.qg, self.ps, self.pg)
        return self.qs <= self.qg <= self.ps <= self.pg
    
    def clear(self):
        self.pg = None
        self.ps = None
        self.qs = None
        self.qg = None
        
    def forPrint(self):
        return "%s qs:%s, qg:%s, ps:%s, pg:%s\n" % (self.name, self.qs, self.qg, self.ps, self.pg)
    
    def parents(self):
    	ret = ''
    	for parent in self.parent:
            ret += parent
        return ret
    
    def getParentFromName(self):
        if self.name.split('#').__len__() > 1 :
           return self.name.split('#')[1]
        else :
           return None  
    
    def getNameOfParent(array, critName):  
        for sth, crit in array.items():
            if crit.name == critName :
                return crit.getParent()
	
    def __repr__(self):
        #return self.forPrint()
        return "'%s'" % self.name
        #return  "%s, lev: %d; parent(%d):%s " % (self.name, self.level, self.parentsNumber(), self.parent)
    def __str__(self):
    	return '%s' % self.name
        #return "%s, lev: %d; parent(%d):%s" % (self.name, self.level, self.parentsNumber(), self.parent)
 
    def orgname(self):
        return self.name.split('#')[0]
    
    @staticmethod
    def getLeaves(criterion, criteria):
       """Returns a list of criteria at the last level"""
       leaves = [key for key, value in criteria.items() if value.getParent() == criterion]
       if len(leaves) == 0:
           return None
       leavesLeaves = []
       for crit in leaves:
           if Criterion.getLeaves(crit, criteria) != None :
               leavesLeaves.extend(Criterion.getLeaves(crit, criteria))
       if len(leavesLeaves) == 0 :
           return leaves
       else :
           return leavesLeaves
    
    
    @staticmethod
    def f7(seq):
        '''Wzwraca unikalne elementy listy'''
        seen = set()
        seen_add = seen.add
        return [ x for x in seq if x not in seen and not seen_add(x)]
    
    
    @staticmethod
    def getLB(criterion, criteria, LB=None):
       if LB == None:
           LB = [criterion]
       """Zwraca LB: Returns a list of criteria at the last but one level"""
       leaves = [key for key, value in criteria.items() if value.getParent() == criterion]
       if len(leaves) == 0:
           return None
       leavesLeaves = []
       for crit in leaves:
           if Criterion.getLB(crit, criteria, leaves) != None :
               leavesLeaves.extend(Criterion.getLB(crit, criteria, leaves))
       if len(leavesLeaves) == 0 :
           return LB
       else :
           return Criterion.f7(leavesLeaves)
       
    @staticmethod
    def getCuttinLevelAtCriterion(criterion, criteria, concordanceCutLev, weights):
       leaves = [key for key, value in criteria.items() if value.getParent() == criterion]
       if type(concordanceCutLev).__name__ == 'float':
           if weights.has_key(criterion):
               cutLevel = concordanceCutLev * weights[criterion]
           else :
               cutLevel = 0
       elif concordanceCutLev.has_key(criterion) :
           cutLevel = concordanceCutLev[criterion]
       else:
           cutLevel = 0
       for crit in leaves:
           cutLevel += Criterion.getCuttinLevelAtCriterion(crit, criteria, concordanceCutLev,weights)
       return cutLevel 

    @staticmethod    
    def getNumberOfLevelsOfCriteria(criteria):
        max = 0
        for criterion in criteria.values():
            if criterion.level > max:
                max = criterion.level
        return max
    @staticmethod    
    def getWithoutLast(criteria):
        values = []
        max = Criterion.getNumberOfLevelsOfCriteria(criteria)
        for criterion in criteria.values():
            if criterion.level < max:
                values.append(criterion.name)
        return values
    @staticmethod    
    def getChildren(criterion, criteria):
        values = []
        for crit in criteria.values():
            if crit.getParent() == criterion:
                values.append(crit.name)
        return values    
    

