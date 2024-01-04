# import package ...
import numpy
import math
import sys
import gzip
import json


def buildIndex(inputFile, terms):
    dicPosting = {}
    totalDoc = []
    numDocs = 0
    occurTerms = []
    docLength = {}

    with gzip.open(inputFile, 'rb') as f:
        corpus = json.loads(f.read().decode("utf-8"))
        stories = corpus['corpus']
        
        dicPosting = {}
        all = []
        for story in stories:
            storyID = story['storyID']
            text = story['text'].split()
            numDocs += 1
            occurTerms.extend(text)

            all.append(len(text))
            docLength[storyID] = len(text)

            
            for term in terms:
                postingList = []
                positions = []
                
                #phares
                if term.find(" ") != -1:
                    splitTerm = term.split()

                    if text[0] == splitTerm[0]:
                        flag = False
                        for i in range(1,len(splitTerm)):
                            if text[i] == splitTerm[i]:
                                flag = True
                            else: 
                                flag = False
                                prevIndex = -1
                                break
                            if flag:
                                prevIndex = -1
                    else: prevIndex = 0

                    for i in range(text.count(splitTerm[0])):
                        flag = False
                        for j in range(0,len(splitTerm)):

                            if (text.index(splitTerm[0],prevIndex+1)+j) < len(text) and text[text.index(splitTerm[0],prevIndex+1)+j] == splitTerm[j]:
                                flag = True
                            else:
                                flag = False
                                break
                        
                        if flag == True:
                            currIndex = text.index(splitTerm[0],prevIndex+1)
                            positions.append(currIndex)
                            prevIndex = currIndex
                        else:
                            currIndex = text.index(splitTerm[0],prevIndex+1)
                            prevIndex = currIndex

                    # docID?
                    if len(positions) != 0:
                        postingList.append({storyID: positions})
                    if term in dicPosting and len(postingList) != 0:
                        postingList.extend(dicPosting[term])
                        
                    if len(postingList) != 0:
                        dicPosting[term] = postingList

                #just words
                else:

                    if text[0] == term:
                        prevIndex = -1
                    else: prevIndex = 0

                    for i in range(text.count(term)):
                        currIndex = text.index(term,prevIndex+1)
                        positions.append(currIndex)
                        prevIndex = currIndex
                    # docID?
                    if len(positions) != 0:
                        postingList.append({storyID: positions})
                    if term in dicPosting and len(postingList) != 0:
                        postingList.extend(dicPosting[term])
                        
                    if len(postingList) != 0:
                        dicPosting[term] = postingList
        
        

        # print("\n------------------------------------------")
        # count={}
        # for i in occurTerms:
        #     try: count[i] += 1
        #     except: count[i]=1
        # print(dict(sorted(count.items(), key=lambda x:x[1])))
                

        totalDoc.append(numDocs)
        totalDoc.append(list(set(occurTerms)))
        totalDoc.append(occurTerms)
        

    return totalDoc, dicPosting, docLength

def boolean_query(queryType, listPhrases, index):
    storyIDs = set()
    if queryType == "and":

        # # first set to compare with other terms
        # if listPhrases[0].find(" ") != -1:
        #     isPhrase(listPhrases[0], index)

        # else:
        for story in index[listPhrases[0]]:
            storyIDs.add(list(story.keys())[0])

        # compare with other terms by using intersection
        for phrase in listPhrases:
            andCheckSet = set()

            # if phrase.find(" ") != -1:
            #     print("find space")
            #     print(phrase)
            #     print(phrase.index(" "))
            # else:
            for story in index[phrase]:
                andCheckSet.add(list(story.keys())[0])
            storyIDs = storyIDs.intersection(andCheckSet)

    elif queryType == "or": 
        for story in index[listPhrases[0]]:
            storyIDs.add(list(story.keys())[0])

        # compare with other terms by using union
        for phrase in listPhrases:
            andCheckSet = set()

            for story in index[phrase]:
                andCheckSet.add(list(story.keys())[0])
            storyIDs = storyIDs.union(andCheckSet)

    storyIDs = sorted(storyIDs)
    return storyIDs

def ql_query(queryType, listPhrases, index, docLength, totalDoc):
    mu = 300
    C = len(totalDoc[2])

    storyIDs = set()
    for phrase in listPhrases:
        for story in index[phrase]:
            storyIDs.add(list(story.keys())[0])

    results = {}
    if queryType == "ql":

        for phrase in listPhrases:

            for story in storyIDs:
                storyData = {}
                cqi = 0
                for data in index[phrase]:
                    cqi += len(list(data.values())[0])
                    if list(data.keys())[0] == story:
                        storyData = data
            
                D = docLength[story]
                if storyData == {}:
                    fqid = 0
                else: fqid = len(list(storyData.values())[0])

                score = (math.log((fqid+(mu*(cqi/C)))/(D+mu)))

                if list(results.keys()).count(story) == 0:
                    results[story] = round(score, 4)
                else:
                    results[story] = round((score + results[story]),4)
                
        results = sorted(results.items(), key=lambda x: x[1], reverse=True)

    return results

def bm25_query(queryType, listPhrases, index, docLength, totalDoc):
    k1 = 1.8
    k2 = 5
    b = 0.75
    N = totalDoc[0]
    avdl = len(totalDoc[2])/totalDoc[0]

    results = {}
    if queryType == "bm25":

        for phrase in listPhrases:

            for story in index[phrase]:
                dl = docLength[list(story.keys())[0]]
                K = k1*((1-b)+b*(dl/avdl))
                n1 = len(index[phrase])
                f1 = len((list(story.values())[0]))
                qf = listPhrases.count(phrase)

                score = (math.log((N-n1+0.5)/(n1+0.5)))*(((k1+1)*f1)/(K+f1))*((((k2+1)*qf)/(k2+qf)))
      
                
                if list(results.keys()).count(list(story.keys())[0]) == 0:
                    results[list(story.keys())[0]] = round(score, 4)
                else:
                    results[list(story.keys())[0]] = round((score + results[list(story.keys())[0]]),4)
                
        results = sorted(results.items(), key=lambda x: x[1], reverse=True)

    return results

def runQueries(index, queriesFile, outputFile):


    return None


if __name__ == '__main__':
    # Read arguments from command line, or use sane defaults for IDE.
    argv_len = len(sys.argv)
    inputFile = sys.argv[1] if argv_len >= 2 else "sciam.json.gz"
    queriesFile = sys.argv[2] if argv_len >= 3 else "trainQueries.tsv"
    outputFile = sys.argv[3] if argv_len >= 4 else "trainQueries.trecrun"

    if queriesFile == 'showIndex':
        terms = []
        if len(sys.argv) > 3:
            for index in range(3, len(sys.argv)):
                terms.append(sys.argv[index])

        totalDoc, index, docLength = buildIndex(inputFile, terms)
        keys = list(index.keys())
        values = list(index.values())

        print("total: "+str(totalDoc[0])+"\t"+ str(len(totalDoc[1]))+"\t"+str(len(totalDoc[2])))

        for i in range(len(keys)):
            occurNum = 0
            for j in values[i]:
                occurNum += len(list(j.values())[0])
            
            print(str(keys[i]) +": " + str(len(values[i]))+" docs "+ str(occurNum)+" occurences")

    elif queriesFile == 'showTerms':
        terms = []
        if len(sys.argv) > 3:
            for index in range(3, len(sys.argv)):
                terms.append(sys.argv[index])
        totalDoc, index, docLength = buildIndex(inputFile, terms)
        keys = list(index.keys())
        values = list(index.values())

        for i in range(len(keys)):
            occurNum = 0
            for j in values[i]:
                occurNum += len(list(j.values())[0])
            
            print("\n")
            print(str(keys[i]) +": " + str(len(values[i]))+" docs "+ str(occurNum)+" occurences")
            print(values[i])

    else:
        output = open(outputFile, 'w')
        with open(queriesFile, 'rb' ) as f:
            while True:
                line = str(f.readline().decode("utf-8"))
                if line == "": break


                queryType = (line[0:line.find("\t")]).lower()
                queryName = line[line.find("\t")+1:line.find("\t",line.find("\t")+1)]
                wordPhrases =  line[line.find("\t",line.find("\t")+1)+1:len(line)-1]
                ranking = 0
                # queryType = "ql"
                # queryName = "q-ac"
                # wordPhrases = "amherst\tcollege"

                listPhrases = []
                indexes = [i for i, c in enumerate(wordPhrases) if c == "\t"]
                if len(indexes) != 0:
                    listPhrases.append(wordPhrases[0:indexes[0]])
                    for i in range(1,wordPhrases.count('\t')+1):
                        if len(listPhrases) == wordPhrases.count('\t'):
                            listPhrases.append(wordPhrases[indexes[i-1]+1:len(wordPhrases)])
                        else:
                            listPhrases.append(wordPhrases[indexes[i-1]+1:indexes[i]])
                else: listPhrases.append(wordPhrases)

                terms = wordPhrases.split() 
                totalDoc, index, docLength = buildIndex(inputFile, listPhrases)

                if queryType == "and":
                    result = boolean_query(queryType, listPhrases, index)
                elif queryType == "or":
                    result = boolean_query(queryType, listPhrases, index)
                elif queryType == "ql":
                    result = ql_query(queryType, listPhrases, index, docLength, totalDoc)
                elif queryType == "bm25":
                    result = bm25_query(queryType, listPhrases, index, docLength, totalDoc)

                for each in result:
                    ranking += 1
                    if queryType == "and":
                        score = "1.0000"
                        output.write(queryName+"\tskip\t"+str(each)+"\t"+str(ranking)+"\t"+score+"\tIlmin\n")
                    elif queryType == "or":
                        score = "1.0000"
                        output.write(queryName+"\tskip\t"+str(each)+"\t"+str(ranking)+"\t"+score+"\tIlmin\n")
                    else:
                        output.write(queryName+"\tskip\t"+str(each[0])+"\t"+str(ranking)+"\t"+str(each[1])+"\tIlmin\n")
                # output.close()
                # break
        output.close()


